from __future__ import annotations
import re
from typing import Any

FORBIDDEN_SCORER_KEYS = {
    "ground_truth", "gold", "gold_label", "gold_answer", "answer_key", "reference_answer",
    "expected_decision", "expected_outcome", "expected_gate_decision", "expected_bind_gate_outcome",
    "expected_handoff_state", "expected_business_decision", "expected_release", "expected_reason_codes",
    "scorer_output", "scoring_result", "scoring_label", "scoring_labels", "evaluation_label",
    "evaluation_labels", "post_lock_score", "attack_success", "is_attack", "attack_label",
}

class IntegrityError(RuntimeError):
    pass

class UnsupportedError(RuntimeError):
    """A capability gap; never reinterpret as a model/governance verdict."""

class ProtocolError(RuntimeError):
    pass

def normalize_key(k: str) -> str:
    k = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", k)
    return re.sub(r"[\s\-]+", "_", k).lower()

def assert_no_scorer_truth(value: Any, where: str = "surface") -> None:
    if isinstance(value, dict):
        bad = sorted(str(k) for k in value if normalize_key(str(k)) in FORBIDDEN_SCORER_KEYS)
        if bad: raise IntegrityError(f"SCORER_FIELD_LEAK:{where}:{','.join(bad)}")
        for k,v in value.items(): assert_no_scorer_truth(v, f"{where}.{k}")
    elif isinstance(value, (list, tuple)):
        for i,v in enumerate(value): assert_no_scorer_truth(v, f"{where}[{i}]")

def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition: raise IntegrityError(code + (f": {detail}" if detail else ""))
