#!/usr/bin/env python3
"""Persistent evidence for a real socket test against a TEST PEER, not VERITAS."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch
import os
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from tests.test_canonical_regressions import HTTPTestPeer,NativeTransportRegressions
from scripts.build_development_fixtures import make
from rcc_revas_eval.integrity import jsonl_bytes,write_json,raw_sha,read_jsonl
from rcc_revas_eval.bundle import create_run
from rcc_revas_eval.native_veritas import invoke_run,verify_native_run


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
    out=p.parse_args().output_dir.absolute()
    if out.exists():p.error('Output exists')
    out.mkdir(parents=True)
    input_path=out/'runtime_inputs.jsonl'
    input_path.write_bytes(jsonl_bytes([make('transport-success','protected_action'),make('transport-503','protected_action')]))
    manifest=ROOT/'evaluation_manifest.json'
    create_run(manifest,input_path,out/'upstream')
    def reply(i,payload):
        return NativeTransportRegressions.good(i,payload) if i==1 else (503,b'{"error":"controlled test failure"}',{})
    with HTTPTestPeer(reply) as peer,patch.dict(os.environ,{'RCC_TRANSPORT_TEST_KEY':'public-loopback-fixture-key-only'}):
        summary=invoke_run(manifest,out/'upstream',out/'transport',base_url=peer.url,api_key_env='RCC_TRANSPORT_TEST_KEY')
    verification=verify_native_run(manifest,out/'upstream',out/'transport')
    records=read_jsonl(out/'transport/veritas_native_receipts.jsonl')
    assert [r['status'] for r in records]==['RESPONSE_RECORDED','ERROR']
    assert summary['errors']==1 and summary['http_success_count']==1
    write_json(out/'TEST_PEER_EVIDENCE.json',{
        'status':'PASS_EXPECTED_FAILURE_RECORDED','server_kind':'LOCAL_HTTP_TEST_PEER_NOT_VERITAS',
        'real_loopback_requests':len(peer.requests),'request_path':'POST /v1/decide',
        'native_VERITAS_code_executed':False,'tests':'200 finite fractional JSON followed by 503; prior success and both attempts persisted',
        'summary':summary,'verification':verification,'sha256_source_manifest':raw_sha((ROOT/'source_manifest.json').read_bytes())})
    print(json.dumps({'status':'PASS','requests':2,'expected_http_failures':1,'native_VERITAS_code_executed':False}))
    return 0
if __name__=='__main__':raise SystemExit(main())
