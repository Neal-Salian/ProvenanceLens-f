"""Phase G command line: ``python -m provenancelens.evaluation.phase_g``.

Subcommands
-----------

``run``       run the whole study and write every artifact (default)
``summary``   print the headline table without writing anything
``ablate``    run only the ablation suite
``failures``  print the failure taxonomy and every failure
``verify``    re-run and compare the report digest for reproducibility
``publish``    write the canonical, version-controlled result set
``verify-canonical``  re-check the committed canonical results
``llm-compare`` optional local open-weight LLM comparator (never runs by default)

All subcommands are offline and deterministic.  ``run`` records the
environment, configuration, input and output digests in ``manifest.json``;
``verify`` exists so a reviewer can confirm reproducibility with one command.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .. import __version__
from .dataset import load_benchmark
from .phase_g import run_phase_g
from .real import adjudication_summary
from .report import build_manifest, report_digest, render_markdown_table, write_phase_g_report
from .schema import Track

__all__ = ["main", "build_parser"]

_DEFAULT_OUTPUT = Path("artifacts/phase_g")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m provenancelens.evaluation.phase_g",
        description="Phase G experimental study (offline, deterministic).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--root", type=Path, default=None,
        help="frozen snapshot root (default: the repository's data/snapshots)",
    )
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run the study and write all artifacts")
    run.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT,
                     help="artifact directory (default: artifacts/phase_g)")
    run.add_argument("--track", choices=[t.value for t in Track], default=None,
                     help="restrict to one track (default: both)")
    run.add_argument("--no-ablations", action="store_true",
                     help="skip the ablation suite")
    run.add_argument("--no-plots", action="store_true",
                     help="skip figures (all tables, the JSON report and the "
                          "manifest are still written)")
    run.add_argument("--quiet", action="store_true", help="only print the digest")

    sub.add_parser("summary", help="print headline metrics only")

    ablate = sub.add_parser("ablate", help="run only the ablation suite")
    ablate.add_argument("--track", choices=[t.value for t in Track], default=None)

    sub.add_parser("failures", help="print the failure taxonomy and failures")

    verify = sub.add_parser("verify", help="re-run twice and compare report digests")
    verify.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)

    publish = sub.add_parser(
        "publish",
        help="write the canonical, version-controlled result set (results/phase_g)",
        description="Regenerate results/phase_g - the committed evidence for the "
                    "research claims - from a fresh offline study run.",
    )
    publish.add_argument("--canonical", type=Path, default=Path("results/phase_g"),
                         help="canonical output directory (default: results/phase_g)")
    publish.add_argument("--output", type=Path, default=None,
                         help="also write the full study artifacts here")
    publish.add_argument("--no-plots", action="store_true",
                         help="skip figures (all tables, results.json, RESULTS.md and "
                              "the manifest are still written)")
    publish.add_argument("--quiet", action="store_true", help="print only the digest")

    verify_canonical = sub.add_parser(
        "verify-canonical",
        help="verify the committed canonical results against their manifest",
    )
    verify_canonical.add_argument("--canonical", type=Path,
                                  default=Path("results/phase_g"))

    compare = sub.add_parser(
        "llm-compare",
        help="optional local open-weight LLM comparator (opt-in, local only)",
    )
    compare.add_argument("--model", default="llama3.2:3b",
                         help="an already-installed local model (never downloaded)")
    compare.add_argument("--output", type=Path, default=Path("artifacts/phase_g/llm"))
    compare.add_argument("--dry-run", action="store_true",
                         help="list the selected cases without calling any model")
    return parser


def _snapshot_root(root: Path | None) -> Path:
    return Path(root) if root else Path("data/snapshots")


def _study_config(args: argparse.Namespace, *, plot_requested: bool) -> dict:
    """Experiment configuration recorded in a manifest.

    Deliberately free of absolute paths, timings and machine details so the
    canonical manifest is byte-identical everywhere.
    """
    return {
        "track": getattr(args, "track", None) or "all",
        "ablations": not getattr(args, "no_ablations", False),
        "plots": plot_requested,
        "systems": "provenancelens + 6 baselines",
        "snapshot_root": "data/snapshots",
        "adjudication_file": "evaluation/adjudication/real_cases.yaml",
        "network": False,
        "llm": False,
    }


def _print_headline(report: dict, track: str | None = None) -> None:
    key = "headline" if track is None else f"headline_{track}"
    rows = [{**row, "ci95": (row.get("ci95") or {}).get("low")} for row in
            report["systems"]["provenancelens"][key]]
    for row in rows:
        ci = row.pop("ci95")
        row["ci95"] = row.get("ci95")
    sys.stdout.write(render_markdown_table(
        [{**row, "ci95": None} for row in rows],
        ["metric", "numerator", "denominator", "value"],
    ))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "run"
    root = args.root

    if command == "summary":
        report = run_phase_g(root=root, include_ablations=False, include_extraction=False)
        _print_headline(report)
        return 0

    if command == "ablate":
        report = run_phase_g(track=args.track, root=root, include_extraction=False)
        rows = report["ablations"]["results"]
        sys.stdout.write(render_markdown_table(
            rows, ["ablation", "action_accuracy", "delta_action_accuracy",
                   "coverage", "attempted_repairs", "false_repairs", "verdict"]))
        return 0

    if command == "failures":
        report = run_phase_g(root=root, include_ablations=False, include_extraction=False)
        analysis = report["failure_analysis"]
        sys.stdout.write(render_markdown_table(
            analysis["taxonomy"], ["category", "n_cases", "description"]))
        sys.stdout.write(render_markdown_table(
            [{**row, "conflicts": "|".join(row["conflicts"])} for row in analysis["failures"]],
            ["case_id", "category", "expected_action", "predicted_action",
             "support_score", "reasoning_summary"]))
        return 0

    if command == "publish":
        from .canonical import verify_canonical_results, write_canonical_results

        config = _study_config(args, plot_requested=not args.no_plots)
        report = run_phase_g(root=root, include_ablations=True,
                             include_extraction=False)
        artifacts = write_canonical_results(
            report, Path(args.canonical), snapshot_root=_snapshot_root(root),
            config=config, adjudication_rows=adjudication_summary(root=root),
            plots=not args.no_plots,
        )
        verification = verify_canonical_results(Path(args.canonical))
        if args.output:
            write_phase_g_report(
                report, Path(args.output), manifest=build_manifest(
                    report, artifacts={}, snapshot_root=_snapshot_root(root),
                    elapsed_seconds=0.0, config=config),
                snapshot_root=_snapshot_root(root), config=config,
                adjudication_rows=adjudication_summary(root=root),
                plots=not args.no_plots,
            )
        digest = report_digest(report)
        if args.quiet:
            print(digest)
            return 0 if verification["ok"] else 1
        print(json.dumps({
            "report_digest": digest,
            "canonical": str(args.canonical),
            "n_files": len(artifacts),
            "verified": verification["ok"],
            "problems": verification["problems"],
        }, indent=1))
        return 0 if verification["ok"] else 1

    if command == "verify-canonical":
        from .canonical import verify_canonical_results

        verification = verify_canonical_results(Path(args.canonical))
        print(json.dumps(verification, indent=1))
        return 0 if verification["ok"] else 1

    if command == "llm-compare":
        from .llm_comparator import (
            LLMComparatorUnavailable,
            llm_comparator_targets,
            run_local_llm_comparator,
            write_comparator_report,
        )

        if args.dry_run:
            targets = llm_comparator_targets(load_benchmark("real", root=root))
            sys.stdout.write(json.dumps(
                {"would_run": [case.case_id for case in targets],
                 "n_cases": len(targets)}, indent=1) + "\n")
            return 0
        try:
            payload = run_local_llm_comparator(load_benchmark("real", root=root),
                                               model=args.model)
        except LLMComparatorUnavailable as exc:
            sys.stdout.write(json.dumps(
                {"status": "skipped", "reason": str(exc)}, indent=1) + "\n")
            return 3
        path = write_comparator_report(payload, args.output)
        sys.stdout.write(json.dumps(
            {"status": "ran", "model": payload["model"], "artifact": str(path),
             "summary": payload["summary"]}, indent=1, default=str) + "\n")
        return 0

    if command == "verify":
        first = report_digest(run_phase_g(include_extraction=False))
        second = report_digest(run_phase_g(include_extraction=False))
        payload = {"first_digest": first, "second_digest": second,
                   "identical": first == second}
        sys.stdout.write(json.dumps(payload, indent=1) + "\n")
        return 0 if first == second else 1

    # run
    config = _study_config(args, plot_requested=not args.no_plots)
    started = time.perf_counter()
    report = run_phase_g(track=args.track, root=root,
                         include_ablations=not args.no_ablations,
                         include_extraction=False)
    elapsed = time.perf_counter() - started
    snapshot_root = Path(root) if root else Path("data/snapshots")
    manifest = build_manifest(report, artifacts={}, snapshot_root=snapshot_root,
                              elapsed_seconds=elapsed, config=config)
    # One writer for every case: --no-plots still produces the JSON report, the
    # markdown summary, all tables, the adjudication CSV and the manifest.
    artifacts = write_phase_g_report(
        report, Path(args.output), manifest=manifest, snapshot_root=snapshot_root,
        config=config, adjudication_rows=adjudication_summary(root=root),
        plots=not args.no_plots,
    )
    digest = report_digest(report)
    if args.quiet:
        print(digest)
        return 0
    print(json.dumps({
        "report_digest": digest,
        "output": str(args.output),
        "n_artifacts": len(artifacts),
        "n_cases": report["benchmark"]["n_cases"],
        "elapsed_seconds": round(elapsed, 3),
        "headline": {
            row["metric"]: row["value"]
            for row in report["systems"]["provenancelens"]["headline"]
        },
    }, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
