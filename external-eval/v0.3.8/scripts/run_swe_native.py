#!/usr/bin/env python3
"""Run the official grader on frozen scorer-only records and sealed predictions."""
import argparse,json
from pathlib import Path
from rveval.integrations.swebench import run_native_grading

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset-json',type=Path,required=True,help='Exact official dataset records; scorer-only, never agent input')
    p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-id',required=True)
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--timeout',type=int,default=3600)
    args=p.parse_args()
    result=run_native_grading(dataset_rows=json.loads(args.dataset_json.read_text()),predictions_path=args.predictions,
        output=args.output,run_id=args.run_id,max_workers=args.workers,timeout_seconds=args.timeout)
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
