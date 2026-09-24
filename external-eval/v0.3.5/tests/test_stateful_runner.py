from pathlib import Path
from rveval.freeze import freeze
from rveval.runner import execute
from rveval.canonical import sha_file,read_json

def test_live_divergence_and_fixed_replay_are_separate(tmp_path):
    root=Path(__file__).parents[1]; cfg=root/"examples/stateful/config.json"; fr=tmp_path/"freeze.json"; out=tmp_path/"run"
    freeze(cfg,fr); execute(cfg,fr,sha_file(fr),out)
    case=read_json(out/"case_00000.json")
    assert case["arm_a"]["initial_state_sha256"]==case["arm_b"]["initial_state_sha256"]
    assert case["arm_a"]["native_score"]["value"]==1
    assert case["arm_b"]["native_score"]["value"]==0
    assert case["fixed_replay"]["events"][0]["veritas"]["disposition"]=="DENY"
    gov=read_json(out/"governance_metrics.json")
    assert gov["fixed_replay_veritas_dispositions"]["DENY"]==2
