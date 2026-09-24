from __future__ import annotations
from ..interfaces import RCCGate,VeritasGate
from ..models import CandidateAction,RCCDecision,VeritasDecision
class PassThroughRCC(RCCGate):
    def identity(self): return {"engine":"PassThroughRCC","version":"test-only-v1"}
    def review(self,*,candidate:CandidateAction,context): return RCCDecision("ADOPT",candidate,handoff={"test_only":True},evidence={"mode":"passthrough"})
class AllowAllVeritas(VeritasGate):
    def identity(self): return {"engine":"AllowAllVeritas","version":"test-only-v1"}
    def review(self,*,rcc_decision:RCCDecision,context): return VeritasDecision("ALLOW",evidence={"mode":"passthrough"})
class DenyNamedActionVeritas(VeritasGate):
    def identity(self): return {"engine":"DenyNamedActionVeritas","version":"test-only-v1","deny_name":self.config.get("deny_name")}
    def review(self,*,rcc_decision:RCCDecision,context):
        c=rcc_decision.adopted_candidate
        return VeritasDecision("DENY",reason_codes=("TEST_DENY_NAMED_ACTION",)) if c and c.name==self.config.get("deny_name") else VeritasDecision("ALLOW")
