"""A content commitment is not external timestamping or an attestation of no exposure."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import platform
from copy import deepcopy
import sys
from .canonical import read_json, sha_file, sha_json, write_json_new
from .plugin import instantiate, plugin_identity, source_closure
from .external_identity import declared_source_identity, repository_identities
from .guardrails import require
from .readiness import assess_profile

def _test_identity(value):
    if isinstance(value, dict):
        return value.get("test_only") is True or any(_test_identity(v) for v in value.values())
    if isinstance(value, (list, tuple)): return any(_test_identity(v) for v in value)
    return isinstance(value, str) and "test-only" in value.lower()

ROLES = ("benchmark", "agent", "rcc", "veritas")


def validate_config(cfg):
    require(type(cfg) is dict, "CONFIG_NOT_OBJECT")
    for role in ROLES:
        require(type(cfg.get(role)) is dict and type(cfg[role].get("plugin")) is str, "PLUGIN_SPEC_REQUIRED", role)
    require(cfg.get("run_mode", "dual") in {"live", "fixed_replay", "dual"}, "RUN_MODE_INVALID")
    require(type(cfg.get("seed", 0)) is int, "SEED_INVALID")
    pol = cfg.get("policy", {})
    require(type(pol) is dict, "POLICY_INVALID")
    require(type(pol.get("max_steps", 32)) is int and pol.get("max_steps", 32) > 0, "MAX_STEPS_INVALID")
    require(pol.get("on_governance_stop", "terminate") in {"terminate", "feedback"}, "STOP_POLICY_INVALID")
    require(type(cfg.get("trials", 1)) is int and cfg.get("trials", 1) > 0, "TRIALS_INVALID")
    require(cfg.get("study_kind", "ENGINEERING") in {"ENGINEERING", "EXTERNAL_EXPLORATORY", "EXTERNAL_CONFIRMATORY"}, "STUDY_KIND_INVALID")
    if cfg.get("study_kind") == "EXTERNAL_CONFIRMATORY":
        for key in ("benchmark_source", "model_configuration", "native_scorer", "treatment_boundary",
                    "case_selection", "exposure_history", "isolation_profile"):
            require(bool(cfg.get("study", {}).get(key)), "CONFIRMATORY_FIELD_REQUIRED", key)
        require(cfg.get("native_profile_path"), "NATIVE_ACCEPTANCE_PROFILE_REQUIRED")
        require(cfg.get("contract_path") is not None, "CONFIRMATORY_CONTRACT_REQUIRED")
        require(bool(cfg.get("source_files")) or bool(cfg.get("source_repositories")), "EXTERNAL_SOURCE_CLOSURE_REQUIRED")
        from .benchmark_fitness import assess_benchmark_fitness
        fitness = assess_benchmark_fitness(cfg.get("benchmark_fitness"), required=True)
        require(fitness["status"] == "FITNESS_REVIEW_RECORDED", "BENCHMARK_FITNESS_NOT_ESTABLISHED")


def collect_state(config_path):
    config_path=Path(config_path).resolve()
    cfg=read_json(config_path)
    from .native_job import is_native_job, collect_native_state
    if is_native_job(cfg): return collect_native_state(config_path)
    validate_config(cfg); base=config_path.parent
    state={"config_sha256": sha_file(config_path), "config_semantic_sha256": sha_json(cfg),
           "run_mode": cfg.get("run_mode", "dual"), "policy": cfg.get("policy", {}),
           "pins_declared": cfg.get("pins", {}),
           "benchmark_fitness": cfg.get("benchmark_fitness"),
           "core_source_closure": source_closure(Path(__file__).resolve().parent),
           "declared_source_files": declared_source_identity(cfg, base),
           "source_repositories": repository_identities(cfg, base),
           "python_implementation": platform.python_implementation(),
           "python_version": list(sys.version_info[:3])}
    if cfg.get("native_profile_path"):
        report = assess_profile(base/cfg["native_profile_path"], config_path)
        if cfg.get("study_kind") == "EXTERNAL_CONFIRMATORY":
            require(report["status"] == "NATIVE_ACCEPTANCE_RECORDS_VERIFIED", "NATIVE_ACCEPTANCE_NOT_READY")
        state["native_readiness"] = report
    if cfg.get("contract_path"):
        p=base/cfg["contract_path"]
        state["contract"]={"path": cfg["contract_path"], "sha256": sha_file(p)}
    for role in ROLES:
        spec=cfg[role]; obj=instantiate(spec["plugin"], deepcopy(spec.get("config", {})), base)
        try:
            identity=obj.identity()
            require(type(identity) is dict, "PLUGIN_IDENTITY_NOT_OBJECT", role)
            state[role]={"plugin": plugin_identity(spec["plugin"]), "identity": identity,
                         "source_files": declared_source_identity(spec.get("config", {}), base)}
            if role == "benchmark":
                caps=obj.capabilities()
                require(type(caps) is dict, "BENCHMARK_CAPABILITIES_NOT_OBJECT")
                ids=obj.case_ids()
                require(type(ids) is list and bool(ids) and all(type(x) is str and bool(x) for x in ids), "CASE_IDS_INVALID")
                require(len(ids)==len(set(ids)), "DUPLICATE_CASE_ID")
                require(not (cfg.get("study_kind")=="EXTERNAL_CONFIRMATORY" and _test_identity(caps)), "TEST_BENCHMARK_IN_CONFIRMATORY_RUN")
                state[role].update(case_ids=ids, case_fingerprints={x: obj.case_fingerprint(x) for x in ids},
                                   capabilities=caps)
                require(cfg.get("run_mode", "dual") in caps.get("modes", []), "BENCHMARK_MODE_UNSUPPORTED")
                allowed=cfg.get("effects", {}).get("allowed", ["LOCAL_SIMULATION"])
                require(caps.get("effects") in allowed, "EFFECT_CLASS_NOT_AUTHORIZED")
            if cfg.get("study_kind") == "EXTERNAL_CONFIRMATORY":
                require(not _test_identity(identity), "TEST_PLUGIN_IN_CONFIRMATORY_RUN", role)
        finally:
            if hasattr(obj, "close"): obj.close()
    # Asset bytes are pinned independently; paths are relative to the config.
    state["assets"]=declared_source_identity({"source_files": cfg.get("assets", [])}, base)
    return state


def build_freeze(config_path):
    state=collect_state(config_path)
    return {"schema_version": "rveval.freeze.v2", "created_at": datetime.now(timezone.utc).isoformat(),
            "state": state, "state_sha256": sha_json(state), "execution_allowed": False,
            "source_of_authorization": "EXACT_FREEZE_HASH_ACK_AT_RUN_TIME",
            "prior_result_exposure": "NOT_ESTABLISHED_BY_THIS_FUNCTION",
            "external_timestamp_attested": False}


def freeze(config_path, output):
    value=build_freeze(config_path); write_json_new(output, value); return value


def verify_freeze(config_path, freeze_path, ack_sha):
    require(sha_file(freeze_path)==ack_sha, "FREEZE_ACK_SHA256_MISMATCH")
    frozen=read_json(freeze_path)
    require(frozen.get("schema_version")=="rveval.freeze.v2", "FREEZE_SCHEMA_UNSUPPORTED_REFREEZE_V2")
    require(sha_json(frozen["state"])==frozen["state_sha256"], "FREEZE_INTERNAL_HASH_MISMATCH")
    observed=collect_state(config_path)
    require(observed==frozen["state"], "EXECUTABLE_OR_DATA_CHANGED_AFTER_FREEZE")
    return frozen
