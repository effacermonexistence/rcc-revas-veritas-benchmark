#!/usr/bin/env python3
"""Runnable native RCC -> signed AuthorityEvidence -> native Bind sandbox.

No production permissions or API keys. Test-only key, action contract, policy and
logical clock are explicit inputs of this reproducible engineering scenario.
Native VERITAS source is imported from the caller's pinned checkout. The original
0.1 RCC release is not changed; the new external RCC runtime is used here.
"""
from __future__ import annotations
import argparse,base64,inspect,json,os
from datetime import datetime,timezone
from pathlib import Path
from copy import deepcopy
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from veritas_os.governance.action_contracts import ActionClassContract
from veritas_os.governance.authority_evidence import (
    AuthorityEvidence,AuthorityEvidenceSignerPolicy,ApprovedAuthorityEvidenceVerifier,
    AuthorityEvidenceVerifierPolicy,AuthorityRevocationPolicy,authority_signature_payload)
from veritas_os.policy.bind_artifacts import ExecutionIntent
from veritas_os.policy.bind_core import execute_bind_adjudication
from veritas_os.security.hash import sha256_of_canonical_json
from rveval.canonical import sha_file,sha_json
from rveval.native_hook import NativeGovernanceHook
from rveval.models import CandidateAction
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.integrations.veritas_bind import NativeBindExecutor
from rveval.integrations.boundary import GovernanceStop
from rveval.integrations.ledger import OperationLedger
from rveval.integrations.veritas_authority import Ed25519AuthorityVerifier,PinnedRevocations,NativeAuthorityResolver

ROOT=Path(__file__).resolve().parents[2]


def run(output:Path, *, mode:str):
    output.mkdir(parents=True,exist_ok=False)
    os.environ['VERITAS_POSTURE']='secure'
    state={'counter':0};records=[]
    log=output/'journal.jsonl'
    def journal(event,payload):
        record={'sequence':len(records),'event':event,'payload':deepcopy(payload)}
        encoded=json.dumps(record,sort_keys=True,allow_nan=False)+'\n'
        with log.open('a') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
        records.append(record)
    policy=ROOT/'policies/external-output-contract.v0.3.json'
    rcc=ExternalRCCGate({'policy':str(policy),'policy_sha256':sha_file(policy)},ROOT)
    contract=ActionClassContract(id='sandbox-counter-increment',version='1',domain='local-benchmark',
        action_class='local-effect',description='Increment one isolated local counter',declared_intent='increment',
        allowed_scope=['counter:increment'],prohibited_scope=['production:*'],authority_sources=['local-test-operator'],
        required_evidence=[],evidence_freshness={},irreversibility={'boundary':'isolated-local-state'},
        human_approval_rules={'required':False},refusal_conditions=[],escalation_conditions=[],
        default_failure_mode='block',metadata={'test_only':True,'clock':'FROZEN_LOGICAL_TIME'})
    actor='sandbox-test-operator';pid='sandbox-counter-policy'
    start='2026-09-23T00:00:00Z';end='2026-09-24T00:00:00Z'
    evidence=AuthorityEvidence(authority_evidence_id='sandbox-grant',action_contract_id=contract.id,
        action_contract_version=contract.version,actor_identity=actor,actor_role='benchmark-operator',
        authority_source_refs=['local-test-operator'],role_or_policy_basis=[pid],scope_grants=['counter:increment'],scope_limitations=[],
        validity_window={'issued_at':start,'valid_from':start,'valid_until':end},issued_at=start,valid_from=start,valid_until=end,
        policy_snapshot_id=pid,action_contract_hash=contract.deterministic_digest())
    key=Ed25519PrivateKey.generate()
    artifact={'artifact_type':'authority_evidence','artifact_version':'v1','claims':evidence.claims_dict(),
        'claims_hash':sha256_of_canonical_json(evidence.claims_dict()),'signed_at':start,
        'signer':{'key_id':'sandbox-key','algorithm':'Ed25519'},'issuer_identity':'sandbox-issuer'}
    artifact['signature']=base64.b64encode(key.sign(authority_signature_payload(artifact).encode())).decode()
    if mode=='tampered':artifact['claims']['scope_grants'].append('production:*')
    signer=AuthorityEvidenceSignerPolicy('sandbox-signers',['sandbox-key'],['Ed25519'],['sandbox-issuer'])
    # This is an explicit local policy, not an invented real-world trust root.
    verifier_policy_record={'purpose':'local-test-only','key_id':'sandbox-key','algorithm':'Ed25519'}
    vph=sha_json(verifier_policy_record)
    public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    verifier=Ed25519AuthorityVerifier(public_key=public,key_id='sandbox-key',issuer_identity='sandbox-issuer',
        verifier_id='sandbox-verifier',verifier_policy_id='sandbox-verifier-policy',verifier_policy_hash=vph,trust_level='development')
    vp=AuthorityEvidenceVerifierPolicy([ApprovedAuthorityEvidenceVerifier(verifier_id='sandbox-verifier',trust_level='development',
        verifier_key_id='sandbox-key',verifier_policy_id='sandbox-verifier-policy',verifier_policy_hash=vph,
        signer_policy_id=signer.policy_id,signer_policy_hash=signer.deterministic_hash())])
    rev=output/'revocations.json';rev.write_text(json.dumps({'as_of':start,'source_identity':'sandbox-revocations',
        'version':'1','status_by_id':{'sandbox-grant':mode=='revoked'}})+'\n')
    resolver=NativeAuthorityResolver(binding_provider=lambda i,s:{'action_contract':contract,'authority_artifact':artifact,
        'requested_scope':['counter:increment'],'required_evidence_metadata':{},'bind_context_metadata':{'valid':True}},
        signature_verifier=verifier,signer_policy=signer,verifier_policy=vp,
        revocation_checker=PinnedRevocations(rev,sha_file(rev)),revocation_policy=AuthorityRevocationPolicy(60,['sandbox-revocations']),
        clock=lambda:datetime(2026,9,23,0,0,1,tzinfo=timezone.utc),journal=journal)
    def intent(candidate,pre,rcc_review):
        return ExecutionIntent(decision_id='upstream:'+rcc_review['evidence']['decision_lock']['decision_id'],
            request_id='sandbox-request',actor_identity=actor,policy_snapshot_id=pid,target_system='local-counter',
            target_resource='counter',intended_action='increment',decision_ts=start,
            expected_state_fingerprint=sha256_of_canonical_json(pre),
            evidence_refs=['rveval-candidate-sha256:'+sha_json(candidate.to_dict())])
    executor=NativeBindExecutor(NativeGovernanceHook(rcc),snapshot=lambda:state,
        context=lambda c:{'task':{'request':'Increment the isolated counter by 1','scope':'counter:increment'}},journal=journal,
        intent_factory=intent,authority_check=resolver,
        constraints_check=lambda i,s:{'counter_initially_zero':s['counter']==0,'declared_action':i.intended_action=='increment'},
        risk_check=lambda i,s:True,postcondition_check=lambda i,s,r:state['counter']==1 and r==1,
        revert=lambda i,s:False,target='isolated-test-counter',bind_time=lambda:'2026-09-23T00:00:01Z',
        native_core_sha256=sha_file(Path(inspect.getsourcefile(execute_bind_adjudication))),
        ledger=OperationLedger(output/'operations.sqlite'))
    def apply(candidate):
        state['counter']+=1
        return state['counter']
    try:
        result=executor.call(CandidateAction('tool_call',name='increment',arguments={'amount':1}),apply,operation_id='increment-once')
        outcome=result.receipt['native_bind_receipt']['final_outcome']
    except GovernanceStop:
        outcome='BLOCKED'
    expected='COMMITTED' if mode=='valid' else 'BLOCKED'
    ok=outcome==expected and state['counter']==(1 if mode=='valid' else 0)
    report={'status':'PASS' if ok else 'FAIL','mode':mode,'native_outcome':outcome,'final_state':state,
        'rcc_runtime':rcc.identity(),'boundary':'NEW_EXTERNAL_RCC_TO_NATIVE_AUTHORITY_TO_NATIVE_BIND_CORE',
        'test_only':True,'clock':start,'paid_provider_calls':0,'native_journal_sha256':sha_file(log),
        'authority_artifact_sha256':sha_json(artifact),'public_key_hex':public.hex(),
        'production_authority_claimed':False,'whole_VERITAS_pipeline_claimed':False}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if ok else 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['valid','tampered','revoked'],default='valid')
    a=p.parse_args();raise SystemExit(run(a.output.resolve(),mode=a.mode))
