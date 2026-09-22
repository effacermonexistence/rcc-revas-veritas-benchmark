#!/usr/bin/env python3
"""Run source checks, tests, an actual smoke run, replay and separate scoring.

No refreezing, no network, no repository writes and no mail sending.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args()
    output=args.output_dir.absolute()
    if output.exists():
        p.error('Output directory already exists; use a new path.')
    output.mkdir(parents=True)
    # Verify the stored development scoring plan before any execution. This keeps
    # reproduction pinned to the same inputs/labels rather than silently
    # recomputing a new plan from changed files.
    plan=json.loads((ROOT/'fixtures/SCORING_PLAN.json').read_text())
    runtime_bytes=(ROOT/'fixtures/smoke_inputs.jsonl').read_bytes()
    label_bytes=(ROOT/'fixtures/scoring_labels.jsonl').read_bytes()
    runtime_sha=hashlib.sha256(runtime_bytes).hexdigest()
    label_sha=hashlib.sha256(label_bytes).hexdigest()
    case_count=sum(1 for line in runtime_bytes.splitlines() if line.strip())
    if runtime_sha != plan['runtime_input_sha256']:
        raise SystemExit('SCORING_PLAN_RUNTIME_INPUT_HASH_MISMATCH')
    if label_sha != plan['label_sha256']:
        raise SystemExit('SCORING_PLAN_LABEL_HASH_MISMATCH')
    if case_count != plan['case_count']:
        raise SystemExit('SCORING_PLAN_CASE_COUNT_MISMATCH')

    base=[sys.executable,'-m','rcc_revas_eval']
    steps=[('preflight',base+['preflight','--manifest',str(ROOT/'evaluation_manifest.json')]),
           ('unittest',[sys.executable,'-m','unittest','discover','-s','tests','-t','.','-v']),
           ('freeze-plan',base+['freeze-plan','--manifest',str(ROOT/'evaluation_manifest.json'),'--input',str(ROOT/'fixtures/smoke_inputs.jsonl'),'--labels',str(ROOT/'fixtures/scoring_labels.jsonl'),'--output',str(output/'preregistration.json')]),
           ('evaluate',base+['evaluate','--manifest',str(ROOT/'evaluation_manifest.json'),'--input',str(ROOT/'fixtures/smoke_inputs.jsonl'),'--output-dir',str(output/'run'),'--plan',str(output/'preregistration.json')]),
           ('verify',base+['verify-artifacts','--manifest',str(ROOT/'evaluation_manifest.json'),'--run-dir',str(output/'run')])]
    labels=ROOT/'fixtures/scoring_labels.jsonl'
    steps.append(('score',base+['score','--manifest',str(ROOT/'evaluation_manifest.json'),'--run-dir',str(output/'run'),'--labels',str(labels),'--labels-sha256',label_sha,'--output-dir',str(output/'scoring')]))
    records=[]
    for name,command in steps:
        completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        (output/(name+'.stdout.txt')).write_text(completed.stdout)
        (output/(name+'.stderr.txt')).write_text(completed.stderr)
        records.append({'stage':name,'command':command,'exit_code':completed.returncode,
                        'stdout_sha256':hashlib.sha256(completed.stdout.encode()).hexdigest(),
                        'stderr_sha256':hashlib.sha256(completed.stderr.encode()).hexdigest()})
        print(name+': '+('PASS' if completed.returncode==0 else 'FAIL'),flush=True)
        if completed.returncode:
            (output/'reproduction.json').write_text(json.dumps({'status':'FAILED','stages':records},indent=2)+'\n')
            return completed.returncode
    report={'status':'LOCAL_REPRODUCTION_PASSED','stages':records,
            'development_fixture_only':True,'VERITAS_native_execution':False,
            'scoring_plan_verified':True,
            'scoring_plan_runtime_input_sha256':runtime_sha,
            'scoring_plan_label_sha256':label_sha,
            'independent_external_validation':False,'github_publication':False}
    (output/'reproduction.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
