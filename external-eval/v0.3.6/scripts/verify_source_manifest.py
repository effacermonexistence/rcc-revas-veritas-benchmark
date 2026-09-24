"""Read-only source closure/hash verification. Does not refreeze changed source."""
from pathlib import Path
import json
from source_manifest import ROOT,source_files
expected=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
actual=source_files();good=actual==expected['files']
print(json.dumps({'status':'PASS' if good else 'FAIL','file_count':len(actual),'closure_and_bytes_match':good},indent=2))
raise SystemExit(0 if good else 2)
