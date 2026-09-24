import json
from pathlib import Path
import pytest
from rveval.canonical import loads,canonical_bytes,sha_file,read_json,write_json_new
from rveval.freeze import freeze,verify_freeze,validate_config
from rveval.models import CandidateAction,RCCDecision,VeritasDecision
from rveval.guardrails import IntegrityError,assert_no_scorer_truth
from rveval.evidence import verify_evidence,write_evidence_index

@pytest.mark.parametrize("raw",['{"a":1,"a":2}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'])
def test_json_rejects_ambiguous_wire(raw):
    with pytest.raises((ValueError,IntegrityError)):loads(raw)
@pytest.mark.parametrize("value",[float("nan"),float("inf"),{1:"bad"}])
def test_hash_rejects_nonfinite_and_nonstring_key(value):
    with pytest.raises((ValueError,TypeError,IntegrityError)):canonical_bytes(value)
@pytest.mark.parametrize("key",["gold","goldLabel","Expected Decision","scorer-output","answer_key"])
def test_gold_spellings_rejected(key):
    with pytest.raises(IntegrityError):assert_no_scorer_truth({"nested":[{key:"x"}]})
def test_known_unknown_states_not_rewritten():
    assert_no_scorer_truth({"approval_required":None,"expected_state_fresh":False})
@pytest.mark.parametrize("call",[lambda:CandidateAction("nonsense"),lambda:RCCDecision("ADOPT",None),lambda:RCCDecision("HOLD",CandidateAction("final_answer",content=1)),lambda:VeritasDecision("MAYBE")])
def test_invalid_decision_shapes_fail(call):
    with pytest.raises((ValueError,IntegrityError)):call()
def test_frozen_wire_detached_from_mutable_data():
    c=CandidateAction("tool_call",name="x",arguments={"n":1});d=c.to_dict();d["arguments"]["n"]=9
    assert c.arguments["n"]==1

def test_config_bytes_change_after_freeze(run_config):
    _,_,_,path,fp=run_config()
    path.write_text(path.read_text()+" ")
    with pytest.raises(IntegrityError):verify_freeze(path,fp,sha_file(fp))
def test_declared_asset_change_rejected(tmp_path):
    root=Path(__file__).resolve().parents[1]
    cfg=json.loads((root/"examples/static_jsonl/config.json").read_text())
    # Freeze file source closure independently of any plugin self-reported version.
    cfg["benchmark"]["config"]["cases_path"]=str(root/"examples/static_jsonl/cases.jsonl")
    cfg["benchmark"]["config"]["labels_path"]=str(root/"examples/static_jsonl/labels.jsonl")
    cfg["agent"]["config"]["actions_path"]=str(root/"examples/static_jsonl/actions.json")
    asset=tmp_path/"image.bin";asset.write_bytes(b"first");cfg["assets"]=["image.bin"]
    path=tmp_path/"config.json";path.write_text(json.dumps(cfg));fp=tmp_path/"freeze.json";freeze(path,fp)
    asset.write_bytes(b"second")
    with pytest.raises(IntegrityError):verify_freeze(path,fp,sha_file(fp))
def test_plugin_source_change_even_identity_constant(run_config,monkeypatch):
    _,_,_,path,fp=run_config()
    from rveval import freeze as module
    old=module.plugin_identity
    monkeypatch.setattr(module,"plugin_identity",lambda spec:{**old(spec),"changed_helper_bytes":True})
    with pytest.raises(IntegrityError):verify_freeze(path,fp,sha_file(fp))
def test_confirmatory_rejects_demo(run_config):
    _,_,_,path,_=run_config();cfg=json.loads(path.read_text())
    cfg.update(study_kind="EXTERNAL_CONFIRMATORY",source_files=["config.json"],contract_path="contract.json",
               study={k:"declared" for k in ["benchmark_source","model_configuration","native_scorer","treatment_boundary","case_selection","exposure_history","isolation_profile"]})
    (path.parent/"contract.json").write_text("{}");path.write_text(json.dumps(cfg))
    with pytest.raises(IntegrityError):freeze(path,path.parent/"confirm.json")
@pytest.mark.parametrize("change",[{"run_mode":"typo"},{"seed":True},{"trials":0},{"policy":{"max_steps":0}},{"policy":{"on_governance_stop":"allow"}}])
def test_invalid_config_rejected(change):
    cfg={k:{"plugin":"x:y"} for k in ("benchmark","agent","rcc","veritas")};cfg.update(change)
    with pytest.raises(IntegrityError):validate_config(cfg)
def test_evidence_tamper_and_closure(run_config):
    _,_,out,_,_=run_config();pin=sha_file(out/"evidence_index.json")
    assert verify_evidence(out,pin)["status"]=="PASS"
    (out/"extra.txt").write_text("unexpected")
    with pytest.raises(IntegrityError):verify_evidence(out,pin)
def test_journal_chain_not_just_index_hash(run_config):
    _,_,out,_,_=run_config();lines=(out/"journal.jsonl").read_text().splitlines()
    x=json.loads(lines[0]);x["payload"]["case_count"]=100;lines[0]=json.dumps(x)
    (out/"journal.jsonl").write_text("\n".join(lines)+"\n")
    (out/"evidence_index.json").unlink();write_evidence_index(out)
    with pytest.raises(IntegrityError):verify_evidence(out,sha_file(out/"evidence_index.json"))
def test_writeonce_and_invalid_value_does_not_create(tmp_path):
    p=tmp_path/"x.json"
    with pytest.raises((ValueError,IntegrityError)):write_json_new(p,{"x":float("nan")})
    assert not p.exists()
    write_json_new(p,{"x":1})
    with pytest.raises(FileExistsError):write_json_new(p,{"x":2})
