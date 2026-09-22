"""Strict finite external JSON, kept separate from rcc-json-v1 integer hashing.

Raw response bytes, not a reserialized float representation, are the transport
receipt's primary evidence. This module never changes the internal hash profile.
"""
from __future__ import annotations
import json
import math
from typing import Any
from .integrity import ContractError, require

MAX_WIRE_BYTES = 4_000_000

def _pairs(pairs):
    d = {}
    for k, v in pairs:
        require(k not in d, "WIRE_DUPLICATE_KEY", k)
        d[k] = v
    return d

def _bad_constant(x):
    raise ContractError("WIRE_NONFINITE_NUMBER", x)

def _validate(v: Any, depth: int = 0) -> None:
    require(depth <= 48, "WIRE_DEPTH_EXCEEDED")
    t = type(v)
    if t in (type(None), bool, str):
        if t is str:
            try:
                v.encode("utf-8", "strict")
            except UnicodeError as e:
                raise ContractError("WIRE_INVALID_UNICODE") from e
        return
    if t is int:
        require(abs(v) <= 2**53-1, "WIRE_INTEGER_OUT_OF_RANGE")
        return
    if t is float:
        require(math.isfinite(v), "WIRE_NONFINITE_NUMBER")
        return
    require(t in (dict, list), "WIRE_TYPE_UNSUPPORTED", t.__name__)
    if t is dict:
        require(all(type(k) is str for k in v), "WIRE_KEY_TYPE")
        for k in v:
            _validate(k, depth+1)
    for x in (v.values() if t is dict else v):
        _validate(x, depth+1)

def wire_loads(raw: bytes | str) -> Any:
    data = raw.encode("utf-8") if type(raw) is str else raw
    require(type(data) is bytes and len(data) <= MAX_WIRE_BYTES, "WIRE_SIZE_EXCEEDED")
    try:
        v = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_pairs, parse_constant=_bad_constant)
        _validate(v)
        return v
    except (UnicodeError, ValueError, RecursionError) as e:
        if isinstance(e, ContractError):
            raise
        raise ContractError("WIRE_INVALID_JSON", type(e).__name__) from e

def wire_bytes(value: Any) -> bytes:
    _validate(value)
    b = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    require(len(b) <= MAX_WIRE_BYTES, "WIRE_SIZE_EXCEEDED")
    return b
