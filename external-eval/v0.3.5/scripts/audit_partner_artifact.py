"""Verify the supplied historical archive without rerunning or modifying it."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def audit(path):
    expected='873ddde355be5a6a909fb6904fd88ea0346ffef176010e4fa7047b774869f7ab'
    archive_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if archive_sha!=expected:raise ValueError('ARCHIVE_PIN_MISMATCH')
    root='results/paired-clean-v1_2/'
    with zipfile.ZipFile(path) as z:
        def read(name):return json.loads(z.read(root+name))
        rows=[json.loads(x) for x in z.read(root+'paired_cases.jsonl').splitlines()]
        idx=read('evidence_index.json')
        mapping={
          'run_manifest_sha256':'run_manifest.json','summary_sha256':'summary.json',
          'environment_manifest_sha256':'environment_manifest.json','paired_cases_sha256':'paired_cases.jsonl',
          'governance_metrics_sha256':'governance_metrics.json','preservation_metrics_sha256':'preservation_metrics.json',
          'operational_metrics_sha256':'operational_metrics.json','rcc_run_bundle_seal_sha256':'rcc-run/bundle_seal.json',
          'registration_sha256':'rcc-registration/registration.json'}
        verified=[]
        for key,name in mapping.items():
            if hashlib.sha256(z.read(root+name)).hexdigest()!=idx[key]:raise ValueError('INDEX_HASH_MISMATCH:'+name)
            verified.append(name)
        hashes=read('rcc-run/hashes.json')
        for item in hashes['files']:
            data=z.read(root+'rcc-run/'+item['path'])
            if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('RCC_BUNDLE_MISMATCH:'+item['path'])
        recomputed={}
        for arm in ('arm_a','arm_b'):
            recomputed[arm]={'exact_agreement':sum(r[arm]==r['expected'] for r in rows),
                'enrolled':len(rows),'false_allow':sum(r[arm]=='ALLOW' and r['expected']!='ALLOW' for r in rows),
                'false_block':sum(r[arm]!='ALLOW' and r['expected']=='ALLOW' for r in rows)}
        result={'status':'PASS','archive_sha256':archive_sha,'archive_members':len(z.namelist()),
                'top_level_index_hashes_verified':len(verified),'rcc_bundle_files_verified':len(hashes['files']),
                'recomputed':recomputed,'changed_dispositions':sum(r['arm_a']!=r['arm_b'] for r in rows),
                'native_bind_gate_invocations':sum(bool(r.get('native_gate') and r['native_gate']['native_bind_gate_invoked']) for r in rows),
                'claim':'HISTORICAL_ARTIFACT_BYTE_AND_METRIC_RECOMPUTATION_NOT_NEW_NATIVE_EXECUTION'}
        return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--zip',type=Path,required=True);p.add_argument('--output',type=Path)
    a=p.parse_args();value=audit(a.zip);text=json.dumps(value,indent=2)
    if a.output:a.output.write_text(text+'\n')
    print(text)
