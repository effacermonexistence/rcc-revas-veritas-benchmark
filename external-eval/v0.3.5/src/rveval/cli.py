import argparse,json,re
from .guardrails import IntegrityError,UnsupportedError
from pathlib import Path
from .canonical import sha_file,write_json_new
from .freeze import freeze,collect_state
from .runner import execute
from .evidence import verify_evidence
from .readiness import assess_profile

def parser():
    p=argparse.ArgumentParser(prog="rveval");sub=p.add_subparsers(dest="command",required=True)
    f=sub.add_parser("freeze");f.add_argument("--config",type=Path,required=True);f.add_argument("--output",type=Path,required=True)
    r=sub.add_parser("run");r.add_argument("--config",type=Path,required=True);r.add_argument("--freeze",type=Path,required=True);r.add_argument("--ack-freeze-sha256",required=True);r.add_argument("--output-dir",type=Path,required=True)
    h=sub.add_parser("hash");h.add_argument("path",type=Path)
    v=sub.add_parser("verify");v.add_argument("--run-dir",type=Path,required=True);v.add_argument("--expected-index-sha256",required=True)
    c=sub.add_parser("check");c.add_argument("--config",type=Path,required=True)
    n=sub.add_parser("readiness");n.add_argument("--profile",type=Path,required=True);n.add_argument("--config",type=Path)
    q=sub.add_parser("mapping-check");q.add_argument("--contract",type=Path,required=True)
    m=sub.add_parser("matrix");m.add_argument("--catalogue",type=Path,required=True);m.add_argument("--output-dir",type=Path,required=True)
    i=sub.add_parser("init-pilot");i.add_argument("--output-dir",type=Path,required=True);i.add_argument("--name",required=True)
    return p

def main(argv=None):
    a=parser().parse_args(argv)
    try:
        if a.command=="init-pilot":
            from .pilot import initialize_pilot
            value=initialize_pilot(a.output_dir, a.name)
        elif a.command=="mapping-check":
            from .partner_mapping import validate_mapping_contract
            value=validate_mapping_contract(a.contract)
        elif a.command=="matrix":
            from .matrix import run_matrix
            value=run_matrix(a.catalogue,a.output_dir)
        elif a.command=="freeze":
            freeze(a.config,a.output);value={"freeze":str(a.output),"sha256":sha_file(a.output)}
        elif a.command=="hash":print(sha_file(a.path));return 0
        elif a.command=="verify":value=verify_evidence(a.run_dir,a.expected_index_sha256)
        elif a.command=="readiness":value=assess_profile(a.profile,a.config)
        elif a.command=="check":
            state=collect_state(a.config);value={"status":"CONFIG_AND_IDENTITY_CHECK_PASS","state":state,
                                               "actual_benchmark_run":False,"capability_validation":"DECLARED_PLUS_TYPE_CHECKS_NOT_END_TO_END"}
        else:
            from .native_job import is_native_job, execute_native_job
            from .canonical import read_json
            runner=execute_native_job if is_native_job(read_json(a.config)) else execute
            value=runner(a.config,a.freeze,a.ack_freeze_sha256,a.output_dir)
        print(json.dumps(value,indent=2,ensure_ascii=False))
        return 2 if value.get("status") in {"COMPLETED_WITH_ERRORS_OR_UNSUPPORTED", "NOT_READY", "FAILED", "FAIL"} else 0
    except Exception as exc:
        code=str(exc).split(':',1)[0]
        if not isinstance(exc,(IntegrityError,UnsupportedError)) or not re.fullmatch(r"[A-Z0-9_]{1,100}",code):code=type(exc).__name__
        print(json.dumps({"status":"FAILED","type":type(exc).__name__,"code":code}))
        return 2
