"""Public Python protocol v0.2. See docs/IMPLEMENTATION_GUIDE.md for contracts."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from copy import deepcopy
from .canonical import sha_json
from .guardrails import require
from .models import CandidateAction, Observation, RCCDecision, VeritasDecision
from .guardrails import UnsupportedError

class DeferredScore(ABC):
    """Detached native final-state handle. No score may be computed during creation."""
    @abstractmethod
    def fingerprint(self) -> str: ...
    @abstractmethod
    def score(self) -> dict[str, Any]: ...
    def close(self) -> None: pass


class BenchmarkSession(ABC):
    @abstractmethod
    def task_payload(self) -> Any: ...
    @abstractmethod
    def agent_state(self) -> Any: ...
    @abstractmethod
    def pairing_state(self) -> Any: ...
    @abstractmethod
    def tool_schema(self) -> Any: ...
    @abstractmethod
    def apply(self, candidate: CandidateAction) -> Observation: ...
    @abstractmethod
    def is_terminal(self) -> bool: ...
    @abstractmethod
    def native_score(self) -> dict[str, Any]: ...
    def governance_context(self) -> Any:
        # Private evaluator state and pairing snapshots are NEVER forwarded by default.
        return {"task": self.task_payload(), "visible_state": self.agent_state(),
                "tools": self.tool_schema()}
    def snapshot(self) -> dict[str, Any]:
        # Default for paused/controlled environments. Dynamic native systems should
        # override with an atomic native snapshot or use NativeGovernanceHook.
        before = deepcopy(self.pairing_state())
        value = {"task": deepcopy(self.task_payload()),
                 "agent_state": deepcopy(self.agent_state()),
                 "tools": deepcopy(self.tool_schema()),
                 "governance_context": deepcopy(self.governance_context()),
                 "terminal": self.is_terminal(), "pairing_state": before}
        require(sha_json(self.pairing_state()) == sha_json(before),
                "STATE_CHANGED_DURING_SNAPSHOT")
        return value
    def defer_score(self) -> DeferredScore | None:
        # Native integrations can spool sealed predictions/checkpoints to disk,
        # release the expensive environment, and score only after the cohort closes.
        # None keeps this session alive for delayed scoring (document resource cost).
        return None
    def close(self) -> None: pass

class BenchmarkAdapter(ABC):
    def __init__(self, config, base_dir): self.config, self.base_dir = config, base_dir
    @abstractmethod
    def identity(self) -> dict[str, Any]: ...
    @abstractmethod
    def case_ids(self) -> list[str]: ...
    @abstractmethod
    def case_fingerprint(self, case_id: str) -> str: ...
    @abstractmethod
    def open_session(self, case_id: str, *, seed: int, arm: str) -> BenchmarkSession: ...
    def capabilities(self):
        return {"protocol": "step/v2", "modes": ["live", "fixed_replay", "dual"],
                "effects": "LOCAL_SIMULATION", "pairing_scope": "ADAPTER_DECLARED_SNAPSHOT",
                "score_phase": "AFTER_ALL_CASES_AND_TRIALS", "test_only": False}
    def compare_native_scores(self, arm_a, arm_b):
        return {"status": "BENCHMARK_ADAPTER_DID_NOT_DEFINE_COMPARISON", "arm_a": arm_a, "arm_b": arm_b}
    def aggregate_native_scores(self, cases):
        # Non-additive metrics (pass@k, corpus BLEU, etc.) stay benchmark-owned.
        return {"status": "PER_CASE_ONLY_AGGREGATE_NOT_IMPLEMENTED", "case_count": len(cases)}
    def close(self): pass

class Agent(ABC):
    def __init__(self, config, base_dir): self.config, self.base_dir = config, base_dir
    @abstractmethod
    def identity(self) -> dict[str, Any]: ...
    @abstractmethod
    def reset(self, *, case_id: str, arm: str, seed: int) -> None: ...
    @abstractmethod
    def act(self, *, task, history, state, tools) -> CandidateAction: ...
    def close(self): pass

class RCCGate(ABC):
    def __init__(self, config, base_dir): self.config, self.base_dir = config, base_dir
    @abstractmethod
    def identity(self) -> dict[str, Any]: ...
    def reset(self, *, case_id: str, arm: str, seed: int) -> None: pass
    @abstractmethod
    def review(self, *, candidate: CandidateAction, context) -> RCCDecision: ...
    def close(self): pass

class VeritasGate(ABC):
    def __init__(self, config, base_dir): self.config, self.base_dir = config, base_dir
    @abstractmethod
    def identity(self) -> dict[str, Any]: ...
    def reset(self, *, case_id: str, arm: str, seed: int) -> None: pass
    def restore_replay(self, *, context) -> None:
        # Stateful gates must override this and bind their reset checkpoint in identity.
        if (self.config.get("stateful", False) or self.identity().get("stateful", False)): raise UnsupportedError("STATEFUL_GATE_REPLAY_RESTORE_REQUIRED")
    @abstractmethod
    def review(self, *, rcc_decision: RCCDecision, context) -> VeritasDecision: ...
    def close(self): pass
