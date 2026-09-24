from __future__ import annotations
from ..interfaces import Agent
from ..models import CandidateAction
from ..rpc import JsonProcess
from ..external_identity import declared_source_identity

class CommandAgent(Agent):
    def __init__(self,config,base_dir):
        super().__init__(config,base_dir);self.rpc=JsonProcess(config,base_dir);self.meta=self._describe()
    def _describe(self):
        try: return self.rpc.call("describe")
        except Exception:
            self.rpc.close(); raise
    def identity(self):
        return {"agent":self.meta,"bridge":"CommandAgent/v2","command":self.rpc.command,
                "source_files":declared_source_identity(self.config,self.base_dir)}
    def reset(self,*,case_id,arm,seed):
        # No experimental arm label delivered to the candidate generator.
        self.rpc.call("reset",case_id=case_id,seed=seed)
    def act(self,*,task,history,state,tools):
        v=self.rpc.call("act",task=task,history=history,state=state,tools=tools)
        return CandidateAction(**v["candidate"])
    def close(self): self.rpc.close()
