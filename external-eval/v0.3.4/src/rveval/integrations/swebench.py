"""SWE-bench native prediction file writer and harness command constructor.

No gold patch, tests_patch or grading inputs enter the candidate. Execution of
untrusted patches belongs to the official container harness, not this process.
"""
from pathlib import Path
import json
import sys
from rveval.models import CandidateAction
from rveval.guardrails import require
from rveval.canonical import sha_json


class PredictionWriter:
    def __init__(self, output: Path, model_name: str, executor):
        self.path = Path(output)
        require(not self.path.exists(), 'SWE_PREDICTIONS_ALREADY_EXIST')
        require(type(model_name) is str and bool(model_name), 'SWE_MODEL_ID_REQUIRED')
        self.model_name, self.executor, self.seen = model_name, executor, set()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('x', encoding='utf-8')
    def add(self, instance_id: str, patch: str):
        require(type(instance_id) is str and bool(instance_id), 'SWE_INSTANCE_ID_REQUIRED')
        require(type(patch) is str, 'SWE_PATCH_MUST_BE_TEXT')
        require(instance_id not in self.seen, 'SWE_DUPLICATE_PREDICTION')
        cand = CandidateAction('artifact', name='patch', content=patch,
                               metadata={'instance_id': instance_id})
        def apply(c):
            require(c.name == 'patch' and c.metadata.get('instance_id') == instance_id,
                    'SWE_PREDICTION_ID_CHANGED')
            row = {'instance_id': instance_id, 'model_patch': c.content,
                   'model_name_or_path': self.model_name}
            require(type(c.content) is str, 'SWE_PATCH_MUST_BE_TEXT')
            self.file.write(json.dumps(row, ensure_ascii=False) + '\n')
            self.file.flush()
            import os
            os.fsync(self.file.fileno())
            self.seen.add(instance_id)
            return row
        return self.executor.call(cand, apply, operation_id=instance_id)
    def close(self): self.file.close()
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()


def native_harness_command(*, dataset_name: str, predictions_path: Path, run_id: str,
                           max_workers: int = 1, python: str = sys.executable):
    require(type(max_workers) is int and max_workers > 0, 'SWE_MAX_WORKERS_INVALID')
    require(Path(predictions_path).is_file(), 'SWE_PREDICTIONS_FILE_MISSING')
    return [python, '-m', 'swebench.harness.run_evaluation', '--dataset_name', dataset_name,
            '--predictions_path', str(Path(predictions_path).resolve()), '--run_id', run_id,
            '--max_workers', str(max_workers)]


def collect_native_reports(run_directory: Path, enrolled_ids: list[str]) -> dict:
    """Read official per-instance reports without interpreting missing work as success.

    PASS here means grading completed, NOT that a model solved every instance.
    Zero solved can be a valid measured model result. Infrastructure failures and
    absent/duplicate reports remain separately counted for the complete enrollment.
    """
    from rveval.canonical import read_json, sha_file
    require(bool(enrolled_ids) and len(enrolled_ids)==len(set(enrolled_ids)), 'SWE_ENROLLMENT_INVALID')
    expected=set(enrolled_ids);found={};unexpected=[]
    for path in Path(run_directory).rglob('report.json'):
        raw=read_json(path)
        require(type(raw) is dict, 'SWE_NATIVE_REPORT_SHAPE')
        for instance,result in raw.items():
            if instance not in expected:
                unexpected.append(instance);continue
            found.setdefault(instance,[]).append({'path':str(path),'sha256':sha_file(path),'result':result})
    rows=[]
    for instance in enrolled_ids:
        reports=found.get(instance,[])
        if len(reports)!=1:
            rows.append({'instance_id':instance,'status':'MISSING' if not reports else 'DUPLICATE','reports':reports});continue
        result=reports[0]['result']
        observed=(type(result) is dict and type(result.get('resolved')) is bool and
                  type(result.get('infra_failure')) is bool and result['infra_failure'] is False)
        rows.append({'instance_id':instance,'status':'GRADED' if observed else 'INFRASTRUCTURE_ERROR',
                     'resolved':result.get('resolved') if observed else None,'report':reports[0]})
    graded=sum(r['status']=='GRADED' for r in rows)
    return {'status':'PASS' if graded==len(rows) and not unexpected else 'FAIL',
            'scope':'OFFICIAL_GRADING_COMPLETION_NOT_ALL_INSTANCES_SOLVED',
            'enrolled':len(rows),'graded':graded,'ungraded':len(rows)-graded,
            'resolved':sum(r.get('resolved') is True for r in rows),'unexpected_report_ids':unexpected,'results':rows}


def run_native_grading(*, dataset_rows: list[dict], predictions_path: Path, output: Path,
                       run_id: str, max_workers: int = 1, timeout_seconds: int = 3600) -> dict:
    """Execute the installed official Docker scorer on exact frozen local records.

    This is SCORER-ONLY input: rows contain official test metadata and may include
    reference patches. Call only after model/gate decisions are sealed. The rows
    are never converted into candidates or authority and never sent to RCC/VERITAS.
    Docker and the images named by the official records must be available.
    """
    import inspect, os, re, subprocess, signal
    from importlib.metadata import version
    from rveval.canonical import read_json, write_json_new, sha_file
    from swebench.harness.utils import make_test_spec
    from swebench.harness.constants import RUN_EVALUATION_LOG_DIR
    require(type(run_id) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',run_id) is not None,
            'SWE_RUN_ID_INVALID')
    require(type(timeout_seconds) is int and timeout_seconds>0,'SWE_TIMEOUT_INVALID')
    require(type(dataset_rows) is list and bool(dataset_rows),'SWE_DATASET_EMPTY')
    # Use the actual installed native schema rather than inventing missing image,
    # evaluation-script or parser values for an incompatible dataset revision.
    ids=[]
    for record in dataset_rows:
        require(type(record) is dict,'SWE_DATASET_RECORD_INVALID')
        try: spec=make_test_spec(record)
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError('SWE_DATASET_GRADER_SCHEMA_MISMATCH: '+str(exc)) from exc
        ids.append(spec.instance_id)
    require(len(ids)==len(set(ids)),'SWE_DUPLICATE_DATASET_ID')
    predictions=Path(predictions_path).resolve()
    require(predictions.is_file(),'SWE_PREDICTIONS_FILE_MISSING')
    raw=predictions.read_bytes();decoded=raw.decode('utf-8')
    rows=[json.loads(line) for line in decoded.splitlines() if line.strip()]
    require(all(type(r) is dict and type(r.get('instance_id')) is str and
                type(r.get('model_patch')) is str and type(r.get('model_name_or_path')) is str for r in rows),
            'SWE_PREDICTION_SCHEMA_INVALID')
    prediction_ids=[r['instance_id'] for r in rows]
    require(len(prediction_ids)==len(set(prediction_ids)) and set(prediction_ids)==set(ids),
            'SWE_PREDICTION_COVERAGE_MISMATCH')
    output=Path(output).resolve();require(not output.exists(),'SWE_RUN_DIRECTORY_ALREADY_EXISTS')
    output.mkdir(parents=True)
    sealed_predictions=output/'predictions.jsonl';sealed_predictions.write_bytes(raw)
    dataset_file=output/'scorer-only-dataset.json';write_json_new(dataset_file,dataset_rows)
    command=native_harness_command(dataset_name=str(dataset_file),predictions_path=sealed_predictions,
                                  run_id=run_id,max_workers=max_workers)
    command += ['--instance_ids',*ids]
    registration={'run_id':run_id,'enrolled_ids':ids,'swebench_version':version('swebench'),
        'native_schema_source_sha256':sha_file(Path(inspect.getsourcefile(make_test_spec))),
        'dataset_sha256':sha_file(dataset_file),'predictions_sha256':sha_file(sealed_predictions),
        'command':command,'automatic_retry':False,'scope':'SCORER_ONLY_AFTER_DECISION_LOCK'}
    write_json_new(output/'registration.json',registration)
    rc=None
    try:
        with (output/'grader.log').open('xb') as stream:
            process=subprocess.Popen(command,cwd=output,stdout=stream,stderr=subprocess.STDOUT,
                                     start_new_session=os.name!='nt')
            try:rc=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                if os.name=='nt':process.kill()
                else:os.killpg(process.pid,signal.SIGKILL)
                process.wait();rc=124
    except OSError as exc:
        write_json_new(output/'launch-error.json',{'type':type(exc).__name__,'message':str(exc)})
        rc=127
    result=collect_native_reports(output/RUN_EVALUATION_LOG_DIR/run_id,ids)
    result.update(returncode=rc,registration_sha256=sha_file(output/'registration.json'),
                  grader_log_sha256=sha_file(output/'grader.log') if (output/'grader.log').exists() else None)
    unchanged=(sha_file(dataset_file)==registration['dataset_sha256'] and
               sha_file(sealed_predictions)==registration['predictions_sha256'])
    result['frozen_inputs_preserved']=unchanged
    if rc!=0 or not unchanged:result['status']='FAIL'
    write_json_new(output/'result.json',result)
    return result
