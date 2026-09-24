"""Adversarial fixtures, not production RCC/VERITAS or benchmark adapters."""
from copy import deepcopy
from rveval.interfaces import BenchmarkAdapter,BenchmarkSession,Agent,RCCGate,VeritasGate
from rveval.models import CandidateAction,Observation,RCCDecision,VeritasDecision
from rveval.canonical import sha_json
from rveval.governance.passthrough import PassThroughRCC,AllowAllVeritas

SCORE_CALLED=False
APPLY_COUNT=0
class Session(BenchmarkSession):
    def __init__(self, mode, arm):
        self.mode,self.arm=mode,arm; self.value=0; self.done=False
        self.internal={"v":0,"private_secret":"not for the gate","gold":"do not leak"}
    def task_payload(self): return {"query":"Compute one plus one"}
    def agent_state(self): return {"v":self.value}
    def pairing_state(self):
        if self.mode=="initial_mismatch": return {"v":1 if self.arm=="B" else 0}
        if self.mode=="mutable_snapshot": return self.internal
        return {"v":self.value,"private_secret":"do not expose", "gold":"scoring only"}
    def tool_schema(self): return [{"name":"first" if self.value==0 else "second"}]
    def apply(self,c):
        global APPLY_COUNT
        APPLY_COUNT+=1
        if self.mode=="apply_error": self.value+=1; raise RuntimeError("API_KEY=never_report_me")
        if self.mode=="mutate_candidate":c.arguments["n"]=99
        self.value+=1;self.internal["v"]=self.value
        self.done=(self.value==2 if self.mode=="two_steps" else True)
        if self.mode=="observation_leak":return Observation("result",{"gold_label":"leaked"},self.done)
        return Observation("result",{"v":self.value},self.done)
    def is_terminal(self):return self.done
    def native_score(self):
        global SCORE_CALLED
        SCORE_CALLED=True
        if self.mode=="score_error":raise RuntimeError("key=secret")
        return {"native_metric":self.value,"done":self.done}
class Adapter(BenchmarkAdapter):
    def identity(self):return {"test_only":True,"mode":self.config.get("mode","ok")}
    def case_ids(self):return ["fixture-A-expected-allow"]
    def case_fingerprint(self,cid):return sha_json({"cid":cid,"config":self.config})
    def open_session(self,cid,*,seed,arm):
        mode=self.config.get("mode","ok")
        if mode=="open_error":raise RuntimeError("secret")
        if mode=="same_session":
            if not hasattr(self,"shared"):self.shared=Session(mode,arm)
            return self.shared
        return Session(mode,arm)
    def compare_native_scores(self,a,b):return {"delta":b["native_metric"]-a["native_metric"]}
class AgentImpl(Agent):
    def identity(self):return {"test_only":True,"config":self.config}
    def reset(self,*,case_id,arm,seed):
        assert "expected" not in case_id
        assert arm=="paired"
        self.calls=0
    def act(self,*,task,history,state,tools):
        mode=self.config.get("mode","ok");self.calls+=1
        if mode=="assert_no_score":assert not SCORE_CALLED
        if mode=="mutation":task["query"]="changed"
        if mode=="no_leak":assert "gold" not in state
        if mode=="dynamic_tools":assert tools[0]["name"]==("first" if self.calls==1 else "second")
        return CandidateAction("tool_call",name="work",arguments={"n":self.calls})
class Gate(RCCGate):
    def identity(self):return {"test_only":True,"config":self.config}
    def review(self,*,candidate,context):
        mode=self.config.get("mode","ok")
        assert "pre_state" not in context and "arm" not in context
        assert "private_secret" not in str(context)
        if mode=="mutation":candidate.arguments["n"]=999
        if mode=="context_mutation":context["task"]["query"]="different"
        if mode in ("ERROR","UNSUPPORTED","HOLD","REJECT"):return RCCDecision(mode,None)
        if mode=="leak":return RCCDecision("ADOPT",candidate,evidence={"gold":"oops"})
        if mode=="replacement":candidate=CandidateAction("tool_call",name="different",arguments={"n":9})
        return RCCDecision("ADOPT",candidate,handoff={"native_namespace":"rcc-test"},evidence={})
class VGate(VeritasGate):
    def identity(self):return {"test_only":True,"config":self.config,"stateful":self.config.get("stateful",False)}
    def review(self,*,rcc_decision,context):
        mode=self.config.get("mode","ALLOW")
        assert "pre_state" not in context and "arm" not in context
        if mode=="mutation":rcc_decision.adopted_candidate.arguments["n"]=999;mode="ALLOW"
        if mode=="assert_no_score":assert not SCORE_CALLED;mode="ALLOW"
        return VeritasDecision(mode,evidence={"candidate_sha":context["candidate_sha256"]})
