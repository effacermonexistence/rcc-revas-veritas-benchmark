import unittest
from copy import deepcopy
from unittest.mock import patch
from .common import *
from rcc_revas_eval.runtime import verify_result
from rcc_revas_eval.handoff import make_handoff, verify_handoff
from rcc_revas_eval.integrity import ContractError, digest, canonical
from rcc_revas_eval.evidence import sign_payload

class DevelopmentCases(unittest.TestCase):
    """Developer-exposed fixtures, deliberately not a fresh benchmark."""
    pass

_rows=read_jsonl(ROOT/'fixtures/smoke_inputs.jsonl')
_labels={x['case_id']:x for x in read_jsonl(ROOT/'fixtures/scoring_labels.jsonl')}
for _row in _rows:
    def test(self, row=deepcopy(_row)):
        result=evaluate(row)
        expected=_labels[row['case_id']]
        self.assertEqual(result['decision']['adoption']['decision'],expected['expected_decision'])
        self.assertEqual(result['handoff_release']['status']=='RELEASED_FOR_GOVERNANCE_REVIEW',expected['expected_release'])
        verify_result(result)
    setattr(DevelopmentCases,'test_'+_row['case_id'].replace('-','_'),test)

class RuntimeInvariants(unittest.TestCase):
    def test_deterministic_result_including_lock(self):
        r=make('unit-replay','protected_action')
        self.assertEqual(canonical(evaluate(r)),canonical(evaluate(r)))

    def test_input_not_mutated(self):
        r=make('unit-purity'); before=canonical(r); evaluate(r)
        self.assertEqual(canonical(r),before)

    def test_case_identifier_does_not_select_verdict(self):
        r=make('unit-id'); a=evaluate(r)
        r['case_id']='UNRELATED_EXPECTED_DENY_WORDS_ARE_NOT_LABELS'
        b=evaluate(r)
        self.assertEqual(a['decision']['adoption'],b['decision']['adoption'])

    def test_partial_fact_retained(self):
        result=evaluate(deepcopy(_rows[3]))
        adopted=result['decision']['adoption']
        self.assertEqual(adopted['decision'],'HOLD')
        self.assertIn('c1',adopted['supported_claims'])
        self.assertNotIn('c2',adopted['supported_claims'])

    def test_inference_does_not_become_fact(self):
        result=evaluate(make('unit-inference','bounded_inference'))
        self.assertEqual(result['decision']['adoption']['supported_claims']['c1']['epistemic_type'],'INFERENCE')

    def test_wrong_epistemic_type_rejected_as_input_error(self):
        r=make('unit-type','bounded_inference'); r['candidate']['claims']['c1']['epistemic_type']='FACT'; sync_content(r); resign(r)
        with self.assertRaisesRegex(ContractError,'EPISTEMIC_TYPE_MISMATCH'): evaluate(r)

    def test_no_claimed_external_authority(self):
        result=evaluate(make('unit-handoff','protected_action'))
        h,objects=make_handoff(result)
        self.assertTrue(all(v is False for v in h['boundary_assertions'].values()))
        self.assertNotIn('decision_id',h)
        self.assertNotIn('ExecutionIntent',h)
        verify_handoff(h,result,objects)

    def test_hash_domains_not_interchangeable(self):
        result=evaluate(make('unit-hash-domain'))
        h,_=make_handoff(result)
        hashes={result['decision_lock']['decision_hash'],h['candidate']['selected_output_hash'].split(':')[-1],h['source_artifact']['artifact_hash'].split(':')[-1]}
        self.assertEqual(len(hashes),3)

    def test_changed_selected_candidate_fails_lock(self):
        r=evaluate(make('unit-tamper')); r['decision']['candidate']['claims']['c1']['value']='different'
        with self.assertRaisesRegex(ContractError,'DECISION_LOCK_MISMATCH'): verify_result(r)

    def test_changed_release_fails_hash(self):
        r=evaluate(make('unit-release')); r['handoff_release']['status']='WITHHELD_BY_RCC'
        with self.assertRaisesRegex(ContractError,'HANDOFF_RELEASE_MISMATCH'): verify_result(r)

    def test_handoff_cannot_widen_permission(self):
        r=evaluate(make('unit-authority','protected_action')); h,objects=make_handoff(r)
        h['boundary_assertions']['execution_authority_conferred']=True
        with self.assertRaisesRegex(ContractError,'HANDOFF_SEMANTICS'): verify_handoff(h,r,objects)

    def test_candidate_object_tamper_detected(self):
        r=evaluate(make('unit-object')); h,objects=make_handoff(r)
        key=h['candidate']['selected_output_ref'].removeprefix('bundle://')
        objects[key]+=b' '
        with self.assertRaisesRegex(ContractError,'HANDOFF_OBJECT_MISMATCH'): verify_handoff(h,r,objects)

    def test_fallback_retained_not_reauthorized(self):
        r=make('unit-fallback','protected_action'); r['evidence']=[]
        r['upstream_fallback']['epistemic_type']='ACTION_PROPOSAL'
        result=evaluate(r)
        self.assertEqual(result['decision']['adoption']['retained_fallback'],r['upstream_fallback'])
        self.assertFalse(result['decision']['adoption']['fallback_reauthorized'])
        self.assertIsNone(make_handoff(result)[0]['candidate']['selected_output_ref'])

    def test_null_measurement_not_invented(self):
        h,_=make_handoff(evaluate(make('unit-null')))
        self.assertIsNone(h['measurement_evidence'])
        self.assertIsNone(h['lineage']['source_observation_id'])

    def test_untyped_measurement_metadata_rejected_before_handoff(self):
        r=make('unit-measurement'); r['lineage']['measurement_evidence']={'score':'0.25'}
        with self.assertRaisesRegex(ContractError,'UNTYPED_MEASUREMENT_EVIDENCE_FORBIDDEN'):
            evaluate(r)

    def test_source_references_preserved_without_measurement_passthrough(self):
        r=make('unit-source-ref'); r['lineage']['source_artifact_refs']=['synthetic://immutable-ref']
        h,_=make_handoff(evaluate(r))
        self.assertIsNone(h['measurement_evidence'])
        self.assertEqual(h['lineage']['immutable_source_artifact_refs'],r['lineage']['source_artifact_refs'])

    def test_no_socket_or_http_calls(self):
        with patch('socket.socket',side_effect=AssertionError('Network prohibited')):
            r=evaluate(make('unit-network','protected_action')); make_handoff(r)

    def test_no_approval_requirement_in_other_action_profile(self):
        r=make('unit-nonapproval','protected_action')
        for obj in (r['request'],r['candidate']): obj['typed_action']['action_class']='document_write'
        r['evidence'][2]['payload']['observations']['approval:required']=False
        sync_content(r);resign(r)
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'ADOPT')

    def test_candidate_cannot_select_weaker_policy(self):
        r=make('unit-weak','protected_action');r['candidate']['typed_action']['action_class']='document_write'
        r['evidence'].pop();sync_content(r);resign(r)
        result=evaluate(r)
        self.assertEqual(result['decision']['adoption']['decision'],'REJECT')
        self.assertTrue(any(c['check']=='approval:required' for c in result['decision']['verification']['checks']))

    def test_unrelated_expired_evidence_does_not_erase_known_claim(self):
        r=make('unit-unrelated')
        add_evidence(r,'synthetic-observation-issuer',{'claim:unrequested':'irrelevant'},'extra')
        r['evidence'][-1]['payload']['expires_at']='2026-09-20T12:00:00Z';resign(r)
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'ADOPT')

    def test_boolean_is_not_integer_evidence(self):
        r=make('unit-number','protected_action')
        r['evidence'][1]['payload']['observations']['authority:valid']=1;resign(r)
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'HOLD')

    def test_candidate_content_cannot_smuggle_unverified_prose(self):
        r=make('unit-content');r['candidate']['content']={'claims':r['candidate']['claims'],'extra':'make external transfer'}
        with self.assertRaisesRegex(ContractError,'UNVERIFIED_CONTENT'):evaluate(r)

    def test_unicode_signature_is_invalid_not_runtime_crash(self):
        r=make('unit-unicode');r['evidence'][0]['signature']='거짓서명'
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'HOLD')

    def test_candidate_parameter_change_is_not_same_action(self):
        r=make('unit-params','protected_action');r['candidate']['typed_action']['parameters']['duration_seconds']=999
        sync_content(r);resign(r)
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'REJECT')

    def test_inference_rejects_non_strict_ranking(self):
        r=make('unit-tie','bounded_inference');r['evidence'][0]['payload']['observations']['ranking:c1']=['hypothesis-A','hypothesis-A'];resign(r)
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'HOLD')

    def test_repeated_runs_do_not_consume_other_case_state(self):
        r=make('unit-isolation','protected_action');before=evaluate(r)
        expired=deepcopy(r);expired['handoff_state']={'as_of':'2026-09-22T00:00:00Z','binding':deepcopy(r['request']['binding']),'revoked_evidence_ids':[]}
        self.assertEqual(evaluate(expired)['handoff_release']['status'],'WITHHELD_BY_RCC')
        self.assertEqual(canonical(evaluate(r)),canonical(before))

    def test_unknown_class_uses_explicit_generic_governance_profile(self):
        r=make('unit-generic-profile','protected_action')
        for obj in (r['request'],r['candidate']):obj['typed_action']['action_class']='unknown-policy-class'
        sync_content(r);resign(r)
        result=evaluate(r)
        self.assertEqual(result['decision']['adoption']['decision'],'ADOPT')
        checks={c['check']:c['status'] for c in result['decision']['verification']['checks']}
        self.assertEqual(checks['authority:valid'],'PASS')
        self.assertEqual(checks['approval:valid'],'PASS')

    def test_wrong_request_binding_does_not_preserve_claims(self):
        r=make('unit-binding');r['candidate']['binding']['object_id']='different-object';resign(r)
        result=evaluate(r)
        self.assertEqual(result['decision']['adoption']['decision'],'REJECT')
        self.assertEqual(result['decision']['adoption']['supported_claims'],{})

    def test_no_verifier_or_adoption_verdicts_in_input(self):
        for field in ('ground_truth','expected_decision','upstream_rcc_revas','runtime_verifier_passed','adoption_decision'):
            with self.subTest(field=field):
                r=make('unit-leak');r[field]=True
                with self.assertRaisesRegex(ContractError,'EVALUATION_ONLY_FIELD_FORBIDDEN|UNEXPECTED_FIELD'):evaluate(r)

    def test_nested_candidate_verdict_rejected(self):
        r=make('unit-nested');r['candidate']['expected_decision']='ADOPT'
        with self.assertRaisesRegex(ContractError,'EVALUATION_ONLY_FIELD_FORBIDDEN|UNEXPECTED_FIELD'):evaluate(r)

    def test_evidence_from_another_candidate_is_not_reused(self):
        r=make('unit-bound');r['candidate']['candidate_id']='changed-id'
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'HOLD')

    def test_unknown_approval_is_hold_not_known_false(self):
        r=make('unit-unknown-approval','protected_action')
        r['evidence'][2]['payload']['observations']['approval:valid']=None;resign(r)
        result=evaluate(r)
        self.assertEqual(result['decision']['adoption']['decision'],'HOLD')
        self.assertIn('BOOLEAN_CONDITION_UNKNOWN',result['decision']['adoption']['reason_codes'])

    def test_unknown_preservation_does_not_become_rejection(self):
        r=make('unit-unknown-preservation','candidate_replacement')
        r['evidence'][0]['payload']['observations']['replacement:preserves_required_properties']=None;resign(r)
        self.assertEqual(evaluate(r)['decision']['adoption']['decision'],'HOLD')

class Rc2RegressionGuards(unittest.TestCase):
    def test_executor_output_is_the_candidate_verified_and_adopted(self):
        from rcc_revas_eval import runtime as rt
        row = make('rc2-executor-binding', 'protected_action')
        original = deepcopy(row['candidate'])

        def changed_executor(supplied, route):
            candidate = deepcopy(supplied)
            candidate['typed_action']['target_resource'] = 'user:changed-by-executor'
            candidate['content']['action'] = deepcopy(candidate['typed_action'])
            receipt = {
                'status': 'EXECUTED',
                'executor_id': route['executor_id'],
                'mode': 'FAULT_INJECTION_TEST',
                'generated_live': False,
                'candidate_hash': digest(candidate, 'rcc-candidate-v1'),
                'candidate_type': candidate['candidate_type'],
                'model_calls': 0,
            }
            return candidate, receipt

        with patch('rcc_revas_eval.runtime.materialize_candidate', side_effect=changed_executor):
            result = evaluate(row)
        self.assertNotEqual(canonical(result['decision']['candidate']), canonical(original))
        self.assertEqual(result['decision']['candidate']['typed_action']['target_resource'],
                         'user:changed-by-executor')
        self.assertEqual(result['decision']['adoption']['decision'], 'REJECT')
        self.assertEqual(result['decision']['execution']['candidate_hash'],
                         digest(result['decision']['candidate'], 'rcc-candidate-v1'))
        verify_result(result)

    def test_nested_evaluation_only_metadata_is_rejected(self):
        row = make('rc2-gold-leak', 'protected_action')
        row['candidate']['typed_action']['parameters']['nested'] = {
            'ground_truth': {'expected_decision': 'ALLOW'}
        }
        sync_content(row); resign(row)
        with self.assertRaisesRegex(ContractError, 'EVALUATION_ONLY_FIELD_FORBIDDEN'):
            evaluate(row)

    def test_replacement_evidence_is_bound_to_baseline(self):
        row = make('rc2-replacement-binding', 'candidate_replacement')
        self.assertEqual(evaluate(row)['decision']['adoption']['decision'], 'ADOPT')
        row['upstream_fallback']['value'] = 'changed-baseline-after-evidence'
        result = evaluate(row)
        self.assertEqual(result['decision']['adoption']['decision'], 'REJECT')
        self.assertIn('OBSERVATION_CONTRADICTS_CANDIDATE',
                      result['decision']['adoption']['reason_codes'])

    def test_decision_lock_is_stable_across_later_handoff_state(self):
        base = make('rc2-temporal-split', 'protected_action')
        later = deepcopy(base)
        later['handoff_state'] = {
            'as_of': '2026-09-21T01:00:00Z',
            'binding': deepcopy(base['request']['binding']),
            'revoked_evidence_ids': [],
        }
        a = evaluate(base)
        b = evaluate(later)
        self.assertEqual(a['decision_lock']['decision_hash'], b['decision_lock']['decision_hash'])
        self.assertNotEqual(a['handoff_release_hash'], b['handoff_release_hash'])
