from pathlib import Path
from copy import deepcopy
import json
ROOT = Path(__file__).resolve().parent.parent
from rcc_revas_eval.integrity import read_json, read_jsonl
from rcc_revas_eval.release import preflight
from rcc_revas_eval.runtime import evaluate_one
from scripts.build_development_fixtures import make, resign, sync_content, add_evidence
POLICY = read_json(ROOT / 'policies/evaluation_policy.json')
KEYRING = read_json(ROOT / 'policies/SYNTHETIC_ONLY_keyring.json')

def identity():
    return preflight(ROOT / 'evaluation_manifest.json')['source_identity']

def evaluate(row):
    return evaluate_one(row, POLICY, KEYRING, identity())
