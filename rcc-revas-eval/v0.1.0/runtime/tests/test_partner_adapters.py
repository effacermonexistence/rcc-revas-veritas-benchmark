import json
import tempfile
import unittest
from pathlib import Path

from .common import ROOT, POLICY, KEYRING, identity
from rcc_revas_eval.bundle import create_run
from rcc_revas_eval.integrity import canonical, jsonl_bytes, read_jsonl
from rcc_revas_eval.native_veritas import build_decide_request, verify_response_echo
from rcc_revas_eval.runtime import evaluate_one
from rcc_revas_eval.takeshi import transform_case, transform_file
from scripts.build_development_fixtures import make


class TakeshiAdapterTests(unittest.TestCase):
    def source_case(self, approval_required=False):
        # Start from the actual complete source schema rather than a partial
        # fixture that silently defaulted missing controls to passing.
        from copy import deepcopy
        from rcc_revas_eval.takeshi import _source_rows
        row = deepcopy(_source_rows(ROOT/'fixtures/takeshi/Governance_labelled_Evaluation_Set_v0.1.1.jsonl')[3])
        row['case_id']='GOV-TEST-01'
        g=row['input']['governance_fixture']
        g['approval_required']=approval_required
        g['approval_evidence_present']=approval_required
        g['approval_valid']=True
        row['ground_truth']['expected_reason_codes']=['THIS_MUST_NOT_LEAK']
        return row

    def test_transform_ignores_gold_and_proxy_verdicts(self):
        source = self.source_case(approval_required=False)
        row = transform_case(source, policy=POLICY, keyring=KEYRING)
        blob = canonical(row).decode('utf-8')
        self.assertNotIn('expected_decision', blob)
        self.assertNotIn('THIS_MUST_NOT_LEAK', blob)
        self.assertNotIn('runtime_verifier_passed', blob)
        self.assertNotIn('adoption_decision', blob)
        result = evaluate_one(row, POLICY, KEYRING, identity())
        self.assertEqual(result['decision']['adoption']['decision'], 'ADOPT')

    def test_transform_file_reports_ignored_lanes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'takeshi.jsonl'
            source.write_text(json.dumps(self.source_case()) + '\n', encoding='utf-8')
            output = root / 'runtime.jsonl'
            report = root / 'transform.json'
            result = transform_file(source, output, report, policy=POLICY, keyring=KEYRING)
            self.assertEqual(result['case_count'], 1)
            self.assertFalse(result['ground_truth_copied_to_runtime'])
            self.assertFalse(result['historical_proxy_verdicts_copied_to_runtime'])
            self.assertEqual(len(read_jsonl(output)), 1)


class VeritasNativeAdapterTests(unittest.TestCase):
    def test_prepare_request_binds_exact_released_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inp = root / 'input.jsonl'
            inp.write_bytes(jsonl_bytes([make('native-adapter', 'protected_action')]))
            run = root / 'run'
            create_run(ROOT / 'evaluation_manifest.json', inp, run)
            handoff = read_jsonl(run / 'handoff_results.jsonl')[0]
            payload, proof = build_decide_request(handoff, run)
            self.assertTrue(proof['request_side_exact_candidate_bound'])
            self.assertFalse(proof['server_side_exact_candidate_consumption_verified'])
            self.assertEqual(payload['context']['rcc_revas']['candidate_semantic_hash'],
                             proof['candidate_semantic_hash'])
            self.assertNotIn('ground_truth', canonical(payload).decode('utf-8'))

    def test_server_consumption_requires_explicit_matching_echo(self):
        proof = {
            'candidate_semantic_hash': 'c',
            'candidate_object_hash': 'sha256:o',
            'decision_state_binding_fingerprint': 's',
            'upstream_decision_hash': 'd',
            'correlation_id': 'x',
        }
        self.assertFalse(verify_response_echo({}, proof)['exact_candidate_consumption_verified'])
        response = {'extras': {'rcc_revas_echo': {
            'candidate_semantic_hash': 'c',
            'candidate_object_hash': 'sha256:o',
            'decision_state_binding_fingerprint': 's',
            'upstream_decision_hash': 'd',
            'correlation_id': 'x',
        }}}
        self.assertFalse(verify_response_echo(response, proof)['exact_candidate_consumption_verified'])
        self.assertTrue(verify_response_echo(response, proof)['correlation_fields_match'])
        response['extras']['rcc_revas_echo']['candidate_semantic_hash'] = 'wrong'
        check = verify_response_echo(response, proof)
        self.assertFalse(check['exact_candidate_consumption_verified'])
        self.assertIn('candidate_semantic_hash', check['mismatch_fields'])


if __name__ == '__main__':
    unittest.main()
