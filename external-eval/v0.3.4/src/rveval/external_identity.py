from __future__ import annotations
import subprocess
from pathlib import Path
from .canonical import sha_file
from .guardrails import require

def declared_source_identity(config, base_dir):
    out=[]
    for raw in config.get("source_files", []):
        p = base_dir / raw
        require(not p.is_symlink() and p.is_file(), "DECLARED_SOURCE_MISSING", raw)
        out.append({"path": raw, "sha256": sha_file(p), "size_bytes": p.stat().st_size})
    return out

def repository_identities(config, base_dir):
    out=[]
    for spec in config.get("source_repositories", []):
        root = (base_dir / spec["path"]).resolve()
        def git(*args):
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                  text=True, check=True, timeout=20).stdout.strip()
        head = git("rev-parse", "HEAD")
        require(head == spec["commit"], "DEPENDENCY_REPO_PIN_MISMATCH", spec["path"])
        require(not git("status", "--porcelain", "--untracked-files=all"), "DEPENDENCY_REPO_DIRTY", spec["path"])
        out.append({"path": spec["path"], "commit": head, "tree": git("rev-parse", "HEAD^{tree}")})
    return out
