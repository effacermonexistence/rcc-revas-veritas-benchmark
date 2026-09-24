"""Paired execution v0.2; native outcomes and local treatment are separate estimands."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import time
import re
from . import __version__
from .canonical import sha_json, sha_file, read_json, write_json_new
from .evidence import Journal, environment_manifest, write_evidence_index
from .freeze import verify_freeze
from .guardrails import IntegrityError, UnsupportedError, assert_no_scorer_truth, require
from .models import CandidateAction, Observation, RCCDecision, VeritasDecision
from .plugin import instantiate
from .metrics import aggregate_governance, aggregate_native
from .snapshot import capture, terminal, verify_initial_pair
from .deferred import make_job


def _wire(value):
    if isinstance(value, (CandidateAction, Observation, RCCDecision, VeritasDecision)):
        return value.to_dict()
    if isinstance(value, dict): return {k: _wire(v) for k,v in value.items()}
    if isinstance(value, (tuple, list)): return [_wire(x) for x in value]
    return value


def _call_pure(fn, **kwargs):
    isolated = deepcopy(kwargs)
    before = sha_json(_wire(isolated))
    result = fn(**isolated)
    require(sha_json(_wire(isolated)) == before, "PLUGIN_MUTATED_TREATMENT_INPUT")
    return result


def _error(stage, exc, step=None):
    # No raw exception values: command stderr / provider exceptions can contain secrets.
    category = "UNSUPPORTED" if isinstance(exc, UnsupportedError) else "INTEGRITY_ERROR" if isinstance(exc, IntegrityError) else "INFRASTRUCTURE_ERROR"
    code = str(exc).split(":", 1)[0]
    if category == "INFRASTRUCTURE_ERROR" or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
        code = type(exc).__name__
    return {"stage": stage, "step": step, "type": type(exc).__name__, "category": category, "code": code}


def _context(*, case_id, step, seed, snapshot_hash, candidate, gov, task, tools):
    # arm labels, private pairing snapshots and benchmark identity/answer-bearing case
    # identifiers are excluded. case_id is an opaque runtime alias.
    result={"schema_version": "rveval.treatment-context.v2", "case_id": case_id,
            "step": step, "seed": seed, "pairing_state_sha256": snapshot_hash,
            "pre_state_sha256": snapshot_hash, "candidate": candidate.to_dict(),
            "candidate_sha256": sha_json(candidate.to_dict()), "task": deepcopy(task),
            "tools": deepcopy(tools), "governance_context": deepcopy(gov)}
    assert_no_scorer_truth(result, "treatment_context")
    return result


def _blank(arm, initial=None):
    return {"arm": arm, "initial_state": deepcopy(initial),
            "initial_state_sha256": sha_json(initial) if initial is not None else None,
            "steps": [], "native_score": None, "terminal": False,
            "termination": "NOT_STARTED", "infrastructure_errors": [], "unsupported_errors": [],
            "integrity_errors": [], "pairing_errors": []}


def _record_error(result, stage, exc, step=None):
    error=_error(stage, exc, step)
    key={"UNSUPPORTED": "unsupported_errors", "INTEGRITY_ERROR": "integrity_errors",
         "INFRASTRUCTURE_ERROR": "infrastructure_errors"}[error["category"]]
    result[key].append(error); result["termination"]=error["category"]
    return error


def _instantiate(cfg, role, base):
    spec=cfg[role]
    return instantiate(spec["plugin"], deepcopy(spec.get("config", {})), base)


def _run_arm(*, session, cfg, base, case_alias, arm, seed, initial, journal, fixture_id=None):
    result=_blank(arm, initial); result["termination"]="MAX_STEPS"
    plugins=[]; stage="INITIALIZE"
    try:
        agent=_instantiate(cfg, "agent", base); plugins.append(agent)
        rcc=_instantiate(cfg, "rcc", base); plugins.append(rcc)
        veritas=_instantiate(cfg, "veritas", base) if arm == "B" else None
        if veritas: plugins.append(veritas)
        for obj in plugins: obj.reset(case_id=case_alias, arm="paired", seed=seed)
        if agent.identity().get("test_only") and hasattr(agent, "select_fixture"):
            agent.select_fixture(fixture_id)
        history=[]; policy=cfg.get("policy", {}); stop=policy.get("on_governance_stop", "terminate")
        for i in range(policy.get("max_steps", 32)):
            stage="SNAPSHOT"
            snap = capture(session)
            if snap["terminal"]: result["termination"]="NATIVE_TERMINAL"; break
            task, tools = snap["task"], snap["tools"]
            visible, pre = snap["agent_state"], snap["pairing_state"]
            gov = snap["governance_context"]; pre_hash = sha_json(pre)
            for label,value in (("task", task), ("tools", tools), ("agent_state", visible), ("governance", gov)):
                assert_no_scorer_truth(value, label)
            stage="AGENT"
            cand=_call_pure(agent.act, task=task, history=history, state=visible, tools=tools)
            require(isinstance(cand, CandidateAction), "AGENT_RESULT_TYPE_INVALID")
            assert_no_scorer_truth(cand.to_dict(), "candidate")
            require(sha_json(session.pairing_state())==pre_hash, "ENVIRONMENT_CHANGED_DURING_PROPOSAL")
            ctx=_context(case_id=case_alias, step=i, seed=seed, snapshot_hash=pre_hash,
                         candidate=cand, gov=gov, task=task, tools=tools)
            event={"step": i, "pre_state": pre, "pre_state_sha256": pre_hash,
                   "candidate": cand.to_dict(), "candidate_sha256": sha_json(cand.to_dict()),
                   "rcc": None, "veritas": None, "executed": False,
                   "apply_attempted": False, "effect_status": "NOT_ATTEMPTED", "observation": None,
                   "treatment_context": deepcopy(ctx), "timings_ns": {}}
            result["steps"].append(event)
            journal.append("PROPOSAL_LOCKED", {"case_id": case_alias, "arm": arm, "step": i,
                                              "candidate_sha256": event["candidate_sha256"], "pre_state_sha256": pre_hash})
            stage="RCC"; started=time.perf_counter_ns()
            rd=_call_pure(rcc.review, candidate=cand, context=ctx)
            event["timings_ns"]["rcc"]=time.perf_counter_ns()-started
            require(isinstance(rd, RCCDecision), "RCC_RESULT_TYPE_INVALID")
            assert_no_scorer_truth(rd.to_dict(), "rcc_decision")
            event["rcc"]=rd.to_dict()
            if rd.disposition == "ERROR": raise RuntimeError("RCC_REPORTED_ERROR")
            if rd.disposition == "UNSUPPORTED": raise UnsupportedError("RCC_UNSUPPORTED")
            allowed=rd.disposition == "ADOPT"
            gate_name="RCC"; disposition=rd.disposition; reasons=list(rd.reason_codes)
            if allowed:
                adopted=CandidateAction(**rd.adopted_candidate.to_dict())
                event["rcc_adopted_candidate_sha256"]=sha_json(adopted.to_dict())
                vctx={**ctx, "candidate": adopted.to_dict(),
                      "candidate_sha256": sha_json(adopted.to_dict()),
                      "rcc_decision_sha256": sha_json(rd.to_dict())}
                event["veritas_context"]=deepcopy(vctx)
                if veritas:
                    stage="VERITAS"; started=time.perf_counter_ns()
                    vd=_call_pure(veritas.review, rcc_decision=rd, context=vctx)
                    event["timings_ns"]["veritas"]=time.perf_counter_ns()-started
                    require(isinstance(vd, VeritasDecision), "VERITAS_RESULT_TYPE_INVALID")
                    assert_no_scorer_truth(vd.to_dict(), "veritas_decision")
                    event["veritas"]=vd.to_dict()
                    if vd.disposition == "ERROR": raise RuntimeError("VERITAS_REPORTED_ERROR")
                    if vd.disposition == "UNSUPPORTED": raise UnsupportedError("VERITAS_UNSUPPORTED")
                    allowed=vd.disposition == "ALLOW"
                    gate_name="VERITAS"; disposition=vd.disposition; reasons=list(vd.reason_codes)
            require(sha_json(session.pairing_state()) == pre_hash, "ENVIRONMENT_CHANGED_DURING_GOVERNANCE")
            if not allowed:
                obs=Observation("governance_feedback", {"gate": gate_name, "disposition": disposition,
                                                       "reason_codes": reasons})
                event["observation"]=obs.to_dict()
                refused_candidate = rd.adopted_candidate if rd.disposition == "ADOPT" else cand
                history.append({"candidate": refused_candidate.to_dict(), "observation": obs.to_dict()})
                journal.append("GOVERNANCE_STOP", {"case_id": case_alias, "arm": arm, "step": i,
                                                  "gate": gate_name, "disposition": disposition})
                if stop == "terminate": result["termination"]="GOVERNANCE_STOP"; break
                continue
            stage="BENCHMARK_APPLY"
            # Persist intent BEFORE handing control to an effectful/sandbox operation.
            event["apply_attempted"]=True; event["effect_status"]="UNKNOWN_AFTER_ATTEMPT"
            journal.append("APPLY_INTENT", {"case_id": case_alias, "arm": arm, "step": i,
                                            "candidate": adopted.to_dict(), "pre_state_sha256": pre_hash})
            isolated=CandidateAction(**adopted.to_dict()); before=sha_json(isolated.to_dict())
            started=time.perf_counter_ns(); obs=session.apply(isolated)
            event["timings_ns"]["apply"]=time.perf_counter_ns()-started
            require(sha_json(isolated.to_dict())==before, "ADAPTER_MUTATED_CANDIDATE")
            require(isinstance(obs, Observation), "OBSERVATION_RESULT_TYPE_INVALID")
            assert_no_scorer_truth(obs.to_dict(), "agent_observation")
            event["executed"]=True; event["effect_status"]="APPLY_RETURNED_NOT_PROOF_OF_EXTERNAL_SUCCESS"
            event["observation"]=obs.to_dict(); event["post_state_sha256"]=sha_json(deepcopy(session.pairing_state()))
            history.append({"candidate": adopted.to_dict(), "observation": obs.to_dict()})
            journal.append("APPLY_RETURNED", {"case_id": case_alias, "arm": arm, "step": i,
                                              "observation": obs.to_dict(), "post_state_sha256": event["post_state_sha256"]})
            native_terminal = terminal(session)
            require(not obs.terminal or native_terminal, "OBSERVATION_TERMINAL_CONTRADICTION")
            if native_terminal: result["termination"]="NATIVE_TERMINAL"; break
        result["terminal"] = terminal(session)
    except Exception as exc:
        error=_record_error(result, stage, exc, len(result["steps"])-1)
        journal.append("ARM_ERROR", {"case_id": case_alias, "arm": arm, **error})
    finally:
        for obj in reversed(plugins):
            try: obj.close()
            except Exception as exc: _record_error(result, "PLUGIN_CLOSE", exc)
    return result


def _fixed_replay(*, arm_a, cfg, base, case_alias, seed, journal):
    events=[]; veritas=None
    try:
        veritas=_instantiate(cfg, "veritas", base)
        veritas.reset(case_id=case_alias, arm="paired", seed=seed)
        for step in arm_a["steps"]:
            raw=step.get("rcc")
            if not raw or raw["disposition"]!="ADOPT": continue
            event={"step": step["step"], "veritas": None, "infrastructure_error": None,
                   "pair_binding_verified": False}; events.append(event)
            try:
                require(sha_json(step["pre_state"])==step["pre_state_sha256"], "REPLAY_SNAPSHOT_HASH_MISMATCH")
                cand=CandidateAction(**deepcopy(raw["adopted_candidate"]))
                require(sha_json(cand.to_dict())==step["rcc_adopted_candidate_sha256"], "REPLAY_CANDIDATE_HASH_MISMATCH")
                rd=RCCDecision(raw["disposition"], cand, deepcopy(raw.get("handoff")), deepcopy(raw.get("evidence", {})), tuple(raw.get("reason_codes", [])))
                ctx=deepcopy(step["veritas_context"])
                require(ctx["rcc_decision_sha256"]==sha_json(rd.to_dict()), "REPLAY_RCC_HASH_MISMATCH")
                require(ctx["pre_state_sha256"]==step["pre_state_sha256"], "REPLAY_CONTEXT_STATE_MISMATCH")
                require(ctx["candidate_sha256"]==sha_json(cand.to_dict()), "REPLAY_CONTEXT_CANDIDATE_MISMATCH")
                # review receives exactly the same serialized context, NOT a changed
                # arm='fixed_replay' flag. Restore is a separate lifecycle operation.
                veritas.restore_replay(context=deepcopy(ctx))
                vd=_call_pure(veritas.review, rcc_decision=rd, context=ctx)
                require(isinstance(vd, VeritasDecision), "VERITAS_RESULT_TYPE_INVALID")
                assert_no_scorer_truth(vd.to_dict(), "replay_veritas")
                event.update(candidate_sha256=ctx["candidate_sha256"], pre_state_sha256=ctx["pre_state_sha256"],
                             rcc_decision_sha256=ctx["rcc_decision_sha256"], context_sha256=sha_json(ctx),
                             veritas=vd.to_dict(), pair_binding_verified=True)
                if vd.disposition=="ERROR": raise RuntimeError("VERITAS_REPORTED_ERROR")
                if vd.disposition=="UNSUPPORTED": raise UnsupportedError("VERITAS_UNSUPPORTED")
            except Exception as exc:
                event["infrastructure_error"]=_error("FIXED_REPLAY", exc, step["step"])
            journal.append("REPLAY_RECORDED", {"case_id": case_alias, **event})
    except Exception as exc:
        events.append({"step": None, "veritas": None, "infrastructure_error": _error("REPLAY_INITIALIZE", exc), "pair_binding_verified": False})
    finally:
        if veritas:
            try: veritas.close()
            except Exception as exc: events.append({"step": None, "veritas": None, "infrastructure_error": _error("REPLAY_CLOSE", exc), "pair_binding_verified": False})
    return {"mode": "FIXED_CANDIDATE_REPLAY", "events": events,
            "pairing_scope": "EXACT_SERIALIZED_CANDIDATE_AND_CONTEXT_NOT_ATTESTED_NATIVE_DATABASE",
            "native_score": "NOT_APPLICABLE_NO_ENVIRONMENT_EFFECTS_APPLIED"}


def _valid(arm):
    return bool(arm) and not any(arm.get(key) for key in
        ("infrastructure_errors", "integrity_errors", "unsupported_errors", "pairing_errors"))


def _score_jobs(jobs, journal):
    """Called only after every candidate-producing run/replay has closed."""
    for job in jobs:
        if not _valid(job.result):
            job.result["native_score_status"] = "NOT_SCORED_INVALID_EXECUTION"
            continue
        try:
            require(job.handle.fingerprint() == job.state_sha256, "SCORER_FINAL_STATE_CHANGED")
            value = job.handle.score()
            sha_json(value)
            require(type(value) is dict, "NATIVE_SCORE_NOT_OBJECT")
            require(job.handle.fingerprint() == job.state_sha256, "SCORER_MUTATED_FINAL_STATE")
            job.result["native_score"] = deepcopy(value)
            job.result["native_score_status"] = "NATIVE_SCORER_RETURNED"
            journal.append("NATIVE_SCORE_RECORDED", {
                "case_id": job.case_alias, "trial": job.trial, "arm": job.result["arm"],
                "score_sha256": sha_json(value), "final_state_sha256": job.state_sha256})
        except Exception as exc:
            _record_error(job.result, "NATIVE_SCORER", exc)
            job.result["native_score"] = None
            job.result["native_score_status"] = "SCORING_ERROR"
    # Catch a later scorer changing a previously scored arm as well.
    for job in jobs:
        try:
            require(job.handle.fingerprint() == job.state_sha256, "SCORER_FINAL_STATE_CHANGED")
        except Exception as exc:
            _record_error(job.result, "SCORING_STATE_RECHECK", exc)
            job.result["native_score"] = None
    for job in jobs:
        try: job.handle.close()
        except Exception as exc: _record_error(job.result, "SCORING_RESOURCE_CLOSE", exc)


def _pair_valid(record):
    return (record.get("pairing_valid") is True and _valid(record.get("arm_a"))
            and (record.get("arm_b") is None or _valid(record["arm_b"])))


def execute(config_path: Path, freeze_path: Path, ack_sha: str, output_dir: Path):
    config_path = Path(config_path); freeze_path = Path(freeze_path); output_dir = Path(output_dir)
    require(not output_dir.exists(), "OUTPUT_DIRECTORY_EXISTS")
    frozen = verify_freeze(config_path, freeze_path, ack_sha)
    cfg = read_json(config_path); base = config_path.resolve().parent
    mode = cfg.get("run_mode", "dual"); seed = cfg.get("seed", 0); trials = cfg.get("trials", 1)
    ids = frozen["state"]["benchmark"]["case_ids"]
    case_indices = {cid: i for i, cid in enumerate(ids)}
    planned = [(trial, cid) for trial in range(trials) for cid in ids]
    output_dir.mkdir(parents=True)
    write_json_new(output_dir / "freeze_snapshot.json", frozen)
    write_json_new(output_dir / "config_snapshot.json", cfg)
    write_json_new(output_dir / "environment_manifest.json", environment_manifest())
    journal = Journal(output_dir / "journal.jsonl")
    results, fatal, scoring_jobs = [], [], []
    adapter = None
    started = time.perf_counter_ns()
    journal.append("RUN_STARTED", {"freeze_sha256": ack_sha, "case_count": len(ids), "trials": trials})
    try:
        adapter = _instantiate(cfg, "benchmark", base)
        for trial, cid in planned:
            index = case_indices[cid]
            alias = "case:" + sha_json({"population": frozen["state"]["benchmark"]["case_fingerprints"][cid], "index": index})
            trial_seed = seed + trial
            record = {"case_id": cid, "runtime_case_id": alias, "trial": trial, "seed": trial_seed,
                      "case_fingerprint": frozen["state"]["benchmark"]["case_fingerprints"][cid],
                      "arm_a": _blank("A"), "arm_b": _blank("B") if mode in {"live", "dual"} else None,
                      "fixed_replay": None, "native_comparison": None, "pairing_valid": False}
            sessions, snapshots = {}, {}
            journal.append("CASE_STARTED", {"case_id": alias, "trial": trial})
            try:
                for arm in ("A", "B") if mode in {"live", "dual"} else ("A",):
                    sessions[arm] = adapter.open_session(cid, seed=trial_seed, arm=arm)
                    snapshots[arm] = capture(sessions[arm])
                    record["arm_" + arm.lower()] = _blank(arm, snapshots[arm]["pairing_state"])
                if "B" in sessions:
                    require(sessions["A"] is not sessions["B"], "SAME_SESSION_INSTANCE_FOR_BOTH_ARMS")
                    verify_initial_pair(snapshots["A"], snapshots["B"])
                record["pairing_valid"] = True
                for arm in ("A", "B") if "B" in sessions else ("A",):
                    # Also recheck public context, not only the private checkpoint.
                    verify_initial_pair(snapshots[arm], capture(sessions[arm]))
                    record["arm_" + arm.lower()] = _run_arm(
                        session=sessions[arm], cfg=cfg, base=base, case_alias=alias, arm=arm,
                        seed=trial_seed, initial=snapshots[arm]["pairing_state"], journal=journal, fixture_id=cid)
                if mode in {"fixed_replay", "dual"}:
                    record["fixed_replay"] = _fixed_replay(
                        arm_a=record["arm_a"], cfg=cfg, base=base,
                        case_alias=alias, seed=trial_seed, journal=journal)
            except Exception as exc:
                record["pairing_valid"] = False
                for key in ("arm_a", "arm_b"):
                    if record[key] is not None:
                        _record_error(record[key], "SESSION_OR_PAIRING", exc)
                        if isinstance(exc, IntegrityError): record[key]["pairing_errors"].append(_error("PAIRING", exc))
            finally:
                journal.append("TREATMENT_PHASE_CLOSED", {"case_id": alias, "trial": trial})
                for arm, session in sessions.items():
                    result = record["arm_" + arm.lower()]
                    if record["pairing_valid"] and _valid(result):
                        try:
                            job = make_job(session, result, alias, trial)
                            scoring_jobs.append(job)
                            result["native_score_status"] = "DEFERRED_UNTIL_COHORT_CLOSED"
                            result["scoring_storage"] = "DETACHED" if job.detached else "RETAINED_SESSION"
                            result["final_state_sha256"] = job.state_sha256
                            continue  # Ownership transferred to the scoring queue.
                        except Exception as exc: _record_error(result, "DEFER_SCORE", exc)
                    result["native_score_status"] = "NOT_SCORED_INVALID_EXECUTION"
                    try: session.close()
                    except Exception as exc: _record_error(result, "SESSION_CLOSE", exc)
            # Freeze unscored execution evidence before progressing to another task.
            write_json_new(output_dir / f"execution_case_{len(results):05d}.json", deepcopy(record))
            results.append(record)
            journal.append("CASE_EXECUTION_CLOSED", {"case_id": alias, "trial": trial,
                                                       "unscored_result_sha256": sha_json(record)})
    except Exception as exc:
        fatal.append(_error("RUN_FATAL", exc)); journal.append("RUN_FATAL", fatal[-1])
    # No score, compare or aggregate can run before this global phase transition.
    journal.append("EXECUTION_PHASE_CLOSED", {"completed_case_attempts": len(results), "enrolled": len(planned)})
    for trial, cid in planned[len(results):]:
        results.append({"case_id": cid, "trial": trial, "status": "NOT_EXECUTED_RUN_ABORTED",
                        "arm_a": None, "arm_b": None, "fixed_replay": None,
                        "native_comparison": None, "pairing_valid": False})
    _score_jobs(scoring_jobs, journal)
    for record in results:
        if record.get("arm_b") is not None:
            if _pair_valid(record):
                try:
                    value = adapter.compare_native_scores(
                        deepcopy(record["arm_a"]["native_score"]), deepcopy(record["arm_b"]["native_score"]))
                    require(type(value) is dict, "NATIVE_COMPARISON_NOT_OBJECT"); sha_json(value)
                    record["native_comparison"] = value
                except Exception as exc:
                    record["native_comparison"] = {"status": "COMPARISON_ERROR", "error": _error("COMPARE", exc)}
                    _record_error(record["arm_b"], "COMPARE", exc)
            else:
                record["native_comparison"] = {"status": "INVALID_OR_UNSUPPORTED_PAIR_NO_DELTA"}
        record["aggregation_eligible"] = _pair_valid(record)
    native = aggregate_native(results)
    eligible = [r for r in results if r["aggregation_eligible"]]
    native["aggregation_population"] = {
        "enrolled": len(planned), "eligible": len(eligible), "excluded_invalid": len(planned) - len(eligible),
        "excluded_records": [{"case_id": r["case_id"], "trial": r.get("trial", 0)}
                             for r in results if not r["aggregation_eligible"]],
        "semantics": "CONDITIONAL_ON_VALID_EXECUTION_PAIRS; ALL_ENROLLED_ATTEMPTS_RETAINED"}
    if adapter and eligible:
        try:
            value = adapter.aggregate_native_scores(deepcopy(eligible))
            require(type(value) is dict, "NATIVE_AGGREGATE_NOT_OBJECT"); sha_json(value)
            native["benchmark_owned_aggregate"] = value
        except Exception as exc:
            native["aggregate_error"] = _error("AGGREGATE", exc); fatal.append(native["aggregate_error"])
    else:
        native["benchmark_owned_aggregate"] = {"status": "NO_VALID_PAIRED_SCORES", "value": None}
    if adapter:
        try: adapter.close()
        except Exception as exc: fatal.append(_error("ADAPTER_CLOSE", exc))
    for index, record in enumerate(results):
        write_json_new(output_dir / f"case_{index:05d}.json", record)
        journal.append("CASE_CLOSED", {"case_id": record["case_id"], "trial": record.get("trial", 0),
                                        "result_sha256": sha_json(record)})
    write_json_new(output_dir / "governance_metrics.json", aggregate_governance(results))
    write_json_new(output_dir / "native_metrics.json", native)
    invalid = bool(fatal) or any(not _pair_valid(r) or
        any(e.get("infrastructure_error") for e in (r.get("fixed_replay") or {}).get("events", [])) for r in results)
    manifest = {
        "schema_version": "rveval.run-manifest.v2", "framework_version": __version__,
        "status": "COMPLETED_WITH_ERRORS_OR_UNSUPPORTED" if invalid else "COMPLETED",
        "run_mode": mode, "freeze_sha256": ack_sha, "config_sha256": sha_file(config_path),
        "case_count": len(results), "unique_cases": len(ids), "trials": trials, "enrolled": len(planned),
        "fatal_errors": fatal, "elapsed_ns": time.perf_counter_ns() - started,
        "score_phase": "AFTER_ALL_CASES_TRIALS_AND_REPLAYS",
        "automatic_retries": 0, "automatic_retries_scope": "RVEVAL_ORCHESTRATOR_ONLY_NATIVE_INTERNAL_RETRIES_REQUIRE_TELEMETRY",
        "silent_denominator_reduction": False, "native_aggregation_eligible": len(eligible),
        "study_kind": cfg.get("study_kind", "ENGINEERING"), "all_benchmarks_validated": False,
        "native_rcc_veritas_integration_attested": False, "independent_validation_attested": False,
        "prior_result_exposure": "NOT_INFERRED_FROM_FREEZE",
        "live_claim_scope": "NATIVE_SCORES_ONLY_WHEN_ADAPTER_IMPLEMENTS_NATIVE_SCORER",
        "fixed_replay_claim_scope": "LOCAL_GATE_ON_EXACT_SERIALIZED_CANDIDATE_CONTEXT_NOT_WHOLE_TASK",
        "isolation": "TRUSTED_PLUGINS_REQUIRE_EXTERNAL_OS_SANDBOX_FOR_UNTRUSTED_CODE",
        "telemetry": {"model_calls": None, "provider_tokens": None, "provider_cost": None, "status": "NOT_MEASURED_BY_CORE"}}
    write_json_new(output_dir / "run_manifest.json", manifest)
    journal.append("RUN_CLOSED", {"status": manifest["status"], "manifest_sha256": sha_file(output_dir / "run_manifest.json")})
    journal.close(); write_evidence_index(output_dir)
    return manifest
