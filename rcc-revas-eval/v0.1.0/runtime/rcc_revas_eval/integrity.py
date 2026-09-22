"""Strict JSON, explicit digest namespaces, safe paths and deterministic receipts.

rcc-json-v1 is NOT RFC 8785: no floating-point values, no Unicode normalization,
UTF-8, sorted keys, array order retained, no spaces, safe integers only.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

PROFILE = "rcc-json-v1:utf8-sortkeys-noascii-no-floats-safeint"
MAX_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 48

class ContractError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}" if detail else code)

def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ContractError(code, detail)

def validate_json(value: Any, depth: int = 0) -> None:
    require(depth <= MAX_DEPTH, "JSON_TOO_DEEP")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(abs(value) <= 2**53 - 1, "UNSAFE_INTEGER")
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise ContractError("INVALID_UNICODE") from exc
        return
    if type(value) is list:
        for item in value:
            validate_json(item, depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, "NON_STRING_KEY")
            validate_json(key, depth + 1)
            validate_json(item, depth + 1)
        return
    raise ContractError("UNSUPPORTED_JSON_TYPE", type(value).__name__)

def canonical(value: Any) -> bytes:
    validate_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def raw_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def digest(value: Any, namespace: str) -> str:
    require(type(namespace) is str and bool(namespace), "DIGEST_NAMESPACE_REQUIRED")
    return raw_sha(namespace.encode("ascii") + b"\x00" + canonical(value))

def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        require(key not in out, "DUPLICATE_JSON_KEY", key)
        out[key] = value
    return out

def _nonfinite(value: str) -> None:
    raise ContractError("NONFINITE_JSON", value)

def loads(data: bytes | str) -> Any:
    require(len(data) <= MAX_BYTES, "INPUT_TOO_LARGE")
    try:
        value = json.loads(data, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("INVALID_JSON", str(exc)) from exc
    validate_json(value)
    return value

def read_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), "INPUT_FILE_INVALID", str(path))
    require(path.stat().st_size <= MAX_BYTES, "INPUT_TOO_LARGE", str(path))
    return loads(path.read_bytes())

def write_json(path: Path, value: Any) -> None:
    validate_json(value)
    require(not path.exists(), "REFUSE_OVERWRITE", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                indent=2, allow_nan=False).encode("utf-8") + b"\n")

def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join(canonical(row) + b"\n" for row in rows)

def read_jsonl(path: Path) -> list[dict]:
    require(path.is_file() and not path.is_symlink(), "INPUT_FILE_INVALID", str(path))
    require(path.stat().st_size <= MAX_BYTES, "INPUT_TOO_LARGE")
    rows = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        require(bool(line.strip()), "BLANK_JSONL_ROW", str(line_number))
        value = loads(line)
        require(type(value) is dict, "JSONL_ROW_NOT_OBJECT", str(line_number))
        rows.append(value)
    require(bool(rows), "EMPTY_INPUT")
    return rows

def safe_path(root: Path, relative: str) -> Path:
    require(type(relative) is str and relative != "" and "\\" not in relative,
            "UNSAFE_PATH", str(relative))
    pure = PurePosixPath(relative)
    require(not pure.is_absolute() and all(p not in (".", "..", "") for p in pure.parts)
            and pure.as_posix() == relative, "UNSAFE_PATH", relative)
    target = root.joinpath(*pure.parts)
    current = root
    require(not current.is_symlink(), "SYMLINK_FORBIDDEN", str(current))
    for part in pure.parts:
        current = current / part
        require(not current.is_symlink(), "SYMLINK_FORBIDDEN", str(current))
    require(target.resolve().is_relative_to(root.resolve()), "PATH_ESCAPE", relative)
    return target

def timestamp(text: str) -> datetime:
    require(type(text) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text)
            is not None, "UTC_TIMESTAMP_REQUIRED", str(text))
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContractError("INVALID_TIMESTAMP", text) from exc

def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def exact_keys(obj: Any, required: set[str], optional: set[str] | None = None,
               where: str = "object") -> None:
    require(type(obj) is dict, "OBJECT_REQUIRED", where)
    require(required <= obj.keys(), "MISSING_FIELD", where + ": " + ",".join(sorted(required - obj.keys())))
    extra = obj.keys() - required - (optional or set())
    require(not extra, "UNEXPECTED_FIELD", where + ": " + ",".join(sorted(extra)))

def text(value: Any, where: str) -> None:
    require(type(value) is str and bool(value.strip()) and len(value) <= 10000,
            "NONEMPTY_STRING_REQUIRED", where)

def strings(value: Any, where: str, nonempty: bool = False) -> None:
    require(type(value) is list and (not nonempty or bool(value)), "STRING_LIST_REQUIRED", where)
    for item in value:
        text(item, where)
    require(len(value) == len(set(value)), "DUPLICATE_LIST_VALUE", where)
