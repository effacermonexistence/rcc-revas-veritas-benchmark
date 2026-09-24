"""Finite UTF-8 JSON profile, not RFC 8785/JCS. No duplicate keys or NaN."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

PROFILE = "rveval.python-finite-json.v2"

def validate_json(value: Any, depth: int = 0) -> None:
    if depth > 100:
        raise ValueError("JSON_DEPTH_LIMIT")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("NONFINITE_JSON_NUMBER")
        return
    if type(value) is list:
        for x in value: validate_json(x, depth + 1)
        return
    if type(value) is dict:
        for k, v in value.items():
            if type(k) is not str: raise ValueError("NONSTRING_JSON_KEY")
            validate_json(v, depth + 1)
        return
    raise ValueError(f"NON_JSON_TYPE:{type(value).__name__}")

def canonical_bytes(value: Any) -> bytes:
    validate_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")

def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha_json(value: Any) -> str:
    return sha_bytes(canonical_bytes(value))

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def _pairs(items):
    out = {}
    for k,v in items:
        if k in out: raise ValueError(f"DUPLICATE_JSON_KEY:{k}")
        out[k] = v
    return out

def _constant(value):
    raise ValueError(f"NONFINITE_JSON_NUMBER:{value}")

def loads(value: str | bytes) -> Any:
    result = json.loads(value, object_pairs_hook=_pairs, parse_constant=_constant)
    validate_json(result)
    return result

def read_json(path: Path) -> Any:
    return loads(Path(path).read_bytes())

def write_json_new(path: Path, value: Any) -> None:
    # Validate before creating a file: failures never leave a partial JSON file.
    payload = canonical_bytes(value) + b"\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
