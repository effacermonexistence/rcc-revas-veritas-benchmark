"""Executable regression witnesses for F01-F07 from the rc2 five-pass audit.

HTTP peers below are explicitly TEST PEERS, not the VERITAS native runtime.
They exercise real loopback sockets, wire numbers, error paths and persistence.
"""
from __future__ import annotations
import base64
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from .common import ROOT, POLICY, KEYRING, identity
from scripts.build_development_fixtures import make
from rcc_revas_eval.integrity import (ContractError, canonical, digest, raw_sha, read_json,
                                    read_jsonl, jsonl_bytes)
from rcc_revas_eval.contract import check_input
from rcc_revas_eval.scenario import BOOL_FIELDS, ID_FIELDS
from rcc_revas_eval.takeshi import _source_rows, transform_case, transform_file
from rcc_revas_eval.runtime import evaluate_one, verify_result
from rcc_revas_eval.bundle import create_run, verify_run, _read_optional_jsonl
from rcc_revas_eval.preregistration import freeze_plan
from rcc_revas_eval.scoring import score_run
from rcc_revas_eval.native_veritas import (build_decide_request, invoke_run, verify_native_run,
    verify_response_echo, response_diagnostics, validate_endpoint)
from rcc_revas_eval.partner_review import register_partner, report_partner
from rcc_revas_eval.wire import wire_loads, wire_bytes

SOURCE=ROOT/'fixtures/takeshi/Governance_labelled_Evaluation_Set_v0.1.1.jsonl'
ROWS=_source_rows(SOURCE)
BY_ID={r['case_id']:r for r in ROWS}
MANIFEST=ROOT/'evaluation_manifest.json'

class FixtureIntegrity(unittest.TestCase):
    def test_exact_36_row_upstream_git_blob_bytes(self):
        b=SOURCE.read_bytes()
        self.assertEqual(len(ROWS),36)
        self.assertEqual(len(b),114884)
        self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
                         '426eda32bda6ba767a42f4c2e0f979483f76f46a')
        self.assertEqual(raw_sha(b),read_json(SOURCE.parent/'SOURCE_PROVENANCE.json')['sha256'])

    def test_all_36_transform_execute_schema_and_replay_without_errors(self):
        for source in ROWS:
            with self.subTest(case=source['case_id']):
                row=transform_case(source,policy=POLICY,keyring=KEYRING)
                check_input(row)
                r=evaluate_one(row,POLICY,KEYRING,identity());verify_result(r)
                self.assertEqual(r,evaluate_one(row,POLICY,KEYRING,identity()))
                try:
                    from jsonschema import Draft202012Validator
                except ImportError:
                    pass
                else:
                    Draft202012Validator(read_json(ROOT/'schemas/runtime_input.schema.json')).validate(row)

    def test_missing_action_h07_is_preserved_and_held_not_batch_exception(self):
        row=transform_case(BY_ID['GOV-H07'],policy=POLICY,keyring=KEYRING)
        self.assertIsNone(row['candidate']['typed_action']['canonical_action'])
        self.assertIsNone(row['candidate']['claims']['c1']['value'])
        r=evaluate_one(row,POLICY,KEYRING,identity())
        self.assertEqual(r['decision']['adoption']['decision'],'HOLD')
        self.assertEqual(r['handoff_release']['status'],'WITHHELD_BY_RCC')

    def test_h09_requirement_unknown_is_not_defaulted(self):
        s=deepcopy(BY_ID['GOV-H09']);a=transform_case(s,policy=POLICY,keyring=KEYRING)
        s['input']['governance_fixture']['approval_requirement_resolved']=True
        b=transform_case(s,policy=POLICY,keyring=KEYRING)
        self.assertNotEqual(a,b)
        self.assertEqual(evaluate_one(a,POLICY,KEYRING,identity())['decision']['adoption']['decision'],'HOLD')
        self.assertEqual(evaluate_one(b,POLICY,KEYRING,identity())['decision']['adoption']['decision'],'ADOPT')

    def test_every_source_condition_survives_transform(self):
        for s in ROWS:
            r=transform_case(s,policy=POLICY,keyring=KEYRING)
            actual=r['partner_scenario']['governance_fixture']
            self.assertEqual(set(actual),set(s['input']['governance_fixture']))
            for k,v in s['input']['governance_fixture'].items():
                with self.subTest(case=s['case_id'],field=k):
                    if k in {'authority_evidence_id','human_approval_receipt_id'} and v is not None:
                        self.assertTrue(actual[k].startswith('fixture:'))
                    else:
                        self.assertEqual(actual[k],v)

    def test_each_boolean_toggle_changes_frozen_evaluation_state(self):
        source=deepcopy(BY_ID['GOV-A01'])
        base=transform_case(source,policy=POLICY,keyring=KEYRING)
        for k in BOOL_FIELDS:
            s=deepcopy(source);s['input']['governance_fixture'][k]=not s['input']['governance_fixture'][k]
            r=transform_case(s,policy=POLICY,keyring=KEYRING)
            with self.subTest(field=k):
                self.assertNotEqual(canonical(r),canonical(base))
                self.assertEqual(r['partner_scenario']['governance_fixture'][k],not base['partner_scenario']['governance_fixture'][k])

    def test_gold_titles_mutations_hashes_cannot_change_runtime(self):
        for source in ROWS:
            a=transform_case(source,policy=POLICY,keyring=KEYRING)
            s=deepcopy(source)
            s['ground_truth']={'expected_decision':'ATTACKER-GOLD','new_key':['answer']}
            s['title']='ANSWER: ALLOW';s['mutation']={'type':'MAKE_ALLOW'};s['case_sha256']='forged-gold-hash'
            s['input']['upstream_rcc_revas']['runtime_verifier_passed']=False
            s['input']['upstream_rcc_revas']['adoption_decision']='rejected'
            b=transform_case(s,policy=POLICY,keyring=KEYRING)
            self.assertEqual(canonical(a),canonical(b),source['case_id'])

    def test_label_coded_identifiers_do_not_reach_native_input(self):
        for source in ROWS:
            r=transform_case(source,policy=POLICY,keyring=KEYRING)
            self.assertNotIn(source['case_id'],canonical(r).decode())

    def test_untrusted_approval_like_metadata_is_not_authority(self):
        s=deepcopy(BY_ID['GOV-H12'])
        r=transform_case(s,policy=POLICY,keyring=KEYRING)
        s['input']['upstream_rcc_revas']['source_annotations']['business_decision']='DENY'
        s['input']['upstream_rcc_revas']['source_annotations']['human_review_required']=True
        q=transform_case(s,policy=POLICY,keyring=KEYRING)
        self.assertEqual(evaluate_one(r,POLICY,KEYRING,identity())['decision']['adoption']['decision'],
                         evaluate_one(q,POLICY,KEYRING,identity())['decision']['adoption']['decision'])

    def test_source_mismatch_not_cured_by_new_valid_rcc_hashes(self):
        for cid in ('GOV-D05','GOV-D06','GOV-D07','GOV-D10','GOV-D11','GOV-D12'):
            r=transform_case(BY_ID[cid],policy=POLICY,keyring=KEYRING)
            self.assertEqual(evaluate_one(r,POLICY,KEYRING,identity())['decision']['adoption']['decision'],'REJECT',cid)

    def test_source_scenario_cannot_be_modified_without_bound_evidence(self):
        r=transform_case(BY_ID['GOV-A01'],policy=POLICY,keyring=KEYRING)
        r['partner_scenario']['governance_fixture']['target_context_match']=False
        v=evaluate_one(r,POLICY,KEYRING,identity())
        self.assertNotEqual(v['decision']['adoption']['decision'],'ADOPT')
        self.assertTrue(any(x['check']=='fixture:scenario_hash' and x['status']=='REJECT' for x in v['decision']['verification']['checks']))

    def test_partial_failure_does_not_erase_successful_transform(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); a=deepcopy(ROWS[0]);b=deepcopy(ROWS[1]);b['input']['governance_fixture']['NEW_UNMAPPED_CONTROL']=True
            (p/'source.jsonl').write_bytes(wire_bytes(a)+b'\n'+wire_bytes(b)+b'\n')
            report=transform_file(p/'source.jsonl',p/'out.jsonl',p/'report.json',policy=POLICY,keyring=KEYRING)
            self.assertEqual(report['enrolled'],2);self.assertEqual(report['case_count'],1);self.assertEqual(report['errors'],1)
            self.assertIsNone(report['case_accounting'][1]['governance_decision'])
            self.assertEqual(len(read_jsonl(p/'out.jsonl')),1)

class GoldLeakage(unittest.TestCase):
    def test_nested_missing_blocklist_fields_and_spelling_variants(self):
        names=['expected_gate_decision','expected_business_decision','expected_bind_gate_outcome',
            'expected_missing_evidence','expected_handoff_state','expected_new_outcome',
            'expectedGateDecision','EXPECTED_GATE_DECISION','expected-gate-decision','gold_answer']
        for name in names:
            row=make('nested','protected_action')
            row['candidate']['typed_action']['parameters']['nested']=[{'inner':{name:'ALLOW'}}]
            row['candidate']['content']['action']=deepcopy(row['candidate']['typed_action'])
            with self.subTest(field=name), self.assertRaisesRegex(ContractError,'EVALUATION_ONLY_FIELD_FORBIDDEN'):
                check_input(row)

    def test_eval_label_rejected_inside_signed_observation_and_fallback(self):
        row=make('signed')
        row['evidence'][0]['payload']['observations']['x']={'expected_decision':'ADOPT'}
        with self.assertRaisesRegex(ContractError,'EVALUATION_ONLY_FIELD_FORBIDDEN'): check_input(row)
        row=make('fallback');row['upstream_fallback']={'value':{'gold':'secret'},'epistemic_type':'UNVERIFIED','source_ref':'test'}
        with self.assertRaisesRegex(ContractError,'EVALUATION_ONLY_FIELD_FORBIDDEN'): check_input(row)

class PreregistrationChecks(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.p=Path(t.name)
        self.i=self.p/'input.jsonl';self.i.write_bytes(jsonl_bytes([make('registered')]))
        self.l=self.p/'label.jsonl';self.l.write_bytes(jsonl_bytes([{'case_id':'registered','expected_decision':'ADOPT','expected_release':True,'label_provenance':'test'}]))
        self.plan=self.p/'plan.json';freeze_plan(MANIFEST,self.i,self.l,self.plan)

    def test_changing_label_and_its_claimed_hash_after_run_is_rejected(self):
        run=self.p/'run';create_run(MANIFEST,self.i,run,plan_path=self.plan)
        label=read_jsonl(self.l);label[0]['expected_decision']='REJECT';self.l.write_bytes(jsonl_bytes(label))
        with self.assertRaisesRegex(ContractError,'POST_RUN_LABEL_CHANGE_FORBIDDEN'):
            score_run(MANIFEST,run,self.l,self.p/'score',raw_sha(self.l.read_bytes()))

    def test_unregistered_run_cannot_be_retroactively_confirmatory(self):
        run=self.p/'run';create_run(MANIFEST,self.i,run)
        with self.assertRaisesRegex(ContractError,'SCORING_NOT_PREREGISTERED'):
            score_run(MANIFEST,run,self.l,self.p/'score',raw_sha(self.l.read_bytes()))

    def test_changed_plan_input_fails_before_directory_or_execution(self):
        rows=read_jsonl(self.i);rows[0]['case_id']='changed';self.i.write_bytes(jsonl_bytes(rows))
        with self.assertRaisesRegex(ContractError,'PREREGISTRATION_INPUT_MISMATCH'):
            create_run(MANIFEST,self.i,self.p/'run',plan_path=self.plan)
        self.assertFalse((self.p/'run').exists())

    def test_registered_and_unregistered_runs_have_identical_core_decisions(self):
        create_run(MANIFEST,self.i,self.p/'a',plan_path=self.plan);create_run(MANIFEST,self.i,self.p/'b')
        for name in ('rcc_results.jsonl','handoff_results.jsonl'):
            self.assertEqual((self.p/'a'/name).read_bytes(),(self.p/'b'/name).read_bytes())

    def test_native_scope_cannot_use_upstream_scorer(self):
        plan=read_json(self.plan);plan['metric_spec']={'metric_spec':'different'};plan['metric_spec_hash']=digest(plan['metric_spec'],'rcc-metric-spec-v1')
        self.plan.write_bytes(canonical(plan)+b'\n')
        create_run(MANIFEST,self.i,self.p/'run',plan_path=self.plan)
        with self.assertRaisesRegex(ContractError,'SCORING_METRIC_SPEC_UNSUPPORTED'):
            score_run(MANIFEST,self.p/'run',self.l,self.p/'score',raw_sha(self.l.read_bytes()))

class WireChecks(unittest.TestCase):
    def test_finite_fractional_response_roundtrip_is_supported(self):
        self.assertEqual(wire_loads(b'{"risk":0.25,"score":1.9e-2}'),{'risk':0.25,'score':0.019})
        self.assertEqual(wire_loads(wire_bytes({'risk':0.25})),{'risk':0.25})
        with self.assertRaises(ContractError): canonical({'risk':0.25})

    def test_invalid_wire_forms_rejected(self):
        for raw in [b'{"risk":NaN}',b'{"risk":Infinity}',b'{"x":1,"x":2}',b'{"x":1e999}', b'\xff',b'{"x":"\\ud800"}',b'['*100+b']'*100]:
            with self.subTest(raw=raw[:40]),self.assertRaises(ContractError): wire_loads(raw)

    def test_bad_endpoint_and_timeout_rejected(self):
        for url in ['http://example.com','https://user:password@example.com','https://example.com?secret=x','https://example.com/v1','file:///etc/passwd']:
            with self.subTest(url=url),self.assertRaises(ContractError):validate_endpoint(url)
        for timeout in (0,-1,float('nan'),float('inf'),301):
            with self.subTest(timeout=timeout),self.assertRaises(ContractError): validate_endpoint('http://127.0.0.1',timeout)

class HTTPTestPeer:
    """Local deterministic wire fixture, never represented as native VERITAS."""
    def __init__(self, callback):
        self.requests=[];self.auth=[];self.callback=callback
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.auth.append(self.headers.get('X-API-Key'))
                payload=wire_loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append(payload)
                code,body,headers=owner.callback(len(owner.requests),payload)
                self.send_response(code)
                for k,v in headers.items():self.send_header(k,v)
                self.end_headers();self.wfile.write(body)
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.url=f'http://127.0.0.1:{self.server.server_address[1]}'
    def __enter__(self):self.thread.start();return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join()

class NativeTransportRegressions(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.p=Path(t.name)
        self.inputs=self.p/'inputs.jsonl';self.inputs.write_bytes(jsonl_bytes([make('net-1','protected_action'),make('net-2','protected_action')]))
        self.run=self.p/'run';create_run(MANIFEST,self.inputs,self.run)

    @staticmethod
    def good(i,payload):
        b=wire_bytes({'meta':{'ok':True,'request_id':str(i)},'gate_decision':'proceed','risk':0.25,
                      'chosen':payload['alternatives'][0]})
        return 200,b,{}

    def invoke(self,cb):
        with HTTPTestPeer(cb) as peer,patch.dict(os.environ,{'CANONICAL_TEST_KEY':'fixture-key-not-a-production-secret'}):
            s=invoke_run(MANIFEST,self.run,self.p/'native',base_url=peer.url,api_key_env='CANONICAL_TEST_KEY')
        return s,peer

    def test_real_loopback_floats_processed_and_raw_bytes_retained(self):
        s,peer=self.invoke(self.good)
        self.assertEqual(s['errors'],0);self.assertEqual(s['attempts'],2)
        receipts=read_jsonl(self.p/'native/veritas_native_receipts.jsonl')
        raw=base64.b64decode(receipts[0]['response_body_base64'])
        self.assertEqual(wire_loads(raw)['risk'],0.25)
        self.assertEqual(receipts[0]['response_hash'],'sha256:'+raw_sha(raw))
        self.assertEqual(s['exact_candidate_consumption_verified_count'],0)
        self.assertFalse(verify_native_run(MANIFEST,self.run,self.p/'native')['native_consumption_verified'])
        self.assertTrue(peer.auth[0])

    def test_success_then_http_failure_preserves_both_and_verifies(self):
        def cb(i,p):return self.good(i,p) if i==1 else (503,b'{"error":"maintenance"}',{})
        s,_=self.invoke(cb)
        self.assertEqual(s['errors'],1)
        receipts=read_jsonl(self.p/'native/veritas_native_receipts.jsonl')
        self.assertEqual([r['status'] for r in receipts],['RESPONSE_RECORDED','ERROR'])
        self.assertEqual(len(read_jsonl(self.p/'native/attempt_journal.jsonl')),4)
        self.assertEqual(verify_native_run(MANIFEST,self.run,self.p/'native')['errors'],1)

    def test_200_failure_with_matching_echo_not_proof(self):
        def cb(i,p):
            c=p['context']['rcc_revas']
            echo={k:c[k] for k in ('candidate_semantic_hash','candidate_object_hash','decision_state_binding_fingerprint','upstream_decision_hash','correlation_id','evaluation_pre_state_hash')}
            return 200,wire_bytes({'meta':{'ok':False,'error':'backend failed'},'chosen':{'id':'wrong-candidate'},'extras':{'rcc_revas_echo':echo}}),{}
        s,_=self.invoke(cb)
        self.assertEqual(s['errors'],2);self.assertEqual(s['exact_candidate_consumption_verified_count'],0)
        for r in read_jsonl(self.p/'native/veritas_native_receipts.jsonl'):
            self.assertTrue(r['diagnostics']['native_echo_verification']['correlation_fields_match'])
            self.assertFalse(r['diagnostics']['response_usable_for_observational_gate_metrics'])

    def test_echo_alone_never_certifies_native(self):
        proof={'candidate_semantic_hash':'x','candidate_object_hash':'a','decision_state_binding_fingerprint':'b','upstream_decision_hash':'c','correlation_id':'d'}
        r=verify_response_echo({'extras':{'rcc_revas_echo':proof}},proof)
        self.assertTrue(r['correlation_fields_match']);self.assertFalse(r['exact_candidate_consumption_verified'])

    def test_redirect_is_not_followed_and_key_not_forwarded(self):
        with HTTPTestPeer(self.good) as other:
            s,_=self.invoke(lambda i,p:(307,b'redirect',{'Location':other.url+'/v1/decide'}))
        self.assertEqual(s['errors'],2);self.assertEqual(other.requests,[])
        self.assertEqual(read_jsonl(self.p/'native/veritas_native_receipts.jsonl')[0]['error_code'],'VERITAS_REDIRECT_REFUSED')

    def test_invalid_json_response_retained_as_error(self):
        s,_=self.invoke(lambda i,p:(200,b'{"risk":NaN}',{}))
        self.assertEqual(s['errors'],2)
        r=read_jsonl(self.p/'native/veritas_native_receipts.jsonl')[0]
        self.assertEqual(base64.b64decode(r['response_body_base64']),b'{"risk":NaN}')
        self.assertEqual(r['error_code'],'WIRE_NONFINITE_NUMBER')

    def test_sensitive_key_reflection_is_redacted(self):
        s,_=self.invoke(lambda i,p:(200,b'{"key":"fixture-key-not-a-production-secret"}',{}))
        self.assertEqual(s['errors'],2)
        for p in (self.p/'native').iterdir():
            if p.is_file():self.assertNotIn(b'fixture-key-not-a-production-secret',p.read_bytes())

    def test_evaluation_prestate_body_is_hash_bound_not_just_binding_ids(self):
        handoff=read_jsonl(self.run/'handoff_results.jsonl')[0]
        p,proof=build_decide_request(handoff,self.run)
        c=p['context']['rcc_revas']
        self.assertEqual(digest(c['evaluation_pre_state'],'rcc-evaluation-pre-state-v1'),proof['evaluation_pre_state_hash'])
        self.assertIn('evidence',c['evaluation_pre_state'])
        self.assertFalse(proof['server_side_exact_candidate_consumption_verified'])

    def test_no_secret_in_request_receipt_headers(self):
        self.invoke(self.good)
        for p in (self.p/'native').iterdir():
            if p.is_file():self.assertNotIn(b'fixture-key-not-a-production-secret',p.read_bytes())

class PartnerReporting(unittest.TestCase):
    def test_registered_36_report_preserves_mismatches_and_unknown_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            register_partner(MANIFEST,SOURCE,p/'registered')
            create_run(MANIFEST,p/'registered/runtime_inputs.jsonl',p/'run',plan_path=p/'registered/preregistration.json')
            report=report_partner(MANIFEST,p/'run',p/'registered/scoring_labels.jsonl',p/'report')
            self.assertEqual(report['upstream_executed'],36);self.assertEqual(report['upstream_errors'],0)
            self.assertEqual(set(report['arm_a_label_mismatch_case_ids']),{'GOV-H06','GOV-H07','GOV-D08'})
            g=read_json(p/'report/governance_metrics.json')
            self.assertIsNone(g['arm_b_observational']['false_allow_count'])
            self.assertIsNone(g['bind_eligibility_accuracy']['value'])
            self.assertFalse(report['joint_full_treatment_completed'])
            self.assertEqual(read_json(p/'report/regression_metrics.json')['candidate_adoption_changes'],None)

class AdditionalReleaseGuards(unittest.TestCase):
    def test_missing_declared_evidence_identifier_does_not_pass(self):
        for key in ('authority_evidence_id','human_approval_receipt_id','policy_snapshot_id'):
            s=deepcopy(BY_ID['GOV-A01']);s['input']['governance_fixture'][key]=None
            row=transform_case(s,policy=POLICY,keyring=KEYRING)
            with self.subTest(key=key):
                self.assertEqual(evaluate_one(row,POLICY,KEYRING,identity())['decision']['adoption']['decision'],'HOLD')

    def test_nonstr_identifier_is_contract_error_not_batch_crash(self):
        s=deepcopy(BY_ID['GOV-A01']);s['input']['governance_fixture']['authority_evidence_id']=42
        with self.assertRaises(ContractError):transform_case(s,policy=POLICY,keyring=KEYRING)

    def test_incomplete_condition_is_preserved_as_unknown(self):
        s=deepcopy(BY_ID['GOV-A01']);del s['input']['governance_fixture']['approval_requirement_resolved']
        r=transform_case(s,policy=POLICY,keyring=KEYRING)
        self.assertNotIn('approval_requirement_resolved',r['partner_scenario']['governance_fixture'])
        self.assertEqual(evaluate_one(r,POLICY,KEYRING,identity())['decision']['adoption']['decision'],'HOLD')

    def test_true_id_echo_does_not_hide_different_candidate_payload(self):
        candidate={'x':'actual'};h=digest(candidate,'rcc-candidate-v1')
        proof={'candidate_semantic_hash':h,'candidate_object_hash':'o','decision_state_binding_fingerprint':'s','upstream_decision_hash':'d','correlation_id':'c'}
        response={'ok':True,'gate_decision':'proceed','chosen':{'id':'rcc-candidate:'+h,'description':'{"x":"changed"}'},'extras':{'rcc_revas_echo':proof}}
        r=response_diagnostics(response,proof)
        self.assertEqual(r['candidate_payload_response'],'MISMATCH')
        self.assertFalse(r['response_usable_for_observational_gate_metrics'])
        self.assertFalse(r['native_echo_verification']['exact_candidate_consumption_verified'])

    def test_wrong_meta_type_cannot_be_reported_as_success(self):
        proof={'candidate_semantic_hash':'h'}
        for response in ({'ok':'true','gate_decision':'proceed'},{'meta':[],'gate_decision':'proceed'},{'error':0,'gate_decision':'proceed'}):
            r=response_diagnostics(response,proof)
            self.assertEqual(r['application_status'],'INVALID_META')
            self.assertFalse(r['response_usable_for_observational_gate_metrics'])

    def test_modern_unknown_gate_not_overwritten_by_legacy_allow(self):
        r=response_diagnostics({'ok':True,'gate_decision':'unknown','decision_status':'allow'}, {'candidate_semantic_hash':'h'})
        self.assertIsNone(r['observed_gate_decision'])

    def test_journal_survives_interruption_before_second_receipt(self):
        from rcc_revas_eval.native_veritas import inspect_native_journal
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);i=p/'i.jsonl';i.write_bytes(jsonl_bytes([make('crash1','protected_action'),make('crash2','protected_action')]))
            run=p/'run';create_run(MANIFEST,i,run)
            calls=[]
            from rcc_revas_eval import native_veritas as n
            original=n.invoke_one
            def interrupt(*a,**kw):
                calls.append(1)
                if len(calls)==2:raise KeyboardInterrupt()
                return original(*a,**kw)
            with HTTPTestPeer(NativeTransportRegressions.good) as peer,patch.dict(os.environ,{'REVIEW_KEY':'no-production-key'}),patch.object(n,'invoke_one',side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    n.invoke_run(MANIFEST,run,p/'native',base_url=peer.url,api_key_env='REVIEW_KEY')
            self.assertEqual(len(read_jsonl(p/'native/veritas_native_receipts.jsonl')),1)
            journal=inspect_native_journal(p/'native')
            self.assertEqual(journal['started'],2);self.assertEqual(journal['finished_markers'],1)
            self.assertEqual(journal['pending'][0]['case_id'],'crash2')
            self.assertFalse(journal['sealed_run_available'])

    def test_partially_written_last_journal_record_reported(self):
        from rcc_revas_eval.native_veritas import inspect_native_journal
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'attempt_journal.jsonl').write_bytes(b'{"attempt_id":"1","case_id":"x","state":"STARTED"}\n{"attemp')
            r=inspect_native_journal(p)
            self.assertTrue(r['truncated_or_invalid_tail']);self.assertEqual(len(r['pending']),1)

    def test_preparation_keeps_valid_rows_when_one_exceeds_native_title_limit(self):
        from .common import resign, sync_content
        from rcc_revas_eval.native_veritas import prepare_run
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);a=make('long','protected_action');b=make('normal','protected_action')
            for act in (a['request']['typed_action'],a['candidate']['typed_action']):act['canonical_action']='X'*1100
            sync_content(a);resign(a)
            (p/'input.jsonl').write_bytes(jsonl_bytes([a,b]));create_run(MANIFEST,p/'input.jsonl',p/'run')
            r=prepare_run(MANIFEST,p/'run',p/'prepared')
            self.assertEqual(r['prepared_requests'],1);self.assertEqual(r['errors'],1)
            self.assertEqual(read_jsonl(p/'prepared/errors.jsonl')[0]['error_code'],'VERITAS_CANDIDATE_TITLE_TOO_LARGE')

    def test_error_record_resealed_as_success_is_detected(self):
        from rcc_revas_eval.native_veritas import _seal
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'i.jsonl').write_bytes(jsonl_bytes([make('error','protected_action')]))
            create_run(MANIFEST,p/'i.jsonl',p/'run')
            with HTTPTestPeer(lambda i,q:(503,b'{}',{})) as peer,patch.dict(os.environ,{'TEST_KEY':'never-real-key'}):
                invoke_run(MANIFEST,p/'run',p/'native',base_url=peer.url,api_key_env='TEST_KEY')
            f=p/'native/veritas_native_receipts.jsonl';r=read_jsonl(f)[0];r['status']='RESPONSE_RECORDED';r['error_code']=None;f.write_bytes(jsonl_bytes([r]))
            j=p/'native/attempt_journal.jsonl';events=read_jsonl(j);events[1]['receipt_hash']=digest(r,'rcc-native-attempt-v2');j.write_bytes(jsonl_bytes(events))
            s=p/'native/summary.json';v=read_json(s);v['errors']=0;s.write_bytes(canonical(v)+b'\n')
            (p/'native/hashes.json').unlink();_seal(p/'native')
            with self.assertRaisesRegex(ContractError,'NATIVE_RESULT_STATUS_MISMATCH'):
                verify_native_run(MANIFEST,p/'run',p/'native')

    def test_native_inspection_does_not_modify_any_files(self):
        from rcc_revas_eval.native_veritas import inspect_native_journal
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);file=p/'attempt_journal.jsonl';b=b'{"attempt_id":"1","case_id":"x","state":"STARTED"}\n';file.write_bytes(b)
            inspect_native_journal(p);self.assertEqual(file.read_bytes(),b)
            self.assertEqual(len(list(p.iterdir())),1)
