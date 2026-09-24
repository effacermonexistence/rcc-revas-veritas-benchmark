"""A real native-owned computation loop; not a task benchmark or full VERITAS.

This runs pure Python matrix algebra, a lazy stream, async fan-in and binary
signal arithmetic, without converting those algorithms into reset/step sessions.
The local RCC output-contract gate runs before native calculation. VERITAS is
explicitly NOT present in this transport/parity reference, not a fake treatment.
Replace the body with the actual native benchmark/agent and NativeBindExecutor.
"""
from pathlib import Path
import argparse, asyncio, hashlib, json, math, struct
from datetime import datetime, timezone
from rveval.canonical import read_json, sha_file, write_json_new, sha_json
from rveval.models import CandidateAction
from rveval.native_hook import NativeGovernanceHook
from rveval.integrations.boundary import GovernedExecutor
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.partner_mapping import build_runtime_packet

ROOT = Path(__file__).resolve().parent


def native_calculation(case):
    if case == 'matrix/inverse':
        # Native batch operation, not a model score.
        a, b, c, d = 4., 7., 2., 6.; determinant = a*d-b*c
        return [[d/determinant, -b/determinant], [-c/determinant, a/determinant]]
    if case == 'stream/statistics':
        data = (float(x) for x in range(101)); n=0; mean=0.; s=0.
        for x in data:
            n+=1; delta=x-mean; mean+=delta/n; s+=delta*(x-mean)
        return {'count':n,'mean':mean,'population_variance':s/n}
    if case == 'async/fan-in':
        async def run():
            async def one(x): await asyncio.sleep(0); return x*x
            return await asyncio.gather(*(one(x) for x in range(8)))
        return asyncio.run(run())
    if case == 'bytes/audio':
        raw=struct.pack('<8h',1,-1,2,-2,3,-3,4,-4)
        samples=struct.unpack('<8h',raw)
        return {'pcm_sha256':hashlib.sha256(raw).hexdigest(),'rms':math.sqrt(sum(x*x for x in samples)/len(samples))}
    raise ValueError('UNSUPPORTED_EXAMPLE_CASE')


def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    request=read_json(a.request); out=a.output; digest=sha_file(a.request)
    if request['phase']=='execute':
        assert 'scorer_inputs' not in request
        policy=ROOT/'policy.json'
        gate=ExternalRCCGate({'policy':str(policy),'policy_sha256':sha_file(policy)},ROOT)
        rows=[]
        for i,cid in enumerate(request['case_ids']):
            for arm in request['arms']:
                trace=[];candidate=CandidateAction('custom',name=cid,arguments={})
                executor=GovernedExecutor(NativeGovernanceHook(gate),snapshot=lambda: {'runtime':'pure-independent-computation'},
                    context=lambda c:{'task':{'request_id':cid,'operation':cid}},journal=lambda k,v:trace.append({'event':k,'payload':v}))
                result=executor.call(candidate,lambda c:native_calculation(c.name))
                packet=build_runtime_packet(candidate=candidate,rcc_decision=gate.review(candidate=candidate,context={'task':{'operation':cid}}),
                    request={'id':cid,'query':'Run the declared native engineering computation.','source_ref':'native-job-request:sha256:'+digest},
                    source_refs=[],produced_at=datetime.now(timezone.utc))
                path=out/f'{i}-{arm}.json';write_json_new(path,{'case_id':cid,'arm':arm,'prediction':result.value,'trace':trace,'partner_packet':packet,
                    'native_veritas_invoked':False,'comparison_role':'IDENTICAL_ENGINEERING_CONTROL_NOT_VERITAS_TREATMENT'})
                rows.append({'case_id':cid,'arm':arm,'status':'COMPLETED','artifacts':[{'path':path.name,'sha256':sha_file(path)}]})
        write_json_new(out/'execution.json',{'schema_version':'rveval.native-execution.v1','request_sha256':digest,'records':rows})
    elif request['phase']=='score':
        execution=Path(request['execution_directory']); values=[]
        for i,cid in enumerate(request['case_ids']):
            left=read_json(execution/f'{i}-A.json')['prediction'];right=read_json(execution/f'{i}-B.json')['prediction']
            values.append({'case_id':cid,'identical':left==right,'native_value_A':left,'native_value_B':right})
        scorefile=out/'native-score.json';write_json_new(scorefile,{'metric':'native-loop-parity-not-capability','rows':values})
        write_json_new(out/'scores.json',{'schema_version':'rveval.native-scores.v1','request_sha256':digest,'status':'COMPLETED',
            'scored_case_ids':request['case_ids'],'arms':request['arms'],'native_score_files':[{'path':scorefile.name,'sha256':sha_file(scorefile)}]})
    else:raise ValueError('UNKNOWN_PHASE')
    return 0
if __name__=='__main__':raise SystemExit(main())
