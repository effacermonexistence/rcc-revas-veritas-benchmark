import unittest
import tempfile
import shutil
import json
import subprocess
import sys
from pathlib import Path
from .common import ROOT

class ReleaseClosure(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.copy=Path(self.temp.name)/'checkout'
        shutil.copytree(ROOT,self.copy,ignore=shutil.ignore_patterns('.git','output','review','__pycache__','*.egg-info'))
    def run_preflight(self):
        return subprocess.run([sys.executable,'-m','rcc_revas_eval','preflight','--manifest','evaluation_manifest.json'],cwd=self.copy,capture_output=True,text=True)
    def test_clean_copy_passes(self):
        result=self.run_preflight();self.assertEqual(result.returncode,0,result.stderr)
    def test_source_tamper_not_silently_refrozen(self):
        with (self.copy/'rcc_revas_eval/runtime.py').open('a') as f:f.write('\n# tampered\n')
        result=self.run_preflight();self.assertEqual(result.returncode,2);self.assertIn('SOURCE_HASH_MISMATCH',result.stderr)
    def test_added_runtime_file_rejected(self):
        (self.copy/'rcc_revas_eval/hidden.py').write_text('')
        result=self.run_preflight();self.assertEqual(result.returncode,2);self.assertIn('SOURCE_CLOSURE_MISMATCH',result.stderr)
    def test_policy_edit_rejected(self):
        p=self.copy/'policies/evaluation_policy.json';x=json.loads(p.read_text());x['version']='tampered';p.write_text(json.dumps(x))
        result=self.run_preflight();self.assertEqual(result.returncode,2);self.assertIn('SOURCE_HASH_MISMATCH',result.stderr)
    def test_development_labels_not_in_runtime_identity(self):
        before=json.loads(self.run_preflight().stdout)['source_identity']
        (self.copy/'fixtures/scoring_labels.jsonl').write_text('{"changed":"entirely"}\n')
        after=json.loads(self.run_preflight().stdout)['source_identity']
        self.assertEqual(before,after)
    def test_loaded_code_must_match_reported_source(self):
        with (self.copy/'rcc_revas_eval/runtime.py').open('a') as f:f.write('\n# changed code identity\n')
        subprocess.run([sys.executable,'scripts/freeze_sources.py'],cwd=self.copy,check=True,capture_output=True)
        # Use the original loaded runtime with a different, freshly self-consistent manifest.
        result=subprocess.run([sys.executable,'-m','rcc_revas_eval','preflight','--manifest',str(self.copy/'evaluation_manifest.json')],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn('LOADED_SOURCE_HASH_MISMATCH',result.stderr)
