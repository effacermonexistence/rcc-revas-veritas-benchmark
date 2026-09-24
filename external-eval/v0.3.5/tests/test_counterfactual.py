from copy import deepcopy
from pathlib import Path
from rveval.counterfactual import paired_effect_counterfactual
from rveval.models import CandidateAction,RCCDecision
from rveval.governance.passthrough import AllowAllVeritas,DenyNamedActionVeritas

def run(gate,**kwargs):
    def apply(env,c):env["value"]+=c.arguments["n"];return {"value":env["value"]}
    base=dict(rcc_decision=RCCDecision("ADOPT",CandidateAction("tool_call",name="increment",arguments={"n":1})),
              context={"task":{"intent":"increment"}},pre_state={"value":0},
              environment_factory=deepcopy,snapshotter=deepcopy,apply_candidate=apply,veritas=gate)
    base.update(kwargs);return paired_effect_counterfactual(**base)
def test_effect_pair_both_native_apply_on_same_checkpoint():
    r=run(AllowAllVeritas({},Path('.')))
    assert r['status']=='COMPLETED' and r['same_pre_state']
    assert r['arm_a']['effect_observed'] and r['arm_b']['effect_observed']
    assert r['whole_task_treatment_score'] is None

def test_effect_pair_actual_divergence_without_model_regeneration():
    r=run(DenyNamedActionVeritas({'deny_name':'increment'},Path('.')))
    assert r['status']=='COMPLETED' and r['arm_a']['effect_observed'] and not r['arm_b']['apply_attempted']
    assert not r['model_regeneration_performed']

def test_effect_pair_alias_rejected_before_application():
    env={'value':0};r=run(AllowAllVeritas({},Path('.')),environment_factory=lambda p:env)
    assert r['status']=='INCOMPLETE_OR_INVALID' and r['arm_a'] is None and env['value']==0

def test_effect_pair_invalid_clone_rejected():
    r=run(AllowAllVeritas({},Path('.')),environment_factory=lambda p:{'value':1})
    assert r['status']=='INCOMPLETE_OR_INVALID' and not r['same_pre_state']

def test_effect_pair_failed_apply_stays_unknown():
    def fail(env,c):env['value']=1;raise RuntimeError('secret')
    r=run(AllowAllVeritas({},Path('.')),apply_candidate=fail)
    assert r['status']=='INCOMPLETE_OR_INVALID' and r['arm_a']['effect_observed'] is None
    assert 'secret' not in str(r)
