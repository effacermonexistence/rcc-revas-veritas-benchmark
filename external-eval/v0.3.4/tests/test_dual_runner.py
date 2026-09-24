from pathlib import Path
from rveval.freeze import freeze
from rveval.runner import execute
from rveval.canonical import sha_file,read_json
def test_example_dual_run(tmp_path):
    root=Path(__file__).parents[1]; cfg=root/"examples/static_jsonl/config.json"; fr=tmp_path/"freeze.json"; out=tmp_path/"run"; freeze(cfg,fr); execute(cfg,fr,sha_file(fr),out); m=read_json(out/"run_manifest.json"); assert m["case_count"]==2 and m["run_mode"]=="dual"; g=read_json(out/"governance_metrics.json"); assert g["live_veritas_dispositions"]["ALLOW"]==2
