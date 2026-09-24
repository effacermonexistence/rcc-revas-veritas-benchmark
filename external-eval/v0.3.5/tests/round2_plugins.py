"""Second-review counterexamples; fixture behavior is deliberately adversarial."""
from tests.support_plugins import Adapter, Session, AgentImpl
from rveval.canonical import sha_json
from rveval.models import Observation

class MultiCaseAdapter(Adapter):
    def case_ids(self): return ['one', 'two']

class TaskDriftSession(Session):
    def task_payload(self): return {'query': 'task A' if self.arm == 'A' else 'task B'}
class TaskDriftAdapter(Adapter):
    def open_session(self, cid, *, seed, arm): return TaskDriftSession('ok', arm)

class StringTerminalSession(Session):
    def is_terminal(self): return 'false'
class StringTerminalAdapter(Adapter):
    def open_session(self, cid, *, seed, arm): return StringTerminalSession('ok', arm)

class BrokenAggregatingAdapter(Adapter):
    def open_session(self, cid, *, seed, arm): return Session('apply_error', arm)
    def aggregate_native_scores(self, cases):
        scores=[r[a]['native_score']['native_metric'] for r in cases for a in ('arm_a','arm_b') if r.get(a) and r[a].get('native_score')]
        return {'metric': 'unsafe-mean', 'value':sum(scores)/len(scores) if scores else None}

class CrossScorerSession(Session):
    def native_score(self):
        if self.arm == 'A': self.other.value=999
        return {'native_metric': self.value}
class CrossScorerAdapter(Adapter):
    def open_session(self, cid, *, seed, arm):
        s=CrossScorerSession('ok',arm)
        if arm=='A': self.first=s
        else: self.first.other=s
        return s

class PoisonCloseSession(Session):
    def close(self): raise RuntimeError('deliberate close failure')
class PoisonCloseAdapter(Adapter):
    def open_session(self,cid,*,seed,arm): return PoisonCloseSession('ok',arm)

class TerminalDisagreementSession(Session):
    def apply(self,c):
        self.value+=1
        return Observation('result', {'v':self.value}, terminal=True)
class TerminalDisagreementAdapter(Adapter):
    def open_session(self,cid,*,seed,arm):return TerminalDisagreementSession('ok',arm)

class MixedAdapter(BrokenAggregatingAdapter):
    def case_ids(self): return ['bad','good']
    def open_session(self,cid,*,seed,arm):return Session('apply_error' if cid=='bad' else 'ok',arm)

class DriftingReadSession(Session):
    def agent_state(self):
        self.value += 1
        return {'value':self.value}
class DriftingReadAdapter(Adapter):
    def open_session(self,cid,*,seed,arm):return DriftingReadSession('ok',arm)

class NativeScorerFixture:
    def __init__(self,config,base_dir): self.config=config
    def identity(self):return {'test_only':True, 'version':'constant'}
    def score(self,**kwargs):return {'score':1}
    def compare(self,a,b):return {'delta':0}
    def aggregate(self,cases):return {'count':len(cases)}
