"""A self-consistent digest must not authorize an inconsistent known predicate."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import pytest
from rveval.canonical import sha_file, sha_json
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.models import CandidateAction
from rveval.partner_mapping import build_runtime_packet, verify_runtime_packet
from rveval.guardrails import IntegrityError

ROOT=Path(__file__).resolve().parents[1]


def make():
    path=ROOT/'policies/external-output-contract.v0.3.json'
    c=CandidateAction('final_answer',content=1)
    d=ExternalRCCGate({'policy':str(path),'policy_sha256':sha_file(path)},ROOT).review(candidate=c,context={'task':{'classes':[1]}})
    return build_runtime_packet(candidate=c,rcc_decision=d,request={'id':'request','query':'independent','source_ref':'user'},source_refs=[],produced_at=datetime.now(timezone.utc))


def rehash_every_layer(packet):
    d=packet['payload']['upstream_adoption'];e=d['evidence'];h=d['handoff'];body=e['decision'];digest=sha_json(body)
    e['decision_lock']['sha256']=digest;e['decision_lock']['decision_id']='rcc-external:'+digest
    h['upstream_decision_sha256']=digest;h['upstream_decision_id']='rcc-external:'+digest
    h['verification']=deepcopy(body['verification'])
    packet['payload']['identities']['rcc_decision_sha256']=sha_json(d)
    packet['payload_sha256']=sha_json(packet['payload'])


@pytest.mark.parametrize('mutation',['empty_checks','optional_only','required_hold','rejected','no_evidence','authority_true','generated_true','claim_mismatch'])
def test_known_adoption_cannot_contradict_its_own_predicates(mutation):
    p=make();d=p['payload']['upstream_adoption'];body=d['evidence']['decision']
    if mutation=='empty_checks':body['verification']=[]
    elif mutation=='optional_only':
        for check in body['verification']:check['required']=False
    elif mutation=='required_hold':body['verification'][0]['report']['status']='HOLD'
    elif mutation=='rejected':body['verification'][0]['report']['status']='REJECT'
    elif mutation=='no_evidence':body['verification'][0]['report']['evidence_refs']=[]
    elif mutation=='authority_true':body['execution_authority_conferred']=True
    elif mutation=='generated_true':body['candidate_generated_by_gate']=True
    else:d['handoff']['claim_scope']='unrelated stronger claim'
    rehash_every_layer(p)
    with pytest.raises(IntegrityError):verify_runtime_packet(p)
