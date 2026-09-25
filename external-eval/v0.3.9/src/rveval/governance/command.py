from __future__ import annotations
from ..interfaces import RCCGate, VeritasGate
from ..models import CandidateAction,RCCDecision,VeritasDecision
from ..rpc import JsonProcess
from ..external_identity import declared_source_identity
from ..guardrails import UnsupportedError, require

class _Command:
    def _init(self,config,base_dir):
        self.rpc=JsonProcess(config,base_dir)
        try:
            self.meta=self.rpc.call("describe")
            if isinstance(self, VeritasGate):
                require(type(self.meta.get("stateful")) is bool, "GATE_STATEFULNESS_MUST_BE_DECLARED")
                if "stateful" in config:
                    require(config["stateful"] == self.meta["stateful"], "GATE_STATEFULNESS_CONTRADICTION")
                require(type(self.meta.get("replay_restore_supported", False)) is bool,
                        "GATE_REPLAY_CAPABILITY_INVALID")
        except Exception:
            self.rpc.close(); raise
    def identity(self):
        return {"engine":self.meta,"bridge":type(self).__name__+"/v2","command":self.rpc.command,
                "source_files":declared_source_identity(self.config,self.base_dir)}
    def reset(self,*,case_id,arm,seed): self.rpc.call("reset",case_id=case_id,seed=seed)
    def close(self): self.rpc.close()

class CommandRCCGate(_Command,RCCGate):
    def __init__(self,config,base_dir): super().__init__(config,base_dir);self._init(config,base_dir)
    def review(self,*,candidate,context):
        v=self.rpc.call("review",candidate=candidate.to_dict(),context=context)["decision"]
        adopted=CandidateAction(**v["adopted_candidate"]) if v.get("adopted_candidate") else None
        return RCCDecision(v["disposition"],adopted,v.get("handoff"),v.get("evidence",{}),tuple(v.get("reason_codes",[])))

class CommandVeritasGate(_Command,VeritasGate):
    def __init__(self,config,base_dir): super().__init__(config,base_dir);self._init(config,base_dir)
    def restore_replay(self,*,context):
        if self.meta.get("stateful",False):
            if not self.meta.get("replay_restore_supported",False): raise UnsupportedError("NATIVE_GATE_REPLAY_STATE_UNSUPPORTED")
            self.rpc.call("restore_replay",context=context)
    def review(self,*,rcc_decision,context):
        v=self.rpc.call("review",rcc_decision=rcc_decision.to_dict(),context=context)["decision"]
        return VeritasDecision(v["disposition"],v.get("evidence",{}),tuple(v.get("reason_codes",[])))
