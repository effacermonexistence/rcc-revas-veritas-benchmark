"""Pinned dependency closure and explicit release readiness states."""
from __future__ import annotations
import platform
import sys
from pathlib import Path
from . import __version__
from .integrity import text, read_json, raw_sha, require, safe_path, digest, exact_keys, strings

ROOT = Path(__file__).resolve().parent.parent


def runtime_paths(root: Path) -> set[str]:
    selected = set()
    for folder, glob in (("rcc_revas_eval", "*.py"), ("schemas", "*.json"), ("policies", "*.json")):
        for p in (root / folder).glob(glob):
            selected.add(p.relative_to(root).as_posix())
    selected.update({"pyproject.toml", "evaluation_manifest.json"})
    return selected


def preflight(manifest_path: Path) -> dict:
    require(sys.version_info >= (3, 11), "PYTHON_3_11_REQUIRED")
    manifest_path = manifest_path.absolute()
    root = manifest_path.parent
    manifest = read_json(manifest_path)
    exact_keys(manifest, {"schema_version", "release_candidate", "source_manifest", "policy", "keyring", "execution_scope", "veritas"}, where="manifest")
    require(manifest["schema_version"] == "rcc-revas.evaluation-manifest.v1", "MANIFEST_SCHEMA_INVALID")
    require(manifest["execution_scope"] == "SYNTHETIC_STRUCTURED_SUBSET_NO_EXTERNAL_EFFECTS", "EXECUTION_SCOPE_UNSUPPORTED")
    sm_path = safe_path(root, manifest["source_manifest"])
    sm = read_json(sm_path)
    require(sm["schema_version"] == "rcc-revas.source-manifest.v1", "SOURCE_MANIFEST_SCHEMA_INVALID")
    entries = sm["files"]
    require(type(entries) is list, "SOURCE_MANIFEST_ENTRIES_INVALID")
    paths = [e["path"] for e in entries]
    require(len(paths) == len(set(paths)), "DUPLICATE_SOURCE_PATH")
    require(set(paths) == runtime_paths(root), "SOURCE_CLOSURE_MISMATCH")
    for entry in entries:
        path = safe_path(root, entry["path"])
        require(path.is_file(), "SOURCE_FILE_MISSING", entry["path"])
        data = path.read_bytes()
        require(raw_sha(data) == entry["sha256"] and len(data) == entry["size_bytes"], "SOURCE_HASH_MISMATCH", entry["path"])
        if entry["path"].startswith("rcc_revas_eval/"):
            loaded_path = safe_path(Path(__file__).resolve().parent, entry["path"].split("/", 1)[1])
            require(loaded_path.is_file() and raw_sha(loaded_path.read_bytes()) == entry["sha256"],
                    "LOADED_SOURCE_HASH_MISMATCH", entry["path"])
    policy = read_json(safe_path(root, manifest["policy"]))
    keyring = read_json(safe_path(root, manifest["keyring"]))
    exact_keys(policy, {"policy_id", "version", "synthetic_only", "supported_kinds", "protected_action_profiles", "allowed_uses"}, where="policy")
    require(policy["synthetic_only"] is True, "REVIEW_RELEASE_MUST_BE_SYNTHETIC_ONLY")
    strings(policy["supported_kinds"], "supported_kinds", True)
    require(set(policy["supported_kinds"]) == {"factual_claim", "bounded_inference", "candidate_replacement", "protected_action"}, "POLICY_KINDS_INVALID")
    require(type(policy["protected_action_profiles"]) is dict, "ACTION_PROFILES_INVALID")
    for requirements in policy["protected_action_profiles"].values():
        strings(requirements, "action_requirements", True)
    require(set(policy["allowed_uses"]) == set(policy["supported_kinds"]), "ALLOWED_USE_MAPPING_INVALID")
    for uses in policy["allowed_uses"].values():
        strings(uses, "allowed_uses", True)
    require(type(keyring) is dict and bool(keyring), "KEYRING_INVALID")
    for issuer, record in keyring.items():
        text(issuer, "keyring.issuer")
        exact_keys(record, {"key_hex", "synthetic", "allowed_observation_prefixes"}, where="keyring." + issuer)
        require(record["synthetic"] is True, "NON_SYNTHETIC_KEY_FORBIDDEN_IN_REVIEW_RELEASE")
        try:
            key = bytes.fromhex(record["key_hex"])
        except (ValueError, TypeError) as exc:
            from .integrity import ContractError
            raise ContractError("INVALID_FIXTURE_KEY") from exc
        require(len(key) >= 32, "FIXTURE_KEY_TOO_SHORT")
        strings(record["allowed_observation_prefixes"], "issuer_prefixes", True)
    identity = {"package": "rcc-revas-eval", "version": __version__,
                "source_manifest_sha256": raw_sha(sm_path.read_bytes()),
                "evaluation_manifest_sha256": raw_sha(manifest_path.read_bytes()),
                "policy_hash": digest(policy, "rcc-policy-v1"),
                "keyring_hash": digest(keyring, "rcc-keyring-v1"),
                "adapter_source_sha256": raw_sha((root / "rcc_revas_eval/handoff.py").read_bytes())}
    return {"status": "PASS", "source_identity": identity, "policy": policy, "keyring": keyring,
            "manifest": manifest, "source_manifest": sm,
            "environment": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                            "system": platform.system(), "machine": platform.machine(),
                            "runtime_dependencies": "Python standard library only"},
            "readiness": {"RCC_local_entrypoint_preflight": True,
                          "Takeshi_36_case_adapter_implemented": True,
                          "VERITAS_native_call_path_implemented": True,
                          "VERITAS_native_execution_observed": False,
                          "VERITAS_server_candidate_consumption_verified": False,
                          "joint_runtime_frozen": False,
                          "production_parity_claimed": False}}
