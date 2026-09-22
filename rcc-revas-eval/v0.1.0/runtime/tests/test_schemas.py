import unittest
from .common import *
from rcc_revas_eval.handoff import make_handoff
try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator=None

@unittest.skipIf(Draft202012Validator is None, 'optional development-only jsonschema is not installed; core tests still run')
class IndependentSchemaValidation(unittest.TestCase):
    def test_all_schema_documents_well_formed(self):
        for p in (ROOT/'schemas').glob('*.json'):
            Draft202012Validator.check_schema(read_json(p))
    def test_all_inputs(self):
        validator=Draft202012Validator(read_json(ROOT/'schemas/runtime_input.schema.json'))
        for r in read_jsonl(ROOT/'fixtures/smoke_inputs.jsonl'):validator.validate(r)
    def test_all_outputs_and_handoffs(self):
        vr=Draft202012Validator(read_json(ROOT/'schemas/rcc_result.schema.json'))
        vh=Draft202012Validator(read_json(ROOT/'schemas/veritas_handoff.schema.json'))
        for r in read_jsonl(ROOT/'fixtures/smoke_inputs.jsonl'):
            result=evaluate(r);vr.validate(result);vh.validate(make_handoff(result)[0])
