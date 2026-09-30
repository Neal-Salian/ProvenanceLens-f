"""Run the benchmark across systems and assemble reports (offline, deterministic)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .. import __version__
from .baselines import BASELINE_NAMES, run_baseline
from .calibration import calibration_status
from .dataset import benchmark_summary, load_benchmark
from .extraction_eval import default_fixtures, evaluate_fixtures
from .metrics import compute_metrics
from .runner import run_case
from .schema import BENCHMARK_VERSION, BenchmarkRun, CaseResult, Track
from .selective import selective_sweep

__all__ = [
    "DEFAULT_SYSTEMS",
    "run_benchmark",
    "run_system",
    "write_artifacts",
    "artifacts_to_json",
    "selective_csv",
]

#: Systems evaluated by default: the production engine plus every baseline.
DEFAULT_SYSTEMS: tuple[str, ...] = ("provenancelens",) + BASELINE_NAMES


def run_system(
    system: str, cases: list, *, snapshot_root: Path | None = None
) -> list[CaseResult]:
    """Evaluate one named system over the benchmark."""
    if system == "provenancelens":
        return [run_case(case, system=system) for case in cases]
    if system in BASELINE_NAMES:
        return [run_baseline(system, case) for case in cases]
    raise ValueError(
        f"unknown system {system!r}; expected one of {DEFAULT_SYSTEMS} or a registered "
        "optional baseline"
    )


def run_benchmark(
    *,
    track: Track | str | None = None,
    systems: tuple[str, ...] = DEFAULT_SYSTEMS,
    root: Path | None = None,
    validate: bool = True,
    include_extraction: bool = True,
) -> dict[str, BenchmarkRun]:
    """Run every requested system and compute metrics, selective sweeps, etc."""
    track = Track(track) if isinstance(track, str) else track
    cases = load_benchmark(track, root=root, validate=validate)
    summary = benchmark_summary(cases)

    runs: dict[str, BenchmarkRun] = {}
    for system in systems:
        results = run_system(system, cases, snapshot_root=root)
        metrics = compute_metrics(results, system=system)
        sweep = selective_sweep(results)
        metrics["selective"] = [point.model_dump(mode="json") for point in sweep]
        metrics["calibration"] = calibration_status(results).model_dump(mode="json")
        runs[system] = BenchmarkRun(
            benchmark_version=BENCHMARK_VERSION,
            system=system,
            suite=track.value if track is not None else "all",
            cases=tuple(results),
            metrics=metrics,
            extraction=(
                evaluate_fixtures(default_fixtures()).model_dump(mode="json")
                if include_extraction else None
            ),
            provenance={
                "package_version": __version__,
                "benchmark_summary": summary,
                "llm_used": "false (deterministic fixtures only)",
            },
        )
    return runs


def selective_csv(runs: dict[str, BenchmarkRun]) -> str:
    """Selective-prediction sweep as CSV (one row per system and threshold)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "system", "threshold", "n_scored", "accepted", "coverage",
        "selective_accuracy", "correct", "attempted_repairs", "false_repairs",
        "false_repair_rate", "abstentions", "abstention_rate",
    ])
    for system, run in runs.items():
        for point in run.metrics.get("selective", []):
            writer.writerow([
                system, point["threshold"], point["n_scored"], point["accepted"],
                point["coverage"], point["selective_accuracy"], point["correct"],
                point["attempted_repairs"], point["false_repairs"],
                point["false_repair_rate"], point["abstentions"], point["abstention_rate"],
            ])
    return buffer.getvalue()


def results_csv(run: BenchmarkRun) -> str:
    """Per-case results as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "case_id", "track", "expected_action", "predicted_action", "action_correct",
        "expected_parents", "predicted_parents", "expected_relation",
        "predicted_relation", "support_score", "abstained", "repair_attempted",
        "false_repair", "n_conflicts",
    ])
    for case in run.cases:
        writer.writerow([
            case.case_id, case.track.value, case.expected_action.value,
            case.predicted_action.value, case.action_correct,
            "|".join(case.expected_parents or ()), "|".join(case.predicted_parents),
            case.expected_relation.value if case.expected_relation else None,
            case.predicted_relation.value if case.predicted_relation else None,
            case.support_score, case.abstained, case.repair_attempted,
            case.false_repair, len(case.conflicts),
        ])
    return buffer.getvalue()


def artifacts_to_json(runs: dict[str, BenchmarkRun]) -> dict:
    """Everything needed to regenerate the report, in one JSON-ready mapping."""
    return {
        system: run.model_dump(mode="json") for system, run in runs.items()
    }


def write_artifacts(
    runs: dict[str, BenchmarkRun], output_dir: Path | None = None
) -> dict[str, Path]:
    """Write JSON/CSV artifacts. Generated output is never committed."""
    from .schema import Track as _Track  # local import keeps the API surface small

    base = Path(output_dir or "artifacts/evaluation")
    base.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for track in ("controlled", "real", "all"):
        track_runs = {
            system: BenchmarkRun(
                benchmark_version=run.benchmark_version,
                system=run.system,
                suite=track,
                cases=tuple(
                    case for case in run.cases
                    if track == "all" or case.track is _Track(track)
                ),
                metrics=run.metrics,
                extraction=run.extraction,
                provenance=run.provenance,
            )
            for system, run in runs.items()
        }
        path = base / f"{track}_results.json"
        path.write_text(
            json.dumps(
                {system: run.model_dump(mode="json")
                 for system, run in track_runs.items()},
                indent=2, ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
        written[track] = path

    metrics_path = base / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {system: run.metrics for system, run in runs.items()}, indent=2
        ) + "\n",
        encoding="utf-8",
    )
    written["metrics"] = metrics_path

    selective_path = base / "selective_metrics.csv"
    selective_path.write_text(selective_csv(runs), encoding="utf-8")
    written["selective"] = selective_path

    baseline_path = base / "baseline_metrics.json"
    baseline_path.write_text(
        json.dumps(
            {
                system: {
                    "action_accuracy": run.metrics["action"]["accuracy"]["value"],
                    "parent_accuracy": run.metrics["parent"]["value"],
                    "false_repair_rate": run.metrics["repair_safety"]["false_repairs"]["value"],
                    "coverage": next(
                        point["coverage"] for point in run.metrics["selective"]
                        if point["threshold"] == 0.0
                    ),
                    "abstention_rate": run.metrics["repair_safety"]["abstentions"]["value"],
                }
                for system, run in runs.items()
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    written["baselines"] = baseline_path

    for system, run in runs.items():
        case_path = base / f"{system}_cases.csv"
        case_path.write_text(results_csv(run), encoding="utf-8")
        written[f"cases:{system}"] = case_path
    return written
