"""CLI for local RCC evaluation, Takeshi fixture adaptation and VERITAS handoff."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bundle import create_run, verify_run
from .integrity import ContractError
from .native_veritas import invoke_run as invoke_veritas_run, prepare_run as prepare_veritas_run
from .release import preflight
from .scoring import score_run
from .takeshi import transform_file as transform_takeshi_file


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m rcc_revas_eval")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("preflight")
    s.add_argument("--manifest", type=Path, required=True)

    s = sub.add_parser("freeze-plan")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--input", type=Path, required=True)
    s.add_argument("--labels", type=Path, required=True)
    s.add_argument("--output", type=Path, required=True)

    s = sub.add_parser("evaluate")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--input", type=Path, required=True)
    s.add_argument("--output-dir", type=Path, required=True)

    s.add_argument("--plan", type=Path)

    s = sub.add_parser("verify-artifacts")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--expected-seal-sha256")

    s = sub.add_parser("score")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--labels", type=Path, required=True)
    s.add_argument("--labels-sha256", required=True)
    s.add_argument("--output-dir", type=Path, required=True)

    s = sub.add_parser("transform-takeshi")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--source", type=Path, required=True)
    s.add_argument("--output", type=Path, required=True)
    s.add_argument("--report", type=Path, required=True)
    s.add_argument("--as-of", default="2026-09-21T00:00:00Z")

    s = sub.add_parser("prepare-veritas")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--output-dir", type=Path, required=True)

    s = sub.add_parser("invoke-veritas")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--output-dir", type=Path, required=True)
    s.add_argument("--base-url", required=True)
    s.add_argument("--api-key-env", default="VERITAS_API_KEY")
    s.add_argument("--timeout", type=float, default=30.0)
    s = sub.add_parser("register-takeshi")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--source", type=Path, required=True)
    s.add_argument("--output-dir", type=Path, required=True)

    s = sub.add_parser("report-partner")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--labels", type=Path, required=True)
    s.add_argument("--native-dir", type=Path)
    s.add_argument("--output-dir", type=Path, required=True)

    s = sub.add_parser("verify-native")
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--run-dir", type=Path, required=True)
    s.add_argument("--native-dir", type=Path, required=True)
    s = sub.add_parser("inspect-native-journal")
    s.add_argument("--native-dir", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "preflight":
            pf = preflight(args.manifest)
            result = {k: v for k, v in pf.items()
                      if k not in {"policy", "keyring", "source_manifest", "manifest"}}
        elif args.command == "freeze-plan":
            from .preregistration import freeze_plan
            result = freeze_plan(args.manifest, args.input, args.labels, args.output)
        elif args.command == "evaluate":
            result = create_run(args.manifest, args.input, args.output_dir, plan_path=args.plan)
        elif args.command == "verify-artifacts":
            result = verify_run(args.manifest, args.run_dir,
                                expected_seal=args.expected_seal_sha256)
        elif args.command == "score":
            result = score_run(args.manifest, args.run_dir, args.labels,
                               args.output_dir, args.labels_sha256)
        elif args.command == "transform-takeshi":
            pf = preflight(args.manifest)
            result = transform_takeshi_file(
                args.source, args.output, args.report,
                policy=pf["policy"], keyring=pf["keyring"], as_of=args.as_of,
            )
        elif args.command == "register-takeshi":
            from .partner_review import register_partner
            result = register_partner(args.manifest, args.source, args.output_dir)
        elif args.command == "report-partner":
            from .partner_review import report_partner
            result = report_partner(args.manifest, args.run_dir, args.labels, args.output_dir, native_dir=args.native_dir)
        elif args.command == "inspect-native-journal":
            from .native_veritas import inspect_native_journal
            result = inspect_native_journal(args.native_dir)
        elif args.command == "verify-native":
            from .native_veritas import verify_native_run
            result = verify_native_run(args.manifest, args.run_dir, args.native_dir)
        elif args.command == "prepare-veritas":
            result = prepare_veritas_run(args.manifest, args.run_dir, args.output_dir)
        else:
            result = invoke_veritas_run(
                args.manifest, args.run_dir, args.output_dir,
                base_url=args.base_url, api_key_env=args.api_key_env,
                timeout=args.timeout,
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 2 if result.get("errors", 0) or result.get("execution_errors", 0) else 0
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"status": "ERROR", "code": getattr(exc, "code", type(exc).__name__),
                   "detail": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
