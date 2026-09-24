from __future__ import annotations
from ..canonical import read_json, sha_file
from ..interfaces import Agent
from ..models import CandidateAction
from ..guardrails import UnsupportedError

class ReplayAgent(Agent):
    """Engineering fixture only. Never evidence of live model generation."""
    def __init__(self, config, base_dir):
        super().__init__(config,base_dir)
        self.source_path=(base_dir/config["actions_path"]).resolve()
        self.actions=read_json(self.source_path); self.index=0; self.case_id=None
    def identity(self): return {"agent":"ReplayAgent/v2","test_only":True,"actions_sha256":sha_file(self.source_path)}
    def reset(self, *, case_id, arm, seed): self.index=0; self.case_id=case_id
    def select_fixture(self, original_id): self.case_id=original_id
    def act(self, *, task, history, state, tools):
        if self.case_id not in self.actions: raise UnsupportedError("REPLAY_CASE_MISSING")
        seq=self.actions[self.case_id]
        if self.index>=len(seq): raise UnsupportedError("REPLAY_EXHAUSTED")
        raw=seq[self.index]; self.index+=1
        return CandidateAction(**raw)
