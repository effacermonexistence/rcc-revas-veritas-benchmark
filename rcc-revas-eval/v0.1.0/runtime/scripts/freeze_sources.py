#!/usr/bin/env python3
"""Author-time release step. Never run automatically to repair a failed preflight."""
from pathlib import Path
import json
import hashlib
ROOT = Path(__file__).resolve().parent.parent
paths = {"pyproject.toml", "evaluation_manifest.json"}
for folder, pattern in (("rcc_revas_eval", "*.py"), ("schemas", "*.json"), ("policies", "*.json")):
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).glob(pattern))
files = []
for rel in sorted(paths):
    p = ROOT / rel
    if p.is_symlink():
        raise SystemExit("Symlinks are forbidden")
    data = p.read_bytes()
    files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
obj = {"schema_version": "rcc-revas.source-manifest.v1", "files": files,
       "exclusions": ["this manifest", "docs", "tests", "fixtures", "review results", "git metadata"],
       "reason": "Runtime-only source identity must not depend on scoring labels or post-run evidence."}
(ROOT / 'source_manifest.json').write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
print(f"Frozen {len(files)} runtime files.")
