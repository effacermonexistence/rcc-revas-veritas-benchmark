#!/usr/bin/env python3
"""Execute installed native integrations and real-data matrices, never fake PASS.

Supply source roots from SOURCES_NATIVE.json. Missing dependencies are failures,
not skips. This validates native integration profiles; it does not silently launch
paid provider calls or claim full performance coverage for every benchmark task.
"""
from __future__ import annotations
import argparse, os, json, sys, subprocess, hashlib, platform, time
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    for k in ('rcc','veritas','agentdojo','tau','tau2'):p.add_argument('--'+k+'-source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--without-real-data',action='store_true',help='Integration-only; records omitted data run, does not claim it passed.')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    roots={k:getattr(a,k+'_source').resolve() for k in ('rcc','veritas','agentdojo','tau','tau2')}
    source_pins=json.loads((ROOT/'SOURCES_NATIVE.json').read_text())
    verified=[]
    for k,entries in source_pins['critical_files'].items():
        for entry in entries:
            f=roots[k]/entry['path'];h=hashlib.sha256(f.read_bytes()).hexdigest()
            if h!=entry['sha256']:raise RuntimeError('NATIVE_SOURCE_MISMATCH:'+k+':'+entry['path'])
            verified.append({'source':k,**entry})
    env={**os.environ,'PYTHONPATH':os.pathsep.join(map(str,[ROOT/'src',ROOT,roots['rcc'],roots['veritas'],roots['agentdojo']/'src',roots['tau'],roots['tau2']/'src'])),
         'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
         'RCC_SOURCE':str(roots['rcc']),'LITELLM_LOCAL_MODEL_COST_MAP':'True','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    attempts=[]
    def call(label,cmd,timeout=600):
        log=out/(label+'.log');start=time.monotonic()
        with log.open('w') as f:
            try:rc=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
            except subprocess.TimeoutExpired:rc=124
        row={'label':label,'returncode':rc,'seconds':time.monotonic()-start,'argv':cmd,'log':log.name,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()};attempts.append(row)
        return rc
    call('dependency-closure',[sys.executable,str(ROOT/'scripts/check_native_dependencies.py')])
    rc=call('native-tests',[sys.executable,'-m','pytest','tests','integration_tests','-q','--junitxml='+str(out/'tests.xml')])
    counts={}
    if (out/'tests.xml').exists():
        suites=ET.parse(out/'tests.xml').findall('.//testsuite')
        counts={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
    if not a.without_real_data:
        call('real-data',[sys.executable,'-m','rveval','matrix','--catalogue',str(ROOT/'examples/sklearn/catalogue.json'),'--output-dir',str(out/'real-data')])
    freeze=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True)
    (out/'environment.txt').write_text(freeze.stdout)
    success=all(c['returncode']==0 for c in attempts) and bool(counts.get('tests')) and all(counts[k]==0 for k in ('failures','errors','skipped'))
    result={'schema_version':'rveval.native-validation.v0.3','status':'PASS' if success else 'FAIL','test_counts':counts,'python':platform.python_version(),
      'scope':'EXACT_NATIVE_COMPONENT_BINDINGS_AND_SELECTED_REAL_DATA_NOT_ALL_TASK_PERFORMANCE',
      'runtime_env':{k:env[k] for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','LITELLM_LOCAL_MODEL_COST_MAP')},
      'real_data_requested':not a.without_real_data,'paid_model_calls_requested':False,'commands':attempts,'verified_native_critical_files':verified,
      'full_native_source_archive_pins':source_pins['repositories'],'environment_sha256':hashlib.sha256((out/'environment.txt').read_bytes()).hexdigest()}
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if success else 2
if __name__=='__main__':raise SystemExit(main())
