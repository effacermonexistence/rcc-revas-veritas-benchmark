from __future__ import annotations
from ..canonical import sha_json
from ..interfaces import BenchmarkAdapter, BenchmarkSession
from ..models import CandidateAction, Observation

class MockStatefulSession(BenchmarkSession):
    def __init__(self, target: int):
        self.target=target; self.value=0; self.steps=0; self.done=False
    def task_payload(self): return {"goal":"reach_target","target":self.target}
    def agent_state(self): return {"value":self.value,"target":self.target}
    def pairing_state(self): return {"value":self.value,"target":self.target,"steps":self.steps}
    def tool_schema(self): return [{"kind":"tool_call","name":"add","arguments":{"n":"int"}}]
    def apply(self,candidate:CandidateAction):
        if candidate.kind=="final_answer": self.done=True; return Observation("final",{"value":self.value},True)
        if candidate.kind!="tool_call" or candidate.name!="add": raise ValueError("unsupported mock action")
        self.value += int((candidate.arguments or {}).get("n",0)); self.steps+=1; self.done=self.value==self.target or self.steps>=5
        return Observation("tool_result",{"value":self.value},self.done)
    def is_terminal(self): return self.done
    def native_score(self): return {"metric":"target_reached","value":1 if self.value==self.target else 0,"final_value":self.value}

class MockStatefulAdapter(BenchmarkAdapter):
    def identity(self): return {"benchmark":"mock-stateful","adapter":"MockStatefulAdapter/v1","test_only":True}
    def case_ids(self): return ["case-1"]
    def case_fingerprint(self,case_id:str): return sha_json({"case_id":case_id,"target":2})
    def open_session(self,case_id:str,*,seed:int,arm:str): return MockStatefulSession(2)
    def compare_native_scores(self,a,b): return {"metric":"target_reached_delta","delta":b["value"]-a["value"]}
