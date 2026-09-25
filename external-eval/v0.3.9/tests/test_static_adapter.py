from pathlib import Path
from rveval.adapters.static_jsonl import StaticJSONLAdapter
def test_labels_quarantined_from_task():
    base=Path(__file__).parents[1]/"examples/static_jsonl"; a=StaticJSONLAdapter({"cases_path":"cases.jsonl","labels_path":"labels.jsonl"},base); s=a.open_session("q1",seed=1,arm="A"); assert "label" not in s.task_payload(); assert a.identity()["labels_quarantined"] is True
