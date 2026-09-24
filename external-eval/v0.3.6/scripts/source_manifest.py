"""Create a release manifest. Run only when producing a NEW release."""
from pathlib import Path
import hashlib,json,tomllib
ROOT=Path(__file__).resolve().parents[1]
IGNORED={'.git','.native','__pycache__','.pytest_cache','.venv','dist','build','results','.evidence-work'}
def source_files():
    files=[]
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if any(x in IGNORED or x.endswith('.egg-info') for x in rel.parts):continue
        if rel.as_posix()=='SOURCE_MANIFEST.json':continue
        if p.is_symlink():raise ValueError('SYMLINK_IN_RELEASE:'+str(rel))
        if p.is_file():files.append({'path':rel.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size})
    return files
if __name__=='__main__':
    manifest={'schema_version':'rveval.release-source-manifest.v2','version':tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version'],'files':source_files(),
              'excluded_self':'SOURCE_MANIFEST.json','independent_authentication':False}
    (ROOT/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(manifest['files'])}))
