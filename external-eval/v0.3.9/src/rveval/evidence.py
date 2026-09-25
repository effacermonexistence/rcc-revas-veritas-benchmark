"""Write-once records, fsynced intent journal, closure verification."""
from __future__ import annotations
import os
import platform
import sys
from pathlib import Path
from .canonical import canonical_bytes, sha_file, sha_json, read_json, loads, write_json_new
from .guardrails import require


def environment_manifest():
    return {"python": sys.version, "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(),
            "github_actions": os.environ.get("GITHUB_ACTIONS"), "image_os": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
            "process_isolation": "TRUSTED_LOCAL_PLUGINS_NOT_AN_OS_SECURITY_SANDBOX"}

class Journal:
    def __init__(self, path):
        self.path=Path(path); self.previous=None; self.sequence=0
        self._file=self.path.open("xb")
    def append(self, event, payload):
        entry={"sequence": self.sequence, "event": event, "payload": payload, "previous_sha256": self.previous}
        entry["sha256"]=sha_json(entry)
        self._file.write(canonical_bytes(entry)+b"\n"); self._file.flush(); os.fsync(self._file.fileno())
        self.sequence+=1; self.previous=entry["sha256"]
    def close(self): self._file.close()

def evidence_index(directory):
    directory=Path(directory); files=[]
    for p in sorted(directory.rglob("*")):
        require(not p.is_symlink(), "EVIDENCE_SYMLINK_FORBIDDEN")
        if p.is_file() and p.relative_to(directory).as_posix()!="evidence_index.json":
            files.append({"path": p.relative_to(directory).as_posix(), "sha256": sha_file(p), "size_bytes": p.stat().st_size})
    return {"schema_version": "rveval.evidence-index.v2", "algorithm": "sha256/raw-bytes", "files": files,
            "external_authentication": False}

def write_evidence_index(directory):
    idx=evidence_index(directory); write_json_new(Path(directory)/"evidence_index.json", idx); return idx

def verify_evidence(directory, expected_index_sha256):
    directory=Path(directory)
    require(sha_file(directory/"evidence_index.json")==expected_index_sha256, "EVIDENCE_INDEX_PIN_MISMATCH")
    wanted=read_json(directory/"evidence_index.json")
    require(sha_json(wanted)==sha_json(evidence_index(directory)), "EVIDENCE_CLOSURE_OR_HASH_MISMATCH")
    previous=None; count=0
    for line in (directory/"journal.jsonl").read_bytes().splitlines():
        entry=loads(line); digest=entry.pop("sha256")
        require(entry["sequence"]==count and entry["previous_sha256"]==previous and sha_json(entry)==digest,
                "JOURNAL_CHAIN_MISMATCH")
        previous=digest; count+=1
    from .run_validation import validate_run_records
    structural = validate_run_records(directory)
    return {"status": "PASS", "record_consistency": structural, "files_verified": len(wanted["files"]), "journal_entries": count,
            "index_sha256": expected_index_sha256, "claim": "BYTE_INTEGRITY_AND_VERSIONED_RECORD_CONSISTENCY_NOT_SCORER_TRUTH_OR_ORIGIN"}
