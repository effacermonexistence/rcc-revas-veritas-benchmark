import json
import pytest
from tests import support_plugins as p
from rveval.canonical import sha_json

@pytest.mark.parametrize("mode",["live","dual","fixed_replay"])
def test_modes_execute(mode,run_config):
    m,rows,*_=run_config(mode=mode)
    assert m["status"]=="COMPLETED" and len(rows)==1
    assert (rows[0]["arm_b"] is not None)==(mode!="fixed_replay")
    assert (rows[0]["fixed_replay"] is not None)==(mode!="live")
@pytest.mark.parametrize("stage",["rcc","veritas"])
@pytest.mark.parametrize("disposition",["ERROR","UNSUPPORTED"])
def test_gate_error_not_governance_refusal(stage,disposition,run_config):
    m,rows,*_=run_config(**{stage:disposition})
    assert m["status"]=="COMPLETED_WITH_ERRORS_OR_UNSUPPORTED"
    arm=rows[0]["arm_a" if stage=="rcc" else "arm_b"]
    assert arm["termination"]==("UNSUPPORTED" if disposition=="UNSUPPORTED" else "INFRASTRUCTURE_ERROR")
    assert not arm["steps"][0]["apply_attempted"]
    assert rows[0]["native_comparison"]["status"]=="INVALID_OR_UNSUPPORTED_PAIR_NO_DELTA"
@pytest.mark.parametrize("benchmark",["initial_mismatch","same_session"])
def test_pairing_checked_before_any_apply(benchmark,run_config):
    m,rows,*_=run_config(benchmark=benchmark)
    assert p.APPLY_COUNT==0 and not rows[0]["pairing_valid"]
    assert m["status"]!="COMPLETED"
@pytest.mark.parametrize("kwargs",[{"agent":"mutation"},{"rcc":"mutation"},{"rcc":"context_mutation"},{"veritas":"mutation"},{"benchmark":"mutate_candidate"}])
def test_mutation_rejected(kwargs,run_config):
    m,rows,*_=run_config(**kwargs);assert m["status"]!="COMPLETED"
    assert any((rows[0][a] or {}).get("integrity_errors") for a in ("arm_a","arm_b"))
def test_private_pairing_snapshot_not_sent_to_gates(run_config):
    m,rows,*_=run_config(agent="no_leak");assert m["status"]=="COMPLETED"
    assert rows[0]["arm_a"]["steps"][0]["pre_state"]["gold"]=="scoring only"
    assert "gold" not in str(rows[0]["arm_a"]["steps"][0]["treatment_context"])
@pytest.mark.parametrize("kwargs",[{"rcc":"leak"},{"benchmark":"observation_leak"}])
def test_dynamic_label_leak_blocked(kwargs,run_config):
    m,rows,*_=run_config(**kwargs);assert m["status"]!="COMPLETED"
def test_mutable_snapshot_detached_before_apply(run_config):
    m,rows,*_=run_config(benchmark="mutable_snapshot");assert m["status"]=="COMPLETED"
    step=rows[0]["arm_a"]["steps"][0]
    assert step["pre_state"]["v"]==0 and sha_json(step["pre_state"])==step["pre_state_sha256"]
def test_both_arms_and_replay_complete_before_score(run_config):
    m,rows,*_=run_config(agent="assert_no_score",veritas="assert_no_score")
    assert m["status"]=="COMPLETED" and p.SCORE_CALLED

def test_fixed_replay_exact_context_and_replacement_candidate(run_config):
    m,rows,*_=run_config(rcc="replacement");assert m["status"]=="COMPLETED"
    step=rows[0]["arm_a"]["steps"][0];replay=rows[0]["fixed_replay"]["events"][0]
    assert step["rcc"]["adopted_candidate"]["name"]=="different"
    assert replay["candidate_sha256"]==step["rcc_adopted_candidate_sha256"]
    assert replay["context_sha256"]==sha_json(step["veritas_context"])
    assert replay["pair_binding_verified"]

def test_stateful_gate_without_replay_restore_not_claimed(run_config):
    m,rows,*_=run_config(stateful=True)
    assert m["status"]!="COMPLETED"
    assert rows[0]["fixed_replay"]["events"][0]["infrastructure_error"]["category"]=="UNSUPPORTED"

def test_apply_failure_keeps_unknown_effect_and_intent(run_config):
    m,rows,out,*_=run_config(benchmark="apply_error")
    step=rows[0]["arm_a"]["steps"][0]
    assert step["effect_status"]=="UNKNOWN_AFTER_ATTEMPT" and step["apply_attempted"]
    assert "APPLY_INTENT" in (out/"journal.jsonl").read_text()
    assert "never_report_me" not in "".join(x.read_text() for x in out.glob("*.json"))
@pytest.mark.parametrize("benchmark",["open_error","score_error"])
def test_failures_preserve_enrollment(benchmark,run_config):
    m,rows,*_=run_config(benchmark=benchmark,trials=2)
    assert m["enrolled"]==2 and len(rows)==2 and m["status"]!="COMPLETED"

def test_trials_have_independent_generators(run_config):
    m,rows,*_=run_config(trials=3)
    assert m["status"]=="COMPLETED" and [r["seed"] for r in rows]==[7,8,9]
    assert all(r[a]["steps"][0]["candidate"]["arguments"]["n"]==1 for r in rows for a in ("arm_a","arm_b"))
def test_dynamic_tool_schema_refreshed_each_step(run_config):
    m,rows,*_=run_config(benchmark="two_steps",agent="dynamic_tools")
    assert m["status"]=="COMPLETED" and len(rows[0]["arm_b"]["steps"])==2

def test_hold_feedback_bounded_not_infinite(run_config):
    m,rows,*_=run_config(rcc="HOLD",stop="feedback")
    assert m["status"]=="COMPLETED" and len(rows[0]["arm_a"]["steps"])==3
    assert rows[0]["arm_a"]["termination"]=="MAX_STEPS"
