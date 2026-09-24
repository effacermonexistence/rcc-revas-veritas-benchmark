#!/usr/bin/env python3
"""Reproducible local acceptance. Native third-party benchmarks are not substituted."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--skip-tests',action='store_true',help='Example runs only; never claims tests passed.')
    p.add_argument('--family',action='append',help='Select example family; default all.')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    commands=[];failures=[];skips=[]
    def call(label,argv,timeout=180):
        start=time.perf_counter();log=out/(label+'.log')
        with log.open('w') as f:
            try:rc=subprocess.run(argv,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
            except subprocess.TimeoutExpired:rc=124
        commands.append({'label':label,'command':argv,'returncode':rc,'elapsed_seconds':time.perf_counter()-start,'log':log.name,
                         'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
        if rc:failures.append(label)
        return rc
    try:
        if not a.skip_tests:
            call('pytest',[sys.executable,'-m','pytest','-q','-rA','--junitxml='+str(out/'pytest.xml')],timeout=240)
        families=a.family or ['static','stateful','rpc-qa','rpc-stateful','rpc-likelihood','rpc-artifact','rpc-batch','rpc-multimodal','rpc-deny','rpc-javascript']
        for family in families:
            if family=='static':cfg=ROOT/'examples/static_jsonl/config.json'
            elif family=='stateful':cfg=ROOT/'examples/stateful/config.json'
            elif family.startswith('rpc-'):cfg=ROOT/'examples/rpc'/(family[4:]+'.json')
            else:raise ValueError('UNKNOWN_EXAMPLE_FAMILY')
            if family=='rpc-javascript' and not shutil.which('node'):
                skips.append({'family':family,'reason':'NODE_RUNTIME_NOT_INSTALLED'});continue
            fp=out/(family+'-freeze.json');run=out/(family+'-run')
            if call(family+'-freeze',[sys.executable,'-m','rveval','freeze','--config',str(cfg),'--output',str(fp)]):continue
            pin=hashlib.sha256(fp.read_bytes()).hexdigest()
            if call(family+'-run',[sys.executable,'-m','rveval','run','--config',str(cfg),'--freeze',str(fp),'--ack-freeze-sha256',pin,'--output-dir',str(run)]):continue
            idx=run/'evidence_index.json';ipin=hashlib.sha256(idx.read_bytes()).hexdigest()
            call(family+'-verify',[sys.executable,'-m','rveval','verify','--run-dir',str(run),'--expected-index-sha256',ipin])
    except Exception as exc:failures.append(type(exc).__name__)
    result={'schema_version':'rveval.acceptance.v2','status':'PASS' if not failures else 'FAIL',
            'python':platform.python_version(),'platform':platform.platform(),'node_available':bool(shutil.which('node')),
            'tests_requested':not a.skip_tests,'commands':commands,'failures':failures,'skips':skips,
            'scope':'LOCAL_REFERENCE_FRAMEWORK_ACCEPTANCE','real_external_benchmarks_run':[],
            'native_RCC_VERITAS_end_to_end_run':False}
    (out/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if not failures else 2
if __name__=='__main__':raise SystemExit(main())
