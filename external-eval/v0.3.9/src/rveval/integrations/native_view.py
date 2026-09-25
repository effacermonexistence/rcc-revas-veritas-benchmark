"""Typed governance view of native payloads; native objects remain native.

Binary/tensor/image payloads are content-addressed, not coerced to string. This
view is NOT a decoder or a security sandbox. Call the native method with the
original objects and recheck this view before invocation. No hidden Instance.doc
or whole TaskState is projected automatically.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, math, struct, os
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from rveval.guardrails import require


class NativeView:
    def __init__(self, blob_dir: Path | None = None):
        self.blob_dir = Path(blob_dir) if blob_dir is not None else None
    def _blob(self, data: bytes) -> dict:
        digest = hashlib.sha256(data).hexdigest()
        if self.blob_dir is not None:
            self.blob_dir.mkdir(parents=True, exist_ok=True)
            p = self.blob_dir / digest
            if p.exists():
                require(not p.is_symlink() and p.read_bytes() == data, 'NATIVE_BLOB_COLLISION')
            else:
                try:
                    with p.open('xb') as f:
                        f.write(data); f.flush(); os.fsync(f.fileno())
                except FileExistsError:
                    require(not p.is_symlink() and p.read_bytes() == data, 'NATIVE_BLOB_COLLISION')
        return {'sha256': digest, 'bytes': len(data), 'storage': 'CONTENT_ADDRESSED' if self.blob_dir else 'DIGEST_ONLY'}
    def _dtype(self, dtype):
        """Preserve named fields, offsets, subarrays and metadata, not only |Vn."""
        result = {'str': dtype.str, 'itemsize': dtype.itemsize,
                  'alignment': dtype.alignment, 'aligned': bool(dtype.isalignedstruct)}
        if dtype.fields is not None:
            fields = []
            for name in dtype.names:
                entry = dtype.fields[name]
                fields.append({'name': name, 'dtype': self._dtype(entry[0]),
                               'offset': entry[1],
                               'title': self.encode(entry[2]) if len(entry) > 2 else None})
            result['fields'] = fields
        if dtype.subdtype is not None:
            base, shape = dtype.subdtype
            result['subarray'] = {'dtype': self._dtype(base), 'shape': list(shape)}
        if dtype.metadata is not None:
            result['metadata'] = self.encode(dict(dtype.metadata))
        return result

    def encode(self, value):
        if value is None or type(value) in (str, bool, int): return value
        if type(value) is float:
            return value if math.isfinite(value) else {'__rveval_type__': 'float64', 'ieee754_hex': struct.pack('>d', value).hex()}
        if type(value) is Decimal:
            parts = value.as_tuple()
            return {'__rveval_type__': 'decimal', 'sign': parts.sign,
                    'digits': list(parts.digits), 'exponent': parts.exponent}
        if type(value) is Fraction:
            return {'__rveval_type__': 'fraction', 'numerator': value.numerator, 'denominator': value.denominator}
        if type(value) is complex:
            return {'__rveval_type__': 'complex128', 'real': self.encode(value.real), 'imaginary': self.encode(value.imag)}
        if type(value) is bytes: return {'__rveval_type__': 'bytes', **self._blob(value)}
        if type(value) in (list, tuple):
            items = [self.encode(x) for x in value]
            return items if type(value) is list else {'__rveval_type__': 'tuple', 'items': items}
        if type(value) is dict:
            require(all(type(k) is str for k in value), 'NATIVE_MAPPING_KEYS_MUST_BE_STRINGS')
            # User keys are retained, so scorer-key guards can still reject them.
            require('__rveval_type__' not in value, 'NATIVE_VIEW_RESERVED_TAG')
            return {k: self.encode(v) for k, v in value.items()}
        if isinstance(value, (datetime, date)):
            return {'__rveval_type__': type(value).__name__, 'iso8601': value.isoformat()}
        module = type(value).__module__
        if module.startswith('numpy'):
            import numpy as np
            if isinstance(value, np.generic):
                require(not value.dtype.hasobject, 'OBJECT_SCALAR_UNSUPPORTED')
                return {'__rveval_type__': 'numpy_scalar', 'dtype': str(value.dtype),
                        'dtype_schema': self._dtype(value.dtype), **self._blob(value.tobytes())}
            if isinstance(value, np.ndarray):
                require(not value.dtype.hasobject, 'OBJECT_ARRAY_UNSUPPORTED')
                return {'__rveval_type__': 'ndarray', 'dtype': value.dtype.str, 'shape': list(value.shape),
                        'order': 'C', 'dtype_schema': self._dtype(value.dtype),
                        **self._blob(value.tobytes(order='C'))}
        if module.startswith('torch'):
            import torch
            if isinstance(value, torch.Tensor):
                require(value.layout == torch.strided, 'SPARSE_TENSOR_REQUIRES_EXPLICIT_CODEC')
                raw = value.detach().resolve_conj().resolve_neg().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
                return {'__rveval_type__': 'tensor', 'dtype': str(value.dtype), 'shape': list(value.shape),
                        'device': str(value.device), **self._blob(raw)}
        if module.startswith('PIL'):
            from PIL.Image import Image
            if isinstance(value, Image):
                require(getattr(value, 'n_frames', 1) == 1, 'ANIMATED_IMAGE_REQUIRES_EXPLICIT_ASSET_PROJECTION')
                return {'__rveval_type__': 'image', 'mode': value.mode, 'size': list(value.size),
                        'palette': self.encode(value.getpalette()), 'info': self.encode(value.info), **self._blob(value.tobytes())}
        raise TypeError('NATIVE_TYPE_REQUIRES_EXPLICIT_PROJECTION:' + module + '.' + type(value).__qualname__)
