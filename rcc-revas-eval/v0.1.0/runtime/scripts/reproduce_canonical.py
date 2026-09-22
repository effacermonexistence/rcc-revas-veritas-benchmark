#!/usr/bin/env python3
"""Reproduce the canonical upstream release without cloud calls or refreezing.

Writes evidence only to the chosen new output directory. The only HTTP exercised
by the tests/capture step is an explicitly labelled loopback test peer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent.parent

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir.absolute()
    if out.exists():parser.error('Use a new output directory; existing evidence is never overwritten.')
    out.mkdir(parents=True)
    p=json.loads((ROOT/'fixtures/SCORING_PLAN.json').read_text())
    for path,key in (('fixtures/smoke_inputs.jsonl','runtime_input_sha256'),('fixtures/scoring_labels.jsonl','label_sha256')):
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=p[key]:
            raise SystemExit('STORED_DEVELOPMENT_PLAN_MISMATCH:'+path)
    base=[sys.executable,'-m','rcc_revas_eval'];manifest=['--manifest',str(ROOT/'evaluation_manifest.json')]
    steps=[
      ('reference-integrity',[sys.executable,str(ROOT/'scripts/verify_release_inputs.py')]),
      ('preflight',base+['preflight']+manifest),
      ('tests',[sys.executable,'-m','unittest','discover','-s','tests','-t','.','-v']),
      ('smoke-plan',base+['freeze-plan']+manifest+['--input',str(ROOT/'fixtures/smoke_inputs.jsonl'),'--labels',str(ROOT/'fixtures/scoring_labels.jsonl'),'--output',str(out/'smoke-plan.json')]),
      ('smoke-execute',base+['evaluate']+manifest+['--input',str(ROOT/'fixtures/smoke_inputs.jsonl'),'--plan',str(out/'smoke-plan.json'),'--output-dir',str(out/'smoke-run')]),
      ('smoke-replay',base+['verify-artifacts']+manifest+['--run-dir',str(out/'smoke-run')]),
      ('smoke-score',base+['score']+manifest+['--run-dir',str(out/'smoke-run'),'--labels',str(ROOT/'fixtures/scoring_labels.jsonl'),'--labels-sha256',p['label_sha256'],'--output-dir',str(out/'smoke-score')]),
      ('takeshi-register',base+['register-takeshi']+manifest+['--source',str(ROOT/'fixtures/takeshi/Governance_labelled_Evaluation_Set_v0.1.1.jsonl'),'--output-dir',str(out/'takeshi-registration')]),
      ('takeshi-execute',base+['evaluate']+manifest+['--input',str(out/'takeshi-registration/runtime_inputs.jsonl'),'--plan',str(out/'takeshi-registration/preregistration.json'),'--output-dir',str(out/'takeshi-run')]),
      ('takeshi-replay',base+['verify-artifacts']+manifest+['--run-dir',str(out/'takeshi-run')]),
      ('takeshi-prepare',base+['prepare-veritas']+manifest+['--run-dir',str(out/'takeshi-run'),'--output-dir',str(out/'takeshi-prepared')]),
      ('takeshi-report',base+['report-partner']+manifest+['--run-dir',str(out/'takeshi-run'),'--labels',str(out/'takeshi-registration/scoring_labels.jsonl'),'--output-dir',str(out/'takeshi-report')]),
      ('loopback-transport',[sys.executable,str(ROOT/'scripts/capture_transport_review.py'),'--output-dir',str(out/'test-peer-transport')]),
    ]
    evidence=[]
    for name,command in steps:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=180)
        (out/(name+'.stdout.txt')).write_text(result.stdout)
        (out/(name+'.stderr.txt')).write_text(result.stderr)
        evidence.append({'stage':name,'command':command,'exit_code':result.returncode,
                         'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),
                         'stderr_sha256':hashlib.sha256(result.stderr.encode()).hexdigest()})
        print(f'{name}: {"PASS" if result.returncode==0 else "FAIL"}',flush=True)
        if result.returncode:break
    status='PASS' if len(evidence)==len(steps) and not any(x['exit_code'] for x in evidence) else 'FAIL'
    report={'status':status,'stages':evidence,'source_manifest_sha256':hashlib.sha256((ROOT/'source_manifest.json').read_bytes()).hexdigest(),
            'native_VERITAS_server_run':False,'transport_peer':'LOOPBACK_TEST_FIXTURE',
            'joint_contract_frozen':False,'remote_write_performed':False}
    (out/'REPRODUCTION.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if status=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
