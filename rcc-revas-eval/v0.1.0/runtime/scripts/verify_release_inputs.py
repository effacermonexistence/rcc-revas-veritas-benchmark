#!/usr/bin/env python3
"""Check the exact bundled external fixture and reference bytes (no network)."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parent.parent

def main():
    p=ROOT/'fixtures/takeshi/Governance_labelled_Evaluation_Set_v0.1.1.jsonl'
    raw=p.read_bytes();m=json.loads((p.parent/'SOURCE_PROVENANCE.json').read_text())
    assert hashlib.sha256(raw).hexdigest()==m['sha256'], 'SOURCE_FIXTURE_SHA256_MISMATCH'
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='426eda32bda6ba767a42f4c2e0f979483f76f46a','SOURCE_GIT_BLOB_MISMATCH'
    refs=json.loads((ROOT/'reference/REFERENCE_MANIFEST.json').read_text())
    contract=ROOT/refs['contract']['path']
    assert hashlib.sha256(contract.read_bytes()).hexdigest()==refs['contract']['sha256'], 'REFERENCE_CONTRACT_BYTES_CHANGED'
    print(json.dumps({'status':'PASS','partner_cases':len(raw.splitlines()),'raw_git_blob_verified':True,'unchanged_contract_bytes_verified':True}))
    return 0
if __name__=='__main__':raise SystemExit(main())
