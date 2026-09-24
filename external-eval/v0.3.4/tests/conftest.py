import json
from pathlib import Path
import pytest
from rveval.freeze import freeze
from rveval.canonical import sha_file,read_json
from rveval.runner import execute
from tests import support_plugins as p

@pytest.fixture(autouse=True)
def reset_globals():
    p.SCORE_CALLED=False;p.APPLY_COUNT=0

@pytest.fixture
def run_config(tmp_path):
    def run(*,mode="dual",benchmark="ok",agent="ok",rcc="ok",veritas="ALLOW",trials=1,stateful=False,stop="terminate"):
        cfg={"run_mode":mode,"seed":7,"trials":trials,
             "benchmark":{"plugin":"tests.support_plugins:Adapter","config":{"mode":benchmark}},
             "agent":{"plugin":"tests.support_plugins:AgentImpl","config":{"mode":agent}},
             "rcc":{"plugin":"tests.support_plugins:Gate","config":{"mode":rcc}},
             "veritas":{"plugin":"tests.support_plugins:VGate","config":{"mode":veritas,"stateful":stateful}},
             "policy":{"max_steps":3,"on_governance_stop":stop}}
        folder=tmp_path/str(len(list(tmp_path.iterdir())));folder.mkdir()
        path=folder/"config.json";path.write_text(json.dumps(cfg))
        fp=folder/"freeze.json";freeze(path,fp);out=folder/"run"
        manifest=execute(path,fp,sha_file(fp),out)
        rows=[read_json(x) for x in sorted(out.glob("case_*.json"))]
        return manifest,rows,out,path,fp
    return run
