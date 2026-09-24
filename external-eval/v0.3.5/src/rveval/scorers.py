from abc import ABC,abstractmethod
from .rpc import JsonProcess
from .external_identity import declared_source_identity

class NativeScorer(ABC):
    def __init__(self,config,base_dir):self.config,self.base_dir=config,base_dir
    @abstractmethod
    def identity(self): ...
    @abstractmethod
    def score(self,*,case,prediction,label,label_present,completed): ...
    @abstractmethod
    def compare(self,a,b): ...
    def aggregate(self,cases):return {"status":"NO_NATIVE_AGGREGATOR","enrolled":len(cases)}
    def close(self):pass

class CommandNativeScorer(NativeScorer):
    def __init__(self,config,base_dir):
        super().__init__(config,base_dir);self.rpc=JsonProcess(config,base_dir);self.meta=self._describe()
    def _describe(self):
        try: return self.rpc.call("describe")
        except Exception:
            self.rpc.close(); raise
    def identity(self):return {"scorer":self.meta,"command":self.rpc.command,"source_files":declared_source_identity(self.config,self.base_dir)}
    def score(self,**payload):return self.rpc.call("score_prediction",**payload)["native_score"]
    def compare(self,a,b):return self.rpc.call("compare",arm_a=a,arm_b=b)["comparison"]
    def aggregate(self,cases):return self.rpc.call("aggregate",cases=cases)["aggregate"]
    def close(self):self.rpc.close()
