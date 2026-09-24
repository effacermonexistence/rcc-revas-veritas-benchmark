"""Catalogue-wide preregistration, then isolated native benchmark executions.

All configuration/data/source identities are committed before the first run.
Every benchmark uses its existing scorer. Isolation here is process-level, not
an OS security sandbox or a claim of independent third-party timestamping.
"""
from __future__ import annotations
from pathlib import Path
import os, signal, subprocess, sys
from .canonical import read_json, write_json_new, sha_file
from .freeze import freeze, verify_freeze
from .evidence import verify_evidence
from .guardrails import require


def _run_child(argv, log, *, cwd, timeout):
    # Preserve the caller's installed/source package selection in a fresh process.
    env = dict(os.environ)
    paths = list(dict.fromkeys(str(Path(p).resolve()) for p in sys.path if p))
    env['PYTHONPATH'] = os.pathsep.join(paths)
    with log.open('xb') as stream:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return 124


def run_matrix(catalogue: Path, output: Path):
    catalogue, output = Path(catalogue).resolve(), Path(output).resolve()
    data = read_json(catalogue)
    require(type(data) is dict and type(data.get('configurations')) is list and bool(data['configurations']),
            'BENCHMARK_CATALOGUE_EMPTY')
    require(all(type(p) is str and p for p in data['configurations']), 'CATALOGUE_PATH_INVALID')
    timeout = data.get('timeout_seconds', 3600)
    require(type(timeout) is int and timeout > 0, 'CATALOGUE_TIMEOUT_INVALID')
    paths = [(catalogue.parent / p).resolve() for p in data['configurations']]
    require(len(paths) == len(set(paths)), 'BENCHMARK_CATALOGUE_DUPLICATE')
    require(not output.exists(), 'MATRIX_OUTPUT_ALREADY_EXISTS')
    output.mkdir(parents=True)
    catalogue_hash = sha_file(catalogue)
    # Enrollment contains every requested entry even if its preparation fails.
    rows = [{'configuration':str(p),'status':'NOT_STARTED'} for p in paths]
    write_json_new(output/'enrollment.json',{'catalogue_sha256':catalogue_hash,
        'configurations':[str(p) for p in paths], 'timeout_seconds':timeout})
    for i,(path,row) in enumerate(zip(paths,rows)):
        directory = output/f'benchmark_{i:03d}'; directory.mkdir()
        try:
            row['configuration_sha256'] = sha_file(path)
            lock = directory/'freeze.json'
            freeze(path, lock)
            row.update(status='FROZEN',freeze_sha256=sha_file(lock))
        except Exception as exc:
            row.update(status='PREPARATION_FAILED',error_type=type(exc).__name__)
    prepared = all(r['status']=='FROZEN' for r in rows)
    if prepared:
        try:
            require(sha_file(catalogue)==catalogue_hash,'CATALOGUE_CHANGED_DURING_PREPARATION')
            for i,(path,row) in enumerate(zip(paths,rows)):
                verify_freeze(path, output/f'benchmark_{i:03d}'/'freeze.json', row['freeze_sha256'])
        except Exception as exc:
            prepared = False
            # Whole-catalogue barrier fails before *any* benchmark is executed.
            for row in rows:
                row.update(status='PREPARATION_BARRIER_FAILED',error_type=type(exc).__name__)
    write_json_new(output/'catalogue_freeze.json',{'schema_version':'rveval.catalogue-freeze.v1',
        'catalogue_sha256':catalogue_hash,'prepared':prepared,'configurations':rows,
        'all_frozen_before_execution':prepared,'external_timestamp_attested':False})
    if prepared:
        for i,(path,row) in enumerate(zip(paths,rows)):
            directory=output/f'benchmark_{i:03d}'; lock=directory/'freeze.json'; run=directory/'run'
            try:
                require(sha_file(catalogue)==catalogue_hash,'CATALOGUE_CHANGED_AFTER_FREEZE')
                require(sha_file(path)==row['configuration_sha256'],'CONFIG_CHANGED_AFTER_CATALOGUE_FREEZE')
                argv=[sys.executable,'-m','rveval','run','--config',str(path),'--freeze',str(lock),
                      '--ack-freeze-sha256',row['freeze_sha256'],'--output-dir',str(run)]
                write_json_new(directory/'attempt.json',{'argv':argv,'automatic_retry':False,
                    'catalogue_freeze_sha256':sha_file(output/'catalogue_freeze.json')})
                rc=_run_child(argv,directory/'execution.log',cwd=path.parent,timeout=timeout)
                row.update(returncode=rc,execution_log_sha256=sha_file(directory/'execution.log'))
                require(rc==0,'BENCHMARK_EXECUTION_FAILED')
                manifest=read_json(run/'run_manifest.json')
                verified=verify_evidence(run,sha_file(run/'evidence_index.json'))
                row.update(status=manifest['status'],manifest=manifest,verification=verified)
            except Exception as exc:
                row.update(status='FAILED',error_type=type(exc).__name__)
            write_json_new(directory/'result.json',row)
    else:
        for i,row in enumerate(rows):
            if row['status']=='FROZEN': row['status']='NOT_RUN_PREPARATION_FAILED_ELSEWHERE'
            write_json_new(output/f'benchmark_{i:03d}'/'result.json',row)
    report={'schema_version':'rveval.matrix.v2','status':'PASS' if all(r['status']=='COMPLETED' for r in rows) else 'FAILED',
        'catalogue_sha256':catalogue_hash,'enrolled':len(rows),'completed':sum(r['status']=='COMPLETED' for r in rows),
        'all_frozen_before_execution':prepared,'process_isolation':True,
        'catalogue_freeze_sha256':sha_file(output/'catalogue_freeze.json'),'results':rows,
        'scope':'EXACT_LISTED_CONFIGURATIONS_NOT_EVERY_BENCHMARK_IN_EXISTENCE'}
    write_json_new(output/'matrix.json',report)
    return report
