"""Validated wire objects. Nested JSON is copied at every trust boundary."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal
from .canonical import validate_json
from .guardrails import require

JSON = Any
CandidateKind = Literal["tool_call", "final_answer", "structured_action", "message", "custom", "batch", "model_request", "artifact"]
KINDS = {"tool_call", "final_answer", "structured_action", "message", "custom", "batch", "model_request", "artifact"}
RCCDisposition = Literal["ADOPT", "HOLD", "REJECT", "UNSUPPORTED", "ERROR"]
VeritasDisposition = Literal["ALLOW", "HOLD", "DENY", "UNSUPPORTED", "ERROR"]

@dataclass(frozen=True)
class CandidateAction:
    kind: CandidateKind
    name: str | None = None
    arguments: JSON = None
    content: JSON = None
    metadata: dict[str, JSON] = field(default_factory=dict)
    def __post_init__(self):
        require(self.kind in KINDS, "CANDIDATE_KIND_INVALID")
        require(self.name is None or (type(self.name) is str and bool(self.name)), "CANDIDATE_NAME_INVALID")
        require(type(self.metadata) is dict, "CANDIDATE_METADATA_INVALID")
        validate_json(self.to_dict())
    def to_dict(self):
        return deepcopy({"kind": self.kind, "name": self.name, "arguments": self.arguments,
                         "content": self.content, "metadata": self.metadata})

@dataclass(frozen=True)
class Observation:
    kind: str
    data: JSON
    terminal: bool = False
    def __post_init__(self):
        require(type(self.kind) is str and bool(self.kind), "OBSERVATION_KIND_INVALID")
        require(type(self.terminal) is bool, "OBSERVATION_TERMINAL_INVALID")
        validate_json(self.data)
    def to_dict(self): return deepcopy({"kind": self.kind, "data": self.data, "terminal": self.terminal})

@dataclass(frozen=True)
class RCCDecision:
    disposition: RCCDisposition
    adopted_candidate: CandidateAction | None
    handoff: dict[str, JSON] | None = None
    evidence: dict[str, JSON] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    def __post_init__(self):
        require(self.disposition in {"ADOPT", "HOLD", "REJECT", "UNSUPPORTED", "ERROR"}, "RCC_DISPOSITION_INVALID")
        require((self.disposition == "ADOPT") == isinstance(self.adopted_candidate, CandidateAction), "RCC_ADOPT_CANDIDATE_INCONSISTENT")
        require(self.handoff is None or type(self.handoff) is dict, "HANDOFF_INVALID")
        require(type(self.evidence) is dict, "RCC_EVIDENCE_INVALID")
        require(type(self.reason_codes) in (tuple,list) and all(type(x) is str for x in self.reason_codes), "RCC_REASON_CODES_INVALID")
        validate_json(self.to_dict())
    def to_dict(self):
        return deepcopy({"disposition": self.disposition,
                         "adopted_candidate": self.adopted_candidate.to_dict() if self.adopted_candidate else None,
                         "handoff": self.handoff, "evidence": self.evidence,
                         "reason_codes": list(self.reason_codes)})

@dataclass(frozen=True)
class VeritasDecision:
    disposition: VeritasDisposition
    evidence: dict[str, JSON] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    def __post_init__(self):
        require(self.disposition in {"ALLOW", "HOLD", "DENY", "UNSUPPORTED", "ERROR"}, "VERITAS_DISPOSITION_INVALID")
        require(type(self.evidence) is dict, "VERITAS_EVIDENCE_INVALID")
        require(type(self.reason_codes) in (tuple,list) and all(type(x) is str for x in self.reason_codes), "VERITAS_REASON_CODES_INVALID")
        validate_json(self.to_dict())
    def to_dict(self):
        return deepcopy({"disposition": self.disposition, "evidence": self.evidence,
                         "reason_codes": list(self.reason_codes)})
