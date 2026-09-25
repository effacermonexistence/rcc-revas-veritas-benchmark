"""Static/batch/artifact output adapter using a separately installed native scorer.

No benchmark is declared installed just because it fits this interface.
"""
from __future__ import annotations
from copy import deepcopy
from .static_jsonl import StaticJSONLAdapter,StaticSession,StaticDeferredScore
from ..plugin import instantiate,plugin_identity
from ..guardrails import require
from ..external_identity import declared_source_identity, repository_identities

class NativeDeferredScore(StaticDeferredScore):
    def __init__(self, session):
        super().__init__(session)
        self.case = deepcopy(session.case)
        self.scorer = session.scorer
    def score(self):
        result = self.scorer.score(case=deepcopy(self.case), prediction=deepcopy(self.answer),
                                   label=deepcopy(self.label), label_present=self.label_present,
                                   completed=self.terminal)
        require(type(result) is dict, "NATIVE_SCORER_RESULT_INVALID")
        return result


class NativeScoredSession(StaticSession):
    def __init__(self,*args,scorer,**kwargs):
        super().__init__(*args,**kwargs);self.scorer=scorer
    def defer_score(self): return NativeDeferredScore(self)
    def native_score(self):
        result=self.scorer.score(case=deepcopy(self.case),prediction=deepcopy(self.answer),
                                 label=deepcopy(self.label),label_present=self.label_present,
                                 completed=self.terminal)
        require(type(result) is dict,"NATIVE_SCORER_RESULT_INVALID")
        return result

class NativeStaticAdapter(StaticJSONLAdapter):
    def __init__(self,config,base_dir):
        super().__init__(config,base_dir)
        spec=config["scorer"]
        self.scorer=instantiate(spec["plugin"],spec.get("config",{}),base_dir)
    def identity(self):
        spec=self.config["scorer"]
        return {**super().identity(),"scorer":self.scorer.identity(),"scorer_plugin":plugin_identity(spec["plugin"]),
                "scorer_source_files":declared_source_identity(spec.get("config",{}),self.base_dir),
                "scorer_source_repositories":repository_identities(spec.get("config",{}),self.base_dir)}
    def open_session(self,cid,*,seed,arm):
        return NativeScoredSession(self.cases[cid],self.labels.get(cid),label_present=cid in self.labels,scorer=self.scorer)
    def compare_native_scores(self,a,b): return self.scorer.compare(deepcopy(a),deepcopy(b))
    def aggregate_native_scores(self,cases): return self.scorer.aggregate(deepcopy(cases))
    def close(self):
        if hasattr(self.scorer,"close"):self.scorer.close()
