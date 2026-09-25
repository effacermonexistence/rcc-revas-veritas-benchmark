from __future__ import annotations
from copy import deepcopy
from ..canonical import loads, sha_file, sha_json
from ..guardrails import require, assert_no_scorer_truth
from ..interfaces import BenchmarkAdapter, BenchmarkSession, DeferredScore
from ..models import Observation

def _jsonl(path):
    return [loads(line) for line in path.read_bytes().splitlines() if line.strip()]

class StaticDeferredScore(DeferredScore):
    def __init__(self, session):
        self.state = deepcopy(session.pairing_state())
        self.answer = deepcopy(session.answer)
        self.label = deepcopy(session.label)
        self.label_present, self.terminal = session.label_present, session.terminal
    def fingerprint(self): return sha_json(self.state)
    def score(self):
        if not self.label_present: return {"status": "UNSCORED", "answer": deepcopy(self.answer)}
        correct = self.terminal and sha_json(self.answer) == sha_json(self.label)
        return {"status": "SCORED", "metric": "exact_json_match", "value": int(correct), "correct": correct,
                "scorer": "rveval_reference_exact_json_not_a_third_party_native_scorer"}


class StaticSession(BenchmarkSession):
    def __init__(self, case, label, *, label_present=False):
        self.case=deepcopy(case);self.label=deepcopy(label);self.label_present=label_present
        self.answer=None;self.terminal=False
    def task_payload(self):
        assert_no_scorer_truth(self.case["input"],"static_task")
        return deepcopy(self.case["input"])
    def agent_state(self): return {"answered":self.terminal}
    def pairing_state(self): return {"case_input_sha256":sha_json(self.case["input"]),"answered":self.terminal,"answer":deepcopy(self.answer)}
    def tool_schema(self): return [{"kind":"final_answer","name":"submit_answer"}]
    def apply(self,candidate):
        require(not self.terminal,"STATIC_ALREADY_TERMINAL")
        require(candidate.kind in {"final_answer","message","artifact","custom","model_request","batch"},"STATIC_ACTION_KIND_UNSUPPORTED")
        self.answer=deepcopy(candidate.content);self.terminal=True
        return Observation("answer_accepted",{"answer":self.answer},True)
    def is_terminal(self): return self.terminal
    def defer_score(self): return StaticDeferredScore(self)
    def native_score(self):
        if not self.label_present: return {"status":"UNSCORED","answer":deepcopy(self.answer)}
        correct=self.terminal and sha_json(self.answer)==sha_json(self.label)
        return {"status":"SCORED","metric":"exact_json_match","value":int(correct),"correct":correct,
                "scorer":"rveval_reference_exact_json_not_a_third_party_native_scorer"}

class StaticJSONLAdapter(BenchmarkAdapter):
    def __init__(self, config, base_dir):
        super().__init__(config,base_dir)
        self.cases_path=(base_dir/config["cases_path"]).resolve()
        self.labels_path=(base_dir/config["labels_path"]).resolve() if config.get("labels_path") else None
        rows=_jsonl(self.cases_path)
        require(bool(rows) and all(type(r) is dict and set(r)=={"case_id","input"} for r in rows),"STATIC_CASE_SHAPE_INVALID")
        self.cases={r["case_id"]:r for r in rows}
        require(len(self.cases)==len(rows),"DUPLICATE_CASE_ID")
        self.labels={}
        if self.labels_path:
            labels=_jsonl(self.labels_path)
            require(all(type(r) is dict and set(r)=={"case_id","label"} for r in labels),"STATIC_LABEL_SHAPE_INVALID")
            self.labels={r["case_id"]:r["label"] for r in labels}
            require(len(labels)==len(self.labels),"DUPLICATE_LABEL_ID")
            require(set(self.labels)==set(self.cases),"STATIC_LABEL_COVERAGE_MISMATCH")
    def identity(self):
        return {"benchmark":self.config.get("name","static-jsonl"),"adapter":"StaticJSONLAdapter/v2",
                "cases_sha256":sha_file(self.cases_path),"labels_sha256":sha_file(self.labels_path) if self.labels_path else None,
                "labels_quarantined":True,"scorer":"reference_exact_json_not_third_party_native"}
    def case_ids(self): return list(self.cases)
    def case_fingerprint(self,cid): return sha_json(self.cases[cid])
    def open_session(self,cid,*,seed,arm): return StaticSession(self.cases[cid],self.labels.get(cid),label_present=cid in self.labels)
    def compare_native_scores(self,a,b):
        av=a.get("value") if a.get("status")=="SCORED" else None
        bv=b.get("value") if b.get("status")=="SCORED" else None
        return {"metric":"exact_json_match_delta","arm_a":av,"arm_b":bv,"delta":bv-av if av is not None and bv is not None else None}
