import pytest
from rveval.guardrails import assert_no_scorer_truth,IntegrityError
def test_gold_is_rejected():
    with pytest.raises(IntegrityError): assert_no_scorer_truth({"x":{"ground_truth":"secret"}})
def test_normal_payload_passes(): assert_no_scorer_truth({"question":"hello","metadata":{"source":"x"}})
