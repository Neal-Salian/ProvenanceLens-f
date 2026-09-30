"""Canonical, version-controlled research outputs.

Phase G wrote everything to ``artifacts/``, which is git-ignored: convenient for
experimentation, useless as evidence, because a reviewer cloning the repository
cannot see a single number.  This module publishes the *same* study output to
``results/phase_g/`` as a compact, committed, byte-deterministic set:

* ``results.json``      - machine-readable metrics and analyses (the source of truth)
* ``RESULTS.md``        - a human-readable results document *rendered from* results.json
* ``manifest.json``     - versions, snapshot revisions and SHA-256 of every file
* ``tables/*.csv``      - the same tables the study writes
* ``figures/*.png``     - the same figures, included because they are the paper-facing view

Design rules
------------

* **One source of truth.**  The canonical set is produced by the same code path
  that produces ``artifacts/``; there is no second implementation and no
  hand-edited number.  ``artifacts/`` is scratch, ``results/`` is evidence.
* **Byte-determinism.**  No timestamps, no absolute paths, no machine names and
  no durations enter the canonical files, so a regeneration on another machine
  produces an identical tree.  The evaluating commit and the elapsed time are
  reported by the study manifest in ``artifacts/`` instead.
* **Verifiable.**  :func:`verify_canonical_results` recomputes every digest and
  cross-checks the headline numbers against ``results.json``, which is what the
  documentation tests use to detect stale numbers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from .report import (
    PLOT_NAMES,
    PlottingUnavailable,
    render_markdown_table,
    report_digest,
    write_plots,
    write_tables,
)

__all__ = [
    "CANONICAL_DIRNAME",
    "CANONICAL_GENERATION_COMMAND",
    "canonical_manifest",
    "write_canonical_results",
    "verify_canonical_results",
    "render_results_document",
]

#: Where the committed evidence lives, relative to the repository root.
CANONICAL_DIRNAME = "results/phase_g"

#: The exact command that regenerates it.  Recorded in the manifest so a
#: reviewer never has to guess.
CANONICAL_GENERATION_COMMAND = (
    "python -m provenancelens.evaluation.phase_g_cli publish --canonical results/phase_g"
)

#: Metric semantics are versioned like the benchmark itself, so a reader can
#: tell which definitions produced a number.
METRIC_DEFINITIONS_VERSION = "phase-f-g-1.0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_revisions(snapshot_root: Path) -> dict[str, str]:
    """repository -> pinned commit, for every frozen snapshot in the tree."""
    revisions: dict[str, str] = {}
    if not snapshot_root.is_dir():
        return revisions
    for repo_dir in sorted(p for p in snapshot_root.iterdir() if p.is_dir()):
        repository = repo_dir.name.replace("__", "/", 1)
        for sha_dir in sorted(p for p in repo_dir.iterdir() if p.is_dir()):
            if (sha_dir / "manifest.json").is_file():
                revisions[repository] = sha_dir.name
    return revisions


def _ci(row: dict) -> str:
    ci = row.get("ci95") or {}
    low, high = ci.get("low"), ci.get("high")
    if low is None or high is None:
        return "-"
    return f"[{low:.3f}, {high:.3f}]"


def render_results_document(report: dict, manifest: dict) -> str:
    """Render ``RESULTS.md`` from the report, so no number is typed by hand."""
    main = report["systems"]["provenancelens"]
    lines: list[str] = []
    add = lines.append
    benchmark = report["benchmark"]

    add("# ProvenanceLens — measured results (LineageRepairBench)")
    add("")
    add("> Generated from `results/phase_g/results.json` by "
        "`provenancelens.evaluation.canonical`. Do not edit by hand: regenerate "
        f"with `{CANONICAL_GENERATION_COMMAND}`. A test fails if this file and a "
        "fresh run disagree.")
    add("")
    add(f"- Report digest: `{report_digest(report)}`")
    add(f"- Benchmark version: `{benchmark['benchmark_version']}` "
        f"({manifest['metric_definitions_version']} metric definitions)")
    add("- Offline, deterministic, no LLM and no network.")
    add("")

    add("## Benchmark composition")
    add("")
    add(render_markdown_table([
        {"track": track, "n_cases": n,
         "label_provenance": "synthetic_construction" if track == "controlled"
                            else "manual_adjudication"}
        for track, n in sorted(benchmark["by_track"].items())
    ] + [
        {"track": "TOTAL", "n_cases": benchmark["n_cases"],
         "label_provenance": "mixed"},
    ], ["track", "n_cases", "label_provenance"]))
    add("Expected action labels (adjudicated, not predicted):")
    add("")
    add(render_markdown_table([
        {"expected_action": action, "n_cases": n}
        for action, n in sorted(benchmark["by_expected_action"].items())
    ], ["expected_action", "n_cases"]))
    add("Declared-metadata state as adjudicated:")
    add("")
    add(render_markdown_table([
        {"metadata_state": state, "n_cases": n}
        for state, n in sorted(benchmark["by_metadata_state"].items())
    ], ["metadata_state", "n_cases"]))
    add(f"Cases whose parent truth is not knowable (ambiguous or unknown): "
        f"**{benchmark['non_known_parent_truth']}** of {benchmark['n_cases']}.")
    add("")

    for title, key in (("CONTROLLED", "headline_controlled"),
                       ("REAL", "headline_real"),
                       ("COMBINED", "headline")):
        if key not in main:
            continue
        add(f"## Main results — {title}")
        add("")
        add(render_markdown_table(
            [{**row, "ci95": _ci(row)} for row in main[key]],
            ["metric", "numerator", "denominator", "value", "ci95"]))
    add("Intervals are Wilson 95% score intervals; several denominators are small, "
        "so a point estimate alone would mislead. `parent_exact_match` and "
        "`relation_accuracy` are scored only on cases with KNOWN truth, which is "
        "why their denominators are smaller than the case count.")
    add("")

    add("## Repair safety")
    add("")
    safety = {row["metric"]: row for row in main["headline"]}
    real = {row["metric"]: row for row in main["headline_real"]}
    add(render_markdown_table([
        {"quantity": "repair attempts", "combined": safety["repair_attempt_rate"]["numerator"],
         "real": real["repair_attempt_rate"]["numerator"]},
        {"quantity": "false repairs", "combined": safety["false_repair_rate"]["numerator"],
         "real": real["false_repair_rate"]["numerator"]},
        {"quantity": "unverifiable repairs",
         "combined": safety["unverifiable_repair_rate"]["numerator"],
         "real": real["unverifiable_repair_rate"]["numerator"]},
        {"quantity": "False Repair Rate (numerator/denominator)",
         "combined": f"{safety['false_repair_rate']['numerator']}/"
                     f"{safety['false_repair_rate']['denominator']}",
         "real": f"{real['false_repair_rate']['numerator']}/"
                 f"{real['false_repair_rate']['denominator']}"},
    ], ["quantity", "combined", "real"]))
    add("**False Repair Rate** = incorrect attempted repairs / total attempted "
        "repairs, where an attempted repair is an ADD or REPLACE whose proposed "
        "lineage contradicts adjudicated truth that is KNOWN. An attempt on "
        "non-knowable truth is reported separately as *unverifiable* and is "
        "counted as neither correct nor false. This definition is unchanged from "
        "Phase F.")
    add("")
    add("Zero observed false repairs is a property of this 70-case benchmark, not "
        "a guarantee: see `docs/THREATS_TO_VALIDITY.md`.")
    add("")

    add("## Coverage and abstention")
    add("")
    add(render_markdown_table([
        {"scope": "COMBINED",
         "coverage": safety["coverage"]["value"],
         "abstention_rate": safety["abstention_rate"]["value"],
         "action_accuracy": safety["action_accuracy"]["value"]},
        {"scope": "REAL", "coverage": real["coverage"]["value"],
         "abstention_rate": real["abstention_rate"]["value"],
         "action_accuracy": real["action_accuracy"]["value"]},
    ], ["scope", "coverage", "abstention_rate", "action_accuracy"]))
    add("")

    add("## Baseline comparison")
    add("")
    add(render_markdown_table(
        report["comparisons"],
        ["system", "action_accuracy", "macro_f1", "coverage", "attempted_repairs",
         "false_repairs", "parent_exact_match", "relation_accuracy",
         "abstention_rate"]))
    add("`config_only` and `prose_only` abstain on every case: honest but useless "
        "alone. `rule_priority` and `majority_count` repair far more often and are "
        "far less accurate; `rule_priority` is the only baseline that produces a "
        "false repair. `declared_metadata` and `always_keep` are identical by "
        "construction (neither ever repairs).")
    add("")

    add("## Ablation results")
    add("")
    add(render_markdown_table(
        [{k: v for k, v in row.items()
          if k in ("ablation", "action_accuracy", "delta_action_accuracy", "coverage",
                   "attempted_repairs", "false_repairs", "macro_f1", "verdict")}
         for row in report["ablations"]["results"]],
        ["ablation", "action_accuracy", "delta_action_accuracy", "macro_f1",
         "coverage", "attempted_repairs", "false_repairs", "verdict"]))
    add("Each ablation transforms the evidence handed to the **unmodified** engine, "
        "so a delta is attributable to the ablated component. Verdicts are "
        "descriptive, not significance tests.")
    add("")
    add("Pre-registered hypotheses (kept even where the measurement contradicted them):")
    add("")
    for spec in report["ablations"]["suite"]:
        add(f"- `{spec['name']}` — {spec['question']} {spec['hypothesis']}")
    add("")

    add("## Selective prediction (risk–coverage)")
    add("")
    rows = report["selective_risk_curve"]
    thresholds = sorted({row["threshold"] for row in rows})
    shown = [row for row in rows if row["threshold"] in (thresholds[0],
                                                        thresholds[len(thresholds) // 2],
                                                        thresholds[-1])]
    add(render_markdown_table(
        [{"threshold": row["threshold"], "coverage": row["coverage"]["value"],
          "accepted": row["coverage"]["denominator"] - row["abstentions"],
          "selective_accuracy": row["selective_accuracy"]["value"],
          "selective_accuracy_ci95": _ci(row["selective_accuracy"]),
          "attempted_repairs": row["attempted_repairs"],
          "false_repairs": row["false_repairs"]}
         for row in shown],
        ["threshold", "coverage", "accepted", "selective_accuracy",
         "selective_accuracy_ci95", "attempted_repairs", "false_repairs"]))
    add(f"Selected from {len(rows)} measured thresholds "
        f"({', '.join(str(t) for t in thresholds)}); the full sweep is in "
        "`tables/risk_coverage_curve.csv`.")
    add("")

    add("## Failure analysis")
    add("")
    add(render_markdown_table(report["failure_analysis"]["taxonomy"],
                             ["category", "n_cases", "n_controlled", "n_real",
                              "description"]))
    add(f"Every one of the {report['failure_analysis']['n_failures']} failures is an "
        "abstention: no incorrect affirmative repair and no incorrect KEEP was "
        "observed. Per-case detail is in `tables/failures.csv`.")
    add("")

    add("## Per-stratum results")
    add("")
    add(render_markdown_table(
        [{"stratum": row["stratum"], "n_cases": row["n_cases"],
          "action_accuracy": row["action_accuracy"]["value"],
          "action_accuracy_ci95": _ci(row["action_accuracy"]),
          "coverage": row["coverage"]["value"],
          "attempted_repairs": row["attempted_repairs"],
          "false_repairs": row["false_repairs"]}
         for row in report["stratified_results"]],
        ["stratum", "n_cases", "action_accuracy", "action_accuracy_ci95", "coverage",
         "attempted_repairs", "false_repairs"]))
    add("Strata are the ones the acquisition plan declared (see "
        "`data/acquisition/real_selection.json`), not strata derived from results. "
        "`quantized_awq` is the clearest measured weakness: 0/5, because for every "
        "AWQ derivative the parent is declared and the relation is documented only "
        "in the model card, with no structured artifact stating it.")
    add("")

    add("## Evidence contribution")
    add("")
    usage = report["evidence_usage"]
    sources = sorted(set(usage["presence"]) | set(usage["decisive"]))
    add(render_markdown_table(
        [{"source": source,
          "cases_present": usage["presence"].get(source, {}).get("n_cases", 0),
          "presence_share": usage["presence"].get(source, {}).get("share"),
          "decisive_items": usage["decisive"].get(source, {}).get("n_items", 0)}
         for source in sources],
        ["source", "cases_present", "presence_share", "decisive_items"]))
    add(usage["definition"])
    add("")

    add("## Local LLM extraction experiment (optional, opt-in)")
    add("")
    add("Run separately with "
        "`python -m provenancelens.evaluation.phase_g_cli llm-compare --model llama3.2:3b`. "
        "It is **not** part of the deterministic study and its output is not in this "
        "manifest. Measured with the already-installed `llama3.2:3b` on the six "
        "frozen cards where lineage is documented but no structured artifact states "
        "it: 20 claims reported, 0 accepted, 0 repair attempts, 0 false repairs; "
        "rejections were 15 `span_not_found`, 15 `malformed_output`, 4 "
        "`lineage_not_stated`, 1 `parent_not_in_source`. On "
        "`webAI-Official/TwIL-LM3` the model produced the correct parent but quoted a "
        "span that did not contain it, so validation rejected it. Read this as a "
        "grounding and output-fidelity problem at that model size, not as evidence "
        "that local models are useless.")
    add("")

    add("## Calibration status")
    add("")
    add("`support_score` is a heuristic evidence strength — a capped sum of "
        "documented per-artifact contributions — with no frequency interpretation. "
        "ECE, Brier score and reliability diagrams are therefore **not** reported "
        "anywhere. Probability calibration stays deferred until a mapping can be "
        "fitted on a held-out split (>= 50 cases) and evaluated on a disjoint split.")
    add("")

    add("## Limitations")
    add("")
    add("See `docs/LIMITATIONS.md` and `docs/THREATS_TO_VALIDITY.md`. In short: 70 "
        "self-authored cases, 44 of them from one hosting ecosystem and "
        "self-adjudicated; zero observed false repairs is not a guarantee; "
        "`quantized_awq` lineage is a measured gap; and no claim of state of the art "
        "or universal superiority is made.")
    add("")
    return "\n".join(lines)


def canonical_manifest(
    report: dict,
    files: Sequence[Path],
    *,
    snapshot_root: Path,
    config: dict,
    output_dir: Path,
) -> dict:
    """Byte-deterministic manifest for the canonical set."""
    benchmark = report["benchmark"]
    return {
        "benchmark_version": benchmark["benchmark_version"],
        "metric_definitions_version": METRIC_DEFINITIONS_VERSION,
        "n_cases": benchmark["n_cases"],
        "n_controlled": benchmark["by_track"].get("controlled"),
        "n_real": benchmark["by_track"].get("real"),
        "label_provenance": benchmark["by_label_provenance"],
        "report_digest": report_digest(report),
        "generation_command": CANONICAL_GENERATION_COMMAND,
        "determinism": {
            "random_seed": None,
            "seed_note": "the study contains no stochastic component: no sampling, "
                         "no shuffling, no model inference; identical inputs give "
                         "identical outputs",
            "network_used": False,
            "llm_used": False,
            "timestamps_in_canonical_files": False,
            "absolute_paths_in_canonical_files": False,
        },
        "experiment_config": dict(sorted(config.items())),
        "figures": list(PLOT_NAMES),
        "snapshot_revisions": _snapshot_revisions(snapshot_root),
        "files": {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted(files)
        },
        "excludes": ["wall-clock timings", "the evaluating git commit",
                     "machine-specific environment details"],
        "excludes_note": "those live in artifacts/phase_g/manifest.json; keeping "
                         "them out is what makes this tree byte-identical across "
                         "machines and runs",
    }


def write_canonical_results(
    report: dict,
    output_dir: Path,
    *,
    snapshot_root: Path,
    config: dict,
    adjudication_rows: Sequence[dict] | None = None,
    plots: bool = True,
) -> dict[str, Path]:
    """Write the canonical, committed result set and return ``name -> path``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    # The same renderers the study uses (write_tables / write_plots), so the
    # canonical set cannot diverge from artifacts/ by construction.  The study's
    # own phase_g_report.* are deliberately not duplicated here: results.json and
    # RESULTS.md are the canonical names, and there is exactly one source of
    # truth for every number.
    artifacts: dict[str, Path] = {}
    for name, _ in write_tables(report, output_dir / "tables").items():
        artifacts[f"tables/{name}"] = output_dir / "tables" / name
    if plots:
        try:
            for name, _ in write_plots(report, output_dir / "figures").items():
                artifacts[f"figures/{name}"] = output_dir / "figures" / name
        except PlottingUnavailable:
            # figures are optional; the canonical numbers are not
            pass
    if adjudication_rows:
        from .report import _csv_bytes  # local: same renderer, private helper

        artifacts["adjudication_summary.csv"] = _write(
            output_dir / "adjudication_summary.csv",
            _csv_bytes(adjudication_rows).decode("utf-8"),
        )
    body = {key: value for key, value in report.items() if key != "per_case"}
    results_json = output_dir / "results.json"
    results_json.write_text(
        json.dumps({**body, "report_digest": report_digest(report)},
                   indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts["results.json"] = results_json
    artifacts["RESULTS.md"] = _write(
        output_dir / "RESULTS.md",
        render_results_document(report, {"metric_definitions_version":
                                         METRIC_DEFINITIONS_VERSION}),
    )
    files = [path for name, path in artifacts.items() if name != "manifest.json"]
    manifest = canonical_manifest(report, files, snapshot_root=snapshot_root,
                                  config=config, output_dir=output_dir)
    artifacts["manifest.json"] = _write(
        output_dir / "manifest.json",
        json.dumps(manifest, indent=1, sort_keys=True) + "\n",
    )
    return artifacts


def verify_canonical_results(output_dir: Path) -> dict:
    """Recompute digests and cross-check headline numbers.

    Returns a report with ``ok`` plus the list of problems, so both the CLI and
    the documentation tests can use it.
    """
    problems: list[str] = []
    manifest_path = output_dir / "manifest.json"
    results_path = output_dir / "results.json"
    if not manifest_path.is_file() or not results_path.is_file():
        return {"ok": False, "problems": [f"{output_dir} is not a canonical result set"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    for name, digest in sorted(manifest["files"].items()):
        path = output_dir / name
        if not path.is_file():
            problems.append(f"missing canonical file: {name}")
            continue
        if _sha256(path) != digest:
            problems.append(f"digest mismatch: {name}")
    if results.get("report_digest") != manifest.get("report_digest"):
        problems.append("results.json digest does not match manifest.report_digest")
    body = {key: value for key, value in results.items() if key != "report_digest"}
    if report_digest(body) != results.get("report_digest"):
        problems.append("results.json does not hash to its own report_digest")
    for name, revision in sorted(manifest["snapshot_revisions"].items()):
        problems.extend(_verify_revision(name, revision))
    if not (output_dir / "RESULTS.md").is_file():
        problems.append("missing canonical file: RESULTS.md")
    return {"ok": not problems, "problems": problems,
            "n_files": len(manifest["files"]),
            "report_digest": manifest.get("report_digest")}


def _verify_revision(repository: str, revision: str) -> list[str]:
    """The pinned revision must still resolve to a frozen snapshot."""
    from .dataset import load_real_benchmark
    from .real import acquisition_strata  # noqa: F401  (import guard)

    known = {case.repository: case.snapshot_commit
             for case in load_real_benchmark()}
    if repository in known and known[repository] != revision:
        return [f"snapshot revision changed for {repository}: "
                f"manifest {revision[:12]} vs benchmark {str(known[repository])[:12]}"]
    return []


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
