"""Do not regress already-published policy checks while publishing pilot fixes."""
from copy import deepcopy
import inspect
from pathlib import Path
import pytest
from rveval.canonical import sha_file, write_json_new
from rveval.guardrails import IntegrityError
from rveval.models import CandidateAction
from rveval.integrations.rcc_external import ExternalRCCGate, verify_output_contract

def make_policy(tmp_path, checks):
    path = tmp_path / "policy.json"
    write_json_new(path, {
        "policy_id": "publication-check", "version": "1",
        "supported_kinds": ["final_answer"], "checks": checks,
        "claim_scope": "STRUCTURE_ONLY"
    })
    return path

def check(required=True):
    return {
        "check_id": "output", "callable": "rveval.integrations.rcc_external:verify_output_contract",
        "source_sha256": sha_file(Path(inspect.getsourcefile(verify_output_contract))),
        "required": required
    }

@pytest.mark.parametrize("checks", [[], [check(False)]])
def test_empty_or_optional_only_policy_refused(tmp_path, checks):
    path = make_policy(tmp_path, checks)
    with pytest.raises(IntegrityError):
        ExternalRCCGate({"policy": path.name, "policy_sha256": sha_file(path)}, tmp_path)

def test_in_memory_policy_change_refused(tmp_path):
    path = make_policy(tmp_path, [check()])
    gate = ExternalRCCGate({"policy": path.name, "policy_sha256": sha_file(path)}, tmp_path)
    gate.policy["checks"] = []
    with pytest.raises(IntegrityError, match="EXTERNAL_RCC_POLICY_MEMORY_CHANGED"):
        gate.review(candidate=CandidateAction("final_answer", content=1), context={"task": {"classes": [1]}})
