import unittest
import tempfile
import shutil
import json
import subprocess
import sys
from pathlib import Path
from .common import *
from rcc_revas_eval.integrity import ContractError, canonical, jsonl_bytes, raw_sha, write_json
from rcc_revas_eval.bundle import create_run,verify_run
from rcc_revas_eval.scoring import score_run
from rcc_revas_eval.preregistration import freeze_plan

class BundleIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.run=self.root/'run'
        self.manifest=ROOT/'evaluation_manifest.json'
        self.inputs=self.root/'inputs.jsonl';self.inputs.write_bytes(jsonl_bytes([make('bundle-test','protected_action')]))
        self.labels=self.root/'registered-labels.jsonl'
        self.labels.write_bytes(jsonl_bytes([{'case_id':'bundle-test','expected_decision':'ADOPT','expected_release':True,'label_provenance':'unit-test-only'}]))
        self.plan=self.root/'plan.json'
        freeze_plan(self.manifest,self.inputs,self.labels,self.plan)
        self.receipt=create_run(self.manifest,self.inputs,self.run,plan_path=self.plan)
    def test_real_run_verifies_and_reexecutes(self):
        result=verify_run(self.manifest,self.run,expected_seal=self.receipt['bundle_seal_sha256'])
        self.assertEqual(result['executed'],1);self.assertTrue(result['external_seal_pin_checked'])
    def test_wrong_external_seal_rejected(self):
        with self.assertRaisesRegex(ContractError,'EXTERNAL_SEAL_PIN_MISMATCH'):verify_run(self.manifest,self.run,expected_seal='0'*64)
    def test_modified_artifact_detected(self):
        with (self.run/'rcc_results.jsonl').open('ab') as f:f.write(b' ')
        with self.assertRaisesRegex(ContractError,'BUNDLE_FILE_HASH_MISMATCH'):verify_run(self.manifest,self.run)
    def test_deleted_artifact_detected(self):
        (self.run/'handoff_results.jsonl').unlink()
        with self.assertRaisesRegex(ContractError,'BUNDLE_CLOSURE_MISMATCH'):verify_run(self.manifest,self.run)
    def test_extra_artifact_detected(self):
        (self.run/'extra.json').write_text('{}')
        with self.assertRaisesRegex(ContractError,'BUNDLE_CLOSURE_MISMATCH'):verify_run(self.manifest,self.run)
    def test_existing_run_never_overwritten(self):
        with self.assertRaisesRegex(ContractError,'RUN_DIRECTORY_EXISTS'):create_run(self.manifest,self.inputs,self.run)
    def test_symlink_artifact_rejected(self):
        p=self.run/'report.md';backup=self.root/'external.md';backup.write_bytes(p.read_bytes());p.unlink();p.symlink_to(backup)
        with self.assertRaisesRegex(ContractError,'SYMLINK_FORBIDDEN'):verify_run(self.manifest,self.run)
    def test_invalid_row_remains_error_not_rejection(self):
        r=make('broken');r['expected_decision']='ADOPT'
        p=self.root/'broken.jsonl';p.write_bytes(jsonl_bytes([r]));out=self.root/'broken'
        result=create_run(self.manifest,p,out)
        self.assertEqual(result['errors'],1);self.assertEqual(result['decisions'],{})
        errors=read_jsonl(out/'errors.jsonl');self.assertIsNone(errors[0]['governance_decision'])
        self.assertEqual(verify_run(self.manifest,out)['errors'],1)
    def test_duplicate_ids_rejected_before_output(self):
        r=make('dup');p=self.root/'dup.jsonl';p.write_bytes(jsonl_bytes([r,r]))
        out=self.root/'dup'
        with self.assertRaisesRegex(ContractError,'DUPLICATE_CASE_ID'):create_run(self.manifest,p,out)
        self.assertFalse(out.exists())
    def test_operational_zero_is_local_scope(self):
        op=read_json(self.run/'operational_metrics.json')
        self.assertEqual(op['model_calls'],0)
        self.assertEqual(op['original_candidate_generation_tokens'],'NOT_MEASURED')
        self.assertEqual(op['VERITAS_latency_delta'],'NOT_MEASURED')
    def test_scoring_does_not_mutate_run(self):
        before={p.relative_to(self.run).as_posix():raw_sha(p.read_bytes()) for p in self.run.rglob('*') if p.is_file()}
        labels=[{'case_id':'bundle-test','expected_decision':'ADOPT','expected_release':True,'label_provenance':'unit-test-only'}]
        path=self.root/'labels.jsonl';path.write_bytes(jsonl_bytes(labels))
        report=score_run(self.manifest,self.run,path,self.root/'score',raw_sha(path.read_bytes()))
        after={p.relative_to(self.run).as_posix():raw_sha(p.read_bytes()) for p in self.run.rglob('*') if p.is_file()}
        self.assertEqual(before,after);self.assertEqual(report['false_stop_on_expected_adopt']['numerator'],0)
    def test_label_only_mutation_leaves_runtime_byte_identical(self):
        labels=[{'case_id':'bundle-test','expected_decision':'REJECT','expected_release':False,'label_provenance':'deliberate-negative-control'}]
        path=self.root/'wrong-label.jsonl';path.write_bytes(jsonl_bytes(labels))
        with self.assertRaisesRegex(ContractError,'POST_RUN_LABEL_CHANGE_FORBIDDEN'):
            score_run(self.manifest,self.run,path,self.root/'wrong-score',raw_sha(path.read_bytes()))
        second=self.root/'second';create_run(self.manifest,self.inputs,second)
        for file in ('rcc_results.jsonl','handoff_results.jsonl'):
            self.assertEqual((self.run/file).read_bytes(),(second/file).read_bytes())
    def test_wrong_label_pin_rejected(self):
        p=self.root/'labels.jsonl';p.write_bytes(b'{}\n')
        with self.assertRaisesRegex(ContractError,'SCORING_LABEL_PIN_MISMATCH'):score_run(self.manifest,self.run,p,self.root/'score','0'*64)
    def test_no_denominator_is_not_zero_rate(self):
        p=self.root/'labels.jsonl';p.write_bytes(jsonl_bytes([{'case_id':'bundle-test','expected_decision':'ADOPT','expected_release':True,'label_provenance':'unit-test-only'}]))
        report=score_run(self.manifest,self.run,p,self.root/'score',raw_sha(p.read_bytes()))
        self.assertIsNone(report['false_adopt_on_expected_stop']['value'])
        self.assertEqual(report['false_adopt_on_expected_stop']['status'],'NO_DENOMINATOR')
    def test_real_cli_preflight(self):
        p=subprocess.run([sys.executable,'-m','rcc_revas_eval','preflight','--manifest',str(self.manifest)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['status'],'PASS')
    def test_real_cli_invalid_input_returns_nonzero_json_error(self):
        p=subprocess.run([sys.executable,'-m','rcc_revas_eval','evaluate','--manifest',str(self.manifest),'--input',str(self.root/'missing'),'--output-dir',str(self.root/'bad')],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stderr)['status'],'ERROR')
    def _reseal_for_negative_control(self):
        # Simulate an internally consistent but semantically false untrusted bundle.
        h=read_json(self.run/'hashes.json')
        for e in h['files']:
            data=(self.run/e['path']).read_bytes();e['sha256']=raw_sha(data);e['size_bytes']=len(data)
        (self.run/'hashes.json').write_bytes(json.dumps(h,indent=2,sort_keys=True).encode()+b'\n')
        seal=read_json(self.run/'bundle_seal.json');seal['hashes_sha256']=raw_sha((self.run/'hashes.json').read_bytes())
        (self.run/'bundle_seal.json').write_bytes(json.dumps(seal,indent=2,sort_keys=True).encode()+b'\n')
    def test_resealed_false_metrics_still_rejected(self):
        path=self.run/'governance_metrics.json';m=read_json(path);m['decisions']={'ADOPT':999}
        path.write_bytes(json.dumps(m,indent=2,sort_keys=True).encode()+b'\n');self._reseal_for_negative_control()
        with self.assertRaisesRegex(ContractError,'DERIVED_METRICS_MISMATCH'):verify_run(self.manifest,self.run)
    def test_resealed_fake_native_execution_still_rejected(self):
        path=self.run/'veritas_results.json';m=read_json(path);m['status']='EXECUTED'
        path.write_bytes(json.dumps(m,indent=2,sort_keys=True).encode()+b'\n');self._reseal_for_negative_control()
        with self.assertRaisesRegex(ContractError,'FABRICATED_NATIVE_RESULT'):verify_run(self.manifest,self.run)
