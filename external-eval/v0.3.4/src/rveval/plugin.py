from __future__ import annotations
import importlib
import inspect
from pathlib import Path
from .canonical import sha_file

def load_class(spec: str):
    if not isinstance(spec, str) or ":" not in spec: raise ValueError("PLUGIN_MUST_BE_MODULE_CLASS")
    module_name, class_name = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), class_name)

def instantiate(spec, config, base_dir):
    return load_class(spec)(config, base_dir)

def source_closure(root: Path) -> list[dict]:
    result = []
    for p in sorted(root.rglob("*")):
        if p.is_symlink(): raise ValueError(f"SYMLINK_IN_SOURCE_CLOSURE:{p}")
        if p.is_file() and p.suffix in {".py", ".json", ".toml", ".yaml", ".yml"} and "__pycache__" not in p.parts:
            result.append({"path": p.relative_to(root).as_posix(), "sha256": sha_file(p)})
    return result

def plugin_identity(spec):
    cls = load_class(spec)
    path = inspect.getsourcefile(cls)
    if not path: raise ValueError(f"PLUGIN_SOURCE_UNINSPECTABLE:{spec}; use a pinned command wrapper")
    # Hash the whole Python package, not only the leaf class's file.
    top = importlib.import_module(cls.__module__.split('.')[0])
    roots = sorted(Path(x).resolve() for x in getattr(top, "__path__", []))
    closure = []
    for i, root in enumerate(roots):
        closure.extend({**x, "root_index": i} for x in source_closure(root))
    if not roots: closure = [{"path": Path(path).name, "sha256": sha_file(Path(path)), "root_index": 0}]
    return {"plugin": spec, "module": cls.__module__, "class": cls.__name__,
            "source_sha256": sha_file(Path(path)), "package_source_closure": closure}
