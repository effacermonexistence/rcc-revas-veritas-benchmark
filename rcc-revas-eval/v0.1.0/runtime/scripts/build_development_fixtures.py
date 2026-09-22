#!/usr/bin/env python3
"""Creates NEW DEVELOPMENT inputs; does not rewrite or relabel historical 36 cases.

The signing keys are deliberately public synthetic test keys. No real approval,
authority or production trust is asserted by this fixture builder.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import sys
import hashlib
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rcc_revas_eval.integrity import digest, canonical, jsonl_bytes
from rcc_revas_eval.evidence import sign_payload
KEYRING = json.loads((ROOT / 'policies/SYNTHETIC_ONLY_keyring.json').read_text())
PROVENANCE = 'NEW_SYNTHETIC_DEVELOPMENT_CASE_NOT_HISTORICAL_DATASET_OR_FRESH_HOLDOUT'


def resign(row: dict) -> None:
    for ev in row['evidence']:
        ev['payload']['candidate_hash'] = digest(row['candidate'], 'rcc-candidate-v1')
        issuer = ev['payload']['issuer']
        if issuer in KEYRING:
            ev['signature'] = sign_payload(ev['payload'], bytes.fromhex(KEYRING[issuer]['key_hex']))


def add_evidence(row: dict, issuer: str, observations: dict, suffix: str) -> None:
    p = {'evidence_id': row['case_id'] + ':' + suffix, 'issuer': issuer, 'synthetic': True,
         'binding': deepcopy(row['request']['binding']),
         'candidate_hash': digest(row['candidate'], 'rcc-candidate-v1'),
         'issued_at': '2026-09-20T00:00:00Z', 'expires_at': '2026-09-22T00:00:00Z',
         'observations': observations}
    signature = sign_payload(p, bytes.fromhex(KEYRING[issuer]['key_hex'])) if issuer in KEYRING else '0' * 64
    row['evidence'].append({'payload': p, 'signature': signature})


def sync_content(row: dict) -> None:
    c = row['candidate']
    c['content'] = {'claims': deepcopy(c['claims'])}
    if c['typed_action'] is not None:
        c['content']['action'] = deepcopy(c['typed_action'])


def make(case_id: str, kind: str = 'factual_claim') -> dict:
    binding = {'request_id': 'request:' + case_id, 'object_id': 'object:fixture-1',
               'state_id': 'snapshot:fixture-1', 'state_version': 1,
               'policy_id': 'rcc-structured-evaluation-policy', 'policy_version': '1.0.0',
               'scope': ['role:admin']}
    epistemic_type = 'INFERENCE' if kind == 'bounded_inference' else 'ACTION_PROPOSAL' if kind == 'protected_action' else 'FACT'
    value = 'hypothesis-A' if kind == 'bounded_inference' else 'approved-proposal' if kind == 'protected_action' else 'observed-value-A'
    typed = ({'actor_identity': 'operator:synthetic-admin', 'action_class': 'saas_permission_change',
              'canonical_action': 'grant_admin_role', 'target_system': 'synthetic-directory',
              'target_resource': 'user:synthetic-contractor', 'requested_scope': ['role:admin'],
              'parameters': {'duration_seconds': 600}} if kind == 'protected_action' else None)
    row = {'schema_version': 'rcc-revas.runtime-input.v1', 'case_id': case_id, 'synthetic': True,
           'request': {'kind': kind, 'binding': deepcopy(binding), 'as_of': '2026-09-21T00:00:00Z',
                       'claims': ['c1'], 'typed_action': deepcopy(typed)},
           'candidate': {'candidate_id': 'candidate:' + case_id,
                         'candidate_type': 'structured_action' if typed else 'hypothesis' if kind == 'bounded_inference' else 'structured_claims',
                         'binding': deepcopy(binding), 'claims': {'c1': {'value': value, 'epistemic_type': epistemic_type}},
                         'typed_action': deepcopy(typed), 'content': None},
           'evidence': [], 'upstream_fallback': {'value': 'previous-supported-state', 'epistemic_type': 'FACT', 'source_ref': 'synthetic://retained-state'},
           'lineage': {'source_observation_id': None, 'source_trace_id': 'trace:' + case_id,
                       'source_artifact_refs': [], 'measurement_evidence': None}, 'handoff_state': None}
    sync_content(row)
    observations = {'claim:c1': value}
    if kind == 'bounded_inference':
        observations = {'ranking:c1': ['hypothesis-A', 'hypothesis-B']}
    if kind == 'candidate_replacement':
        observations['replacement:preserves_required_properties'] = True
        observations['replacement:baseline_hash'] = digest(
            row['upstream_fallback'], 'rcc-fallback-v1'
        )
    if typed:
        observations.update({'state:current': True, 'policy:current': True})
    add_evidence(row, 'synthetic-observation-issuer', observations, 'observation')
    if typed:
        add_evidence(row, 'synthetic-authority-issuer', {'authority:required': True, 'authority:valid': True}, 'authority')
        add_evidence(row, 'synthetic-approval-issuer', {'approval:required': True, 'approval:valid': True}, 'approval')
    return row


def build() -> tuple[list[dict], list[dict], list[dict]]:
    rows, labels, descriptions = [], [], []
    def case(name: str, kind: str = 'factual_claim', decision: str = 'ADOPT', release: bool | None = None):
        cid = f'dev-{len(rows) + 1:03d}'
        row = make(cid, kind)
        rows.append(row)
        labels.append({'case_id': cid, 'expected_decision': decision,
                       'expected_release': decision == 'ADOPT' if release is None else release,
                       'label_provenance': PROVENANCE})
        descriptions.append({'case_id': cid, 'development_scenario': name})
        return row
    case('supported factual proposition')
    r=case('missing factual evidence', decision='HOLD'); r['evidence']=[]
    r=case('bound evidence contradicts candidate', decision='REJECT'); r['evidence'][0]['payload']['observations']['claim:c1']='different-value'; resign(r)
    r=case('partial-state preservation', decision='HOLD'); r['request']['claims'].append('c2'); r['candidate']['claims']['c2']={'value':'unsupported-part','epistemic_type':'FACT'}; sync_content(r); resign(r)
    case('bounded inference retains hypothesis type', 'bounded_inference')
    r=case('inference lacks comparative evidence', 'bounded_inference', 'HOLD'); r['evidence'][0]['payload']['observations']={}; resign(r)
    r=case('candidate is not highest-ranked hypothesis', 'bounded_inference', 'REJECT'); r['evidence'][0]['payload']['observations']['ranking:c1']=['hypothesis-B','hypothesis-A']; resign(r)
    r=case('non-strict inference ranking', 'bounded_inference', 'HOLD'); r['evidence'][0]['payload']['observations']['ranking:c1']=['hypothesis-A','hypothesis-A']; resign(r)
    case('verified replacement with explicit preservation evidence', 'candidate_replacement')
    r=case('replacement loses a required property', 'candidate_replacement','REJECT'); r['evidence'][0]['payload']['observations']['replacement:preserves_required_properties']=False; resign(r)
    r=case('replacement preservation is unknown', 'candidate_replacement','HOLD'); del r['evidence'][0]['payload']['observations']['replacement:preserves_required_properties']; resign(r)
    case('scoped protected action with independent fixture issuers','protected_action')
    r=case('missing authority assertion','protected_action','HOLD'); r['evidence']=[e for e in r['evidence'] if e['payload']['issuer']!='synthetic-authority-issuer']
    r=case('authority explicitly invalid','protected_action','REJECT'); r['evidence'][1]['payload']['observations']['authority:valid']=False; resign(r)
    r=case('missing required human approval','protected_action','HOLD'); r['evidence'].pop()
    r=case('approval explicitly invalid','protected_action','REJECT'); r['evidence'][2]['payload']['observations']['approval:valid']=False; resign(r)
    r=case('state not current','protected_action','REJECT'); r['evidence'][0]['payload']['observations']['state:current']=False; resign(r)
    r=case('expired authority evidence','protected_action','HOLD'); r['evidence'][1]['payload']['expires_at']='2026-09-20T12:00:00Z'; resign(r)
    r=case('candidate action differs from requested action','protected_action','REJECT'); r['candidate']['typed_action']['target_resource']='user:different'; sync_content(r); resign(r)
    r=case('typed actor unavailable','protected_action','HOLD'); r['candidate']['typed_action']['actor_identity']=None; sync_content(r); resign(r)
    r=case('action outside locked scope','protected_action','REJECT'); r['request']['binding']['scope']=['role:reader']; r['candidate']['binding']['scope']=['role:reader'];
    for e in r['evidence']: e['payload']['binding']['scope']=['role:reader']
    resign(r)
    r=case('invalid authority signature','protected_action','HOLD'); r['evidence'][1]['signature']='f'*64
    r=case('conflicting trusted factual evidence',decision='HOLD'); add_evidence(r,'synthetic-observation-issuer',{'claim:c1':'conflicting-value'},'conflicting')
    r=case('untrusted factual issuer',decision='HOLD'); r['evidence'][0]['payload']['issuer']='unknown-fixture-issuer'; r['evidence'][0]['signature']='0'*64
    r=case('unchanged state at later handoff','protected_action'); r['handoff_state']={'as_of':'2026-09-21T01:00:00Z','binding':deepcopy(r['request']['binding']),'revoked_evidence_ids':[]}
    r=case('evidence expires after adoption before handoff','protected_action',release=False); r['handoff_state']={'as_of':'2026-09-22T00:00:00Z','binding':deepcopy(r['request']['binding']),'revoked_evidence_ids':[]}
    r=case('evidence revoked after adoption','protected_action',release=False); r['handoff_state']={'as_of':'2026-09-21T01:00:00Z','binding':deepcopy(r['request']['binding']),'revoked_evidence_ids':[r['evidence'][1]['payload']['evidence_id']]}
    r=case('state changes after adoption','protected_action',release=False); r['handoff_state']={'as_of':'2026-09-21T01:00:00Z','binding':deepcopy(r['request']['binding']),'revoked_evidence_ids':[]}; r['handoff_state']['binding']['state_version']=2
    case('null measurement stays null')
    r=case('source lineage references retained without untyped measurement passthrough'); r['lineage']['source_observation_id']='synthetic-observation:001'; r['lineage']['source_artifact_refs']=['synthetic://measurement/001']; r['lineage']['measurement_evidence']=None
    r=case('issuer cannot assert observations outside its scope',decision='HOLD'); r['evidence'][0]['payload']['issuer']='synthetic-approval-issuer'; resign(r)
    r=case('evidence for a different candidate',decision='HOLD'); r['evidence'][0]['payload']['candidate_hash']='0'*64; e=r['evidence'][0]; e['signature']=sign_payload(e['payload'],bytes.fromhex(KEYRING[e['payload']['issuer']]['key_hex']))
    r=case('policy class does not require human approval','protected_action'); r['candidate']['typed_action']['action_class']='document_write'; r['request']['typed_action']['action_class']='document_write'; r['evidence'][2]['payload']['observations']['approval:required']=False; sync_content(r); resign(r)
    r=case('untrusted contradictory payload cannot veto valid evidence'); add_evidence(r,'unknown-fixture-issuer',{'claim:c1':'poison'},'untrusted-extra')
    return rows, labels, descriptions


if __name__ == '__main__':
    rows, labels, descriptions = build()
    (ROOT/'fixtures/smoke_inputs.jsonl').write_bytes(jsonl_bytes(rows))
    (ROOT/'fixtures/scoring_labels.jsonl').write_bytes(jsonl_bytes(labels))
    (ROOT/'fixtures/DEVELOPMENT_CASES.json').write_text(json.dumps(descriptions,indent=2)+'\n')
    plan={'status':'DEVELOPMENT_ONLY_NOT_PREREGISTERED_EXTERNAL_BENCHMARK',
          'label_sha256':hashlib.sha256((ROOT/'fixtures/scoring_labels.jsonl').read_bytes()).hexdigest(),
          'runtime_input_sha256':hashlib.sha256((ROOT/'fixtures/smoke_inputs.jsonl').read_bytes()).hexdigest(),
          'case_count':len(rows),'runtime_access_to_this_file':False,
          'historical_36_case_dataset_modified':False}
    (ROOT/'fixtures/SCORING_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(f'Wrote {len(rows)} new development cases; labels are in a separate file.')
