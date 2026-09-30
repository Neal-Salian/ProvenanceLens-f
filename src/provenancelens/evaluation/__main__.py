"""Command line entry point: ``python -m provenancelens.evaluation``.

Offline and deterministic by default. Examples::

    python -m provenancelens.evaluation validate
    python -m provenancelens.evaluation run --track controlled
    python -m provenancelens.evaluation run --track real --systems provenancelens
    python -m provenancelens.evaluation all --output artifacts/evaluation
    python -m provenancelens.evaluation extraction
    python -m provenancelens.evaluation phase-g run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import benchmark_summary, load_benchmark, validation_report
from .extraction_eval import default_fixtures, evaluate_fixtures
from .run import DEFAULT_SYSTEMS, run_benchmark, write_artifacts
from .schema import Track


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def _cmd_validate(args: argparse.Namespace) -> int:
    cases = load_benchmark(args.track, root=args.root, validate=False)
    issues = validation_report(cases)
    errors = [i for i in issues if i.severity.value == "error"]
    _print({
        "summary": benchmark_summary(cases),
        "errors": [i.model_dump(mode="json") for i in errors],
        "warnings": [i.model_dump(mode="json") for i in issues if i.severity.value == "warning"],
    })
    return 1 if errors else 0


def _cmd_run(args: argparse.Namespace) -> int:
    systems = tuple(args.systems) if args.systems else DEFAULT_SYSTEMS
    runs = run_benchmark(
        track=args.track, systems=systems, root=args.root,
        include_extraction=not args.no_extraction,
    )
    if args.output:
        written = write_artifacts(runs, Path(args.output))
        _print({"artifacts": {k: str(v) for k, v in written.items()}})
    else:
        _print({system: run.metrics for system, run in runs.items()})
    return 0


def _cmd_phase_g(args: argparse.Namespace) -> int:
    """Forward to the Phase G study CLI (see provenancelens.evaluation.phase_g_cli)."""
    from .phase_g_cli import main as phase_g_main

    forwarded = list(args.phase_g or [])
    if args.root:
        forwarded += ["--root", args.root]
    return phase_g_main(forwarded)


def _cmd_extraction(args: argparse.Namespace) -> int:
    metrics = evaluate_fixtures(default_fixtures())
    _print(metrics.model_dump(mode="json"))
    return 0


def _cmd_all(args: argparse.Namespace) -> int:
    status = _cmd_validate(args)
    runs = run_benchmark(root=args.root, include_extraction=True)
    written = write_artifacts(runs, Path(args.output))
    _print({
        "artifacts": {k: str(v) for k, v in written.items()},
        "summary": {system: {
            "action_accuracy": run.metrics["action"]["accuracy"]["value"],
            "false_repair_rate": run.metrics["repair_safety"]["false_repairs"]["value"],
        } for system, run in runs.items()},
    })
    return status


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--track", choices=[t.value for t in Track], default=None,
        help="benchmark track (default: both)",
    )
    common.add_argument(
        "--root", default=None,
        help="frozen snapshot root (default: the repository's data/snapshots)",
    )

    parser = argparse.ArgumentParser(
        prog="python -m provenancelens.evaluation",
        description="LineageRepairBench evaluation (offline, deterministic).",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("validate", parents=[common],
                   help="validate the benchmark and print its summary").set_defaults(
        func=_cmd_validate
    )

    run = sub.add_parser("run", parents=[common],
                         help="evaluate systems against the benchmark")
    run.add_argument("--systems", nargs="*", default=None,
                     help=f"systems to evaluate (default: {' '.join(DEFAULT_SYSTEMS)})")
    run.add_argument("--output", default=None, help="directory for JSON/CSV artifacts")
    run.add_argument("--no-extraction", action="store_true",
                     help="skip the prose-extraction metrics")
    run.set_defaults(func=_cmd_run)

    sub.add_parser("extraction", parents=[common],
                   help="evaluate prose-extraction quality only").set_defaults(
        func=_cmd_extraction)

    phase_g = sub.add_parser("phase-g", parents=[common],
                             help="run the Phase G experimental study")
    phase_g.add_argument("phase_g", nargs="*",
                         help="arguments forwarded to the Phase G CLI "
                              "(run, summary, ablate, failures, verify)")
    phase_g.set_defaults(func=_cmd_phase_g)

    every = sub.add_parser("all", parents=[common],
                           help="validate, run every system and write artifacts")
    every.add_argument("--output", default="artifacts/evaluation")
    every.set_defaults(func=_cmd_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
