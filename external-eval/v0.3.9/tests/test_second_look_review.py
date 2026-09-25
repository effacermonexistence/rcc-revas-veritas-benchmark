"""Separate second-look lifecycle, live-source and relocation probes."""
from pathlib import Path
import json, os, signal, subprocess, sys, time
import pytest
from rveval.canonical import read_json, sha_file, write_json_new
from rveval.freeze import freeze
from rveval.runner import execute
from rveval.evidence import verify_evidence
from rveval.pilot import initialize_pilot
from rveval.native_job import execute_native_job


def test_step_source_change_during_execution_cannot_be_scored_successfully(tmp_path, monkeypatch):
    from tests import support_plugins
    original = support_plugins.Gate.review
    asset = tmp_path / 'frozen-contract.txt'; asset.write_text('frozen version')
    def changed(self, **kwargs):
        asset.write_text('changed in execution')
        return original(self, **kwargs)
    monkeypatch.setattr(support_plugins.Gate, 'review', changed)
    cfg={'run_mode':'live','seed':7,
         'benchmark':{'plugin':'tests.support_plugins:Adapter','config':{'mode':'ok'}},
         'agent':{'plugin':'tests.support_plugins:AgentImpl','config':{'mode':'ok'}},
         'rcc':{'plugin':'tests.support_plugins:Gate','config':{'mode':'ok'}},
         'veritas':{'plugin':'tests.support_plugins:VGate','config':{'mode':'ALLOW'}},
         'assets':[str(asset)]}
    cp=tmp_path/'config.json';write_json_new(cp,cfg);fp=tmp_path/'freeze.json';freeze(cp,fp)
    result=execute(cp,fp,sha_file(fp),tmp_path/'run')
    assert result['status']!='COMPLETED','Changed frozen asset silently scored as a valid run'
    for row in (tmp_path/'run').glob('case_*.json'):
        assert read_json(row)['aggregation_eligible'] is False
    assert verify_evidence(tmp_path/'run',sha_file(tmp_path/'run/evidence_index.json'))['status']=='PASS'


def test_rpc_keyboard_interrupt_closes_worker(tmp_path,monkeypatch):
    from rveval.rpc import JsonProcess
    channel=JsonProcess({'command':[sys.executable,'-c','import time; time.sleep(60)']},tmp_path)
    def interrupt(*args):raise KeyboardInterrupt()
    monkeypatch.setattr(channel,'_line',interrupt)
    try:
        with pytest.raises(KeyboardInterrupt):channel.call('work')
        assert channel.closed and channel.process is None,'Interrupted RPC worker left live'
    finally:channel.close()


@pytest.mark.skipif(os.name!='posix', reason='POSIX signal propagation contract')
def test_matrix_parent_termination_cancels_running_child(tmp_path):
    marker=tmp_path/'late.txt'; ready=tmp_path/'ready.txt'
    worker=tmp_path/'wait.py';worker.write_text('from pathlib import Path\nimport time\nPath('+repr(str(ready))+').write_text("ready")\ntime.sleep(1.2)\nPath('+repr(str(marker))+').write_text("late")\n')
    parent=tmp_path/'matrix-parent.py';parent.write_text('from rveval.matrix import _run_child\nfrom pathlib import Path\nimport sys\n_run_child([sys.executable,'+repr(str(worker))+'],Path('+repr(str(tmp_path/'child.log'))+'),cwd=Path('+repr(str(tmp_path))+'),timeout=10)\n')
    p=subprocess.Popen([sys.executable,str(parent)],start_new_session=True)
    try:
        end=time.monotonic()+5
        while not ready.exists() and time.monotonic()<end:time.sleep(.01)
        assert ready.exists(),'Probe child never started'
        p.send_signal(signal.SIGTERM);p.wait(timeout=5);time.sleep(1.3)
        assert not marker.exists(),'Matrix child kept executing after parent was terminated'
    finally:
        if p.poll() is None:p.kill();p.wait()


@pytest.mark.parametrize('backend',['native','step'])
def test_exact_noncanonical_acknowledged_freeze_bytes_survive_recording(tmp_path,backend):
    if backend=='native':
        p=tmp_path/'new pilot 한글';initialize_pilot(p,'공동 검증');cp=p/'config.json';fn=execute_native_job
    else:
        root=Path(__file__).resolve().parents[1];cfg=read_json(root/'examples/static_jsonl/config.json')
        for role,key in [('benchmark','cases_path'),('benchmark','labels_path'),('agent','actions_path')]:
            cfg[role]['config'][key]=str(root/'examples/static_jsonl'/cfg[role]['config'][key])
        cp=tmp_path/'config.json';write_json_new(cp,cfg);p=tmp_path;fn=execute
    fp=p/'freeze.json';freeze(cp,fp)
    fp.write_text(json.dumps(read_json(fp),indent=3)+' \n')
    result=fn(cp,fp,sha_file(fp),p/'run')
    assert result['status']=='COMPLETED',result
    assert verify_evidence(p/'run',sha_file(p/'run/evidence_index.json'))['status']=='PASS'


def test_relocated_native_evidence_remains_verifiable(tmp_path):
    import shutil
    p=tmp_path/'pilot';initialize_pilot(p,'relocate');fp=p/'freeze.json';freeze(p/'config.json',fp)
    assert execute_native_job(p/'config.json',fp,sha_file(fp),p/'run')['status']=='COMPLETED'
    destination=tmp_path/'別のフォルダ with spaces';shutil.copytree(p/'run',destination)
    shutil.rmtree(p)
    assert verify_evidence(destination,sha_file(destination/'evidence_index.json'))['status']=='PASS'
