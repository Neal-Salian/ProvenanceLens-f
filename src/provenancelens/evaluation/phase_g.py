"""Phase G experimental study: full system, baselines, ablations, analyses.

Everything in this module is *evaluation only*.  It reads the frozen
benchmark, re-runs the unmodified production engine and the registered
baselines, runs the ablation suite and derives the analyses required by
the Phase G research questions:

=================================  =========================================
Analysis                           Research question
=================================  =========================================
``headline_metrics``               RQ1/RQ2 - does it work, how often
``ablation_effects``               RQ4-RQ8 - which components matter
``selective_risk_curve``           RQ3 - safety/coverage trade-off
``failure_analysis``               RQ9 - where does it fail and why
``evidence_usage``                 RQ6 - which evidence changes decisions
``stratified_results``             RQ10 - does it generalise per stratum
=================================  =========================================

Design commitments that make the numbers trustworthy:

* **Ground truth never comes from the system.**  Labels are adjudicated in
  ``adjudication/real_cases.yaml`` (real) or constructed (controlled); no
  analysis module imports the decision engine to derive a label.
* **Abstention is never counted as correct** unless the benchmark expects
  an abstention, and unverifiable repairs are never folded into either
  "correct" or "false".
* **Statistics are reported with intervals.**  Small samples make point
  estimates fragile, so every headline proportion carries a Wilson 95%
  interval and no significance is claimed anywhere.
* **Determinism.**  No randomness, no network, no clocks in any metric
  value; ``manifest`` records the environment separately.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Sequence

from ..schemas.evidence import EvidenceItem, EvidenceRole, SourceType
from .ablations import ABLATIONS, ablation_table, run_ablations
from .dataset import benchmark_summary, load_benchmark
from .metrics import compute_metrics
from .run import DEFAULT_SYSTEMS, run_system
from .runner import case_inputs
from .schema import BenchmarkCase, CaseResult, Track

__all__ = [
    "wilson_interval",
    "proportion",
    "headline_metrics",
    "ablation_effects",
    "selective_risk_curve",
    "failure_analysis",
    "evidence_usage",
    "stratified_results",
    "run_phase_g",
]

#: 95% two-sided normal quantile, hard-coded so no SciPy dependency is needed.
_Z_95 = 1.959963984540054


def wilson_interval(
    successes: int, trials: int, *, z: float = _Z_95
) -> dict:
    """Wilson score interval for a binomial proportion.

    Preferred over the normal approximation here because several headline
    numbers have denominators below 30, where the Wald interval produces
    nonsensical bounds (and the exact method is awkward at zero counts).
    """
    if trials <= 0:
        return {"numerator": successes, "denominator": trials, "value": None,
                "low": None, "high": None,
                "definition": "Wilson 95% score interval for a binomial proportion"}
    phat = successes / trials
    denominator = 1.0 + z * z / trials
    center = (phat + z * z / (2 * trials)) / denominator
    margin = (
        z / denominator
        * math.sqrt(phat * (1 - phat) / trials + z * z / (4 * trials * trials))
    )
    # rounded so exact-zero counts do not surface as float noise (e.g. 2.8e-17)
    return {
        "numerator": successes,
        "denominator": trials,
        "value": round(phat, 12),
        "low": round(max(0.0, center - margin), 12),
        "high": round(min(1.0, center + margin), 12),
        "definition": "Wilson 95% score interval for a binomial proportion",
    }


def proportion(successes: int, trials: int) -> dict:
    """Headline proportion with its interval, in the report's metric shape."""
    return wilson_interval(successes, trials)


# --- RQ1/RQ2: headline metrics -------------------------------------------------

def _track_block(metrics: dict, track: str | None) -> dict:
    return metrics if track is None else metrics["by_track"][track]


def headline_metrics(
    system_metrics: dict, *, track: str | None = None, include_ci: bool = True
) -> list[dict]:
    """One row per headline metric with denominators and (by default) CIs."""
    block = _track_block(system_metrics, track)
    rows: list[dict] = []

    def add(name: str, numerator: int, denominator: int, definition: str) -> None:
        row = {
            "metric": name,
            "numerator": numerator,
            "denominator": denominator,
            "value": (numerator / denominator) if denominator else None,
            "definition": definition,
        }
        if include_ci:
            row["ci95"] = wilson_interval(numerator, denominator)
        rows.append(row)

    action = block["action"]["accuracy"]
    add("action_accuracy", action["numerator"], action["denominator"],
        action["definition"])
    parent = block["parent"]
    add("parent_exact_match", parent["numerator"], parent["denominator"],
        parent["definition"])
    relation = block["relation"]["accuracy"]
    add("relation_accuracy", relation["numerator"], relation["denominator"],
        relation["definition"])
    coverage = block["coverage"]
    add("coverage", coverage["numerator"], coverage["denominator"],
        coverage["definition"])
    repairs = block["repair_safety"]
    add("repair_attempt_rate", repairs["attempted_repairs"]["numerator"],
        repairs["attempted_repairs"]["denominator"],
        repairs["attempted_repairs"]["definition"])
    add("false_repair_rate", repairs["false_repairs"]["numerator"],
        repairs["false_repairs"]["denominator"],
        repairs["false_repairs"]["definition"])
    add("unverifiable_repair_rate", repairs["unverifiable_repairs"]["numerator"],
        repairs["unverifiable_repairs"]["denominator"],
        repairs["unverifiable_repairs"]["definition"])
    add("abstention_rate", repairs["abstentions"]["numerator"],
        repairs["abstentions"]["denominator"], repairs["abstentions"]["definition"])
    return rows


# --- RQ4-RQ8: ablations -------------------------------------------------------

def ablation_effects(ablation_runs: dict, *, track: str | None = None) -> list[dict]:
    """Ablation rows enriched with the pre-registered hypothesis and verdict.

    The verdict compares the measured delta against the reference run; it is
    deliberately descriptive ("supported" / "not supported") rather than a
    significance test, because these are small, paired samples.
    """
    rows = ablation_table(ablation_runs, track=track)
    for row in rows:
        spec = next((s for s in ABLATIONS if s.name == row["ablation"]), None)
        row["question"] = spec.question if spec else "reference run, no transformation"
        row["hypothesis"] = spec.hypothesis if spec else "baseline for every ablation delta"
        delta = row.get("delta_action_accuracy")
        if row["ablation"] == "full" or delta is None:
            row["verdict"] = "reference"
        elif delta < -0.02:
            row["verdict"] = "component matters (removing it hurts)"
        elif delta > 0.02:
            row["verdict"] = "component not needed (removing it helps)"
        else:
            row["verdict"] = "no measurable effect on this benchmark"
    return rows


# --- RQ3: selective risk ------------------------------------------------------

def selective_risk_curve(system_metrics: dict, *, track: str | None = None) -> list[dict]:
    """Risk/coverage points with intervals, read from the Phase F sweep."""
    sweep = system_metrics["selective"]
    rows = []
    for point in sweep:
        accepted = point["accepted"]
        rows.append({
            "threshold": point["threshold"],
            "coverage": proportion(accepted, point["n_scored"]),
            "selective_accuracy": proportion(point["correct"], accepted)
            if accepted else proportion(0, 0),
            "attempted_repairs": point["attempted_repairs"],
            "false_repairs": point["false_repairs"],
            "false_repair_rate": proportion(point["false_repairs"],
                                            point["attempted_repairs"])
            if point["attempted_repairs"] else proportion(0, 0),
            "abstentions": point["abstentions"],
            "abstention_rate": proportion(point["abstentions"], point["n_scored"]),
        })
    return rows


# --- RQ9: failure analysis ----------------------------------------------------

#: Ordered failure taxonomy.  A case is placed in the first matching bucket, so
#: every failure is counted exactly once and the categories stay stable.
_FAILURE_TAXONOMY: tuple[tuple[str, str], ...] = (
    ("correct", "the decision matched the adjudicated label"),
    ("unverifiable_lineage",
     "no independent evidence exists, so abstention is the only safe action"),
    ("insufficient_support",
     "evidence exists but its support score is below the policy threshold"),
    ("relation_not_provable",
     "the parent is identifiable but no artifact establishes the relation"),
    ("prose_only_lineage",
     "lineage is documented only in model-card prose without a canonical id"),
    ("declared_metadata_contradicted",
     "the declared metadata contradicts what independent evidence shows"),
    ("multi_parent_conflict",
     "several parents are supported and the policy cannot choose among them"),
    ("false_repair",
     "an attempted repair contradicted knowable truth"),
    ("incorrect_non_repair",
     "a KEEP or abstention decision was wrong for another reason"),
)


def _categorise(result: CaseResult, case: BenchmarkCase) -> str:
    if result.false_repair is True:
        return "false_repair"
    if result.action_correct:
        return "correct"
    evidence, _ = _decision_evidence(case)
    independent = [item for item in evidence if item.role is EvidenceRole.INDEPENDENT]
    has_prose = any(
        item.role is EvidenceRole.INDEPENDENT
        and item.source_type in (SourceType.README, SourceType.OTHER)
        for item in evidence
    )
    if not independent:
        return "unverifiable_lineage"
    if result.abstained:
        return "prose_only_lineage" if has_prose else "insufficient_support"
    if case.truth.metadata_state.value == "incorrect":
        return "declared_metadata_contradicted"
    if len(independent) > 1 and {i.candidate_parent for i in independent} > {
        p for p in (case.truth.parents or ()) if p
    }:
        return "multi_parent_conflict"
    return "incorrect_non_repair"


def _decision_evidence(case: BenchmarkCase) -> tuple[list[EvidenceItem], list]:
    evidence, issues = case_inputs(case)[1:]
    return evidence, issues


def failure_analysis(
    results: Sequence[CaseResult], cases: Sequence[BenchmarkCase]
) -> dict:
    """Categorise every failure and summarise the confusion patterns.

    ``cases`` is indexed by ``case_id`` so the analysis can inspect the
    evidence available at decision time - it never re-derives a label.
    """
    by_id = {case.case_id: case for case in cases}
    counts: Counter = Counter()
    per_track: dict[str, Counter] = defaultdict(Counter)
    failures: list[dict] = []
    for result in results:
        category = _categorise(result, by_id[result.case_id])
        counts[category] += 1
        per_track[result.track.value][category] += 1
        if category == "correct":
            continue
        case = by_id[result.case_id]
        failures.append({
            "case_id": result.case_id,
            "track": result.track.value,
            "category": category,
            "expected_action": result.expected_action.value,
            "predicted_action": result.predicted_action.value,
            "support_score": result.support_score,
            "conflicts": list(result.conflicts),
            "truth_metadata_state": case.truth.metadata_state.value,
            "truth_parents_status": case.truth.parents_status.value,
            "repair_attempted": result.repair_attempted,
            "false_repair": result.false_repair,
            "reasoning_summary": result.reasoning_summary,
        })
    failures.sort(key=lambda row: (row["category"], row["case_id"]))
    taxonomy = [
        {
            "category": name,
            "description": description,
            "n_cases": counts.get(name, 0),
            **{f"n_{track}": counter.get(name, 0)
               for track, counter in sorted(per_track.items())},
        }
        for name, description in _FAILURE_TAXONOMY
    ]
    return {
        "taxonomy": taxonomy,
        "total": len(results),
        "n_failures": sum(1 for row in failures),
        "failures": failures,
        "definition": "each case is assigned to exactly one category; a failure is "
                      "any case whose category is not 'correct'",
    }


# --- RQ6: evidence usage ------------------------------------------------------

def evidence_usage(cases: Sequence[BenchmarkCase]) -> dict:
    """How often each evidence source is present, and which source matters.

    Frequency is reported separately from the ablation-based attribution in
    :func:`ablation_effects`: a source can be *common but irrelevant* or
    *rare but decisive*, and conflating the two is the classic way evidence
    analysis misleads.  ``decisive`` counts cases where the independent
    evidence proposes the adjudicated parent set.
    """
    presence: Counter = Counter()
    declared_only: Counter = Counter()
    decisive: Counter = Counter()
    n_cases = 0
    for case in cases:
        evidence, _ = _decision_evidence(case)
        independent = [i for i in evidence if i.role is EvidenceRole.INDEPENDENT]
        n_cases += 1
        kinds = {item.source_type for item in independent}
        for source in kinds:
            presence[source.value] += 1
        if not independent:
            declared_only["no_independent_evidence"] += 1
            continue
        truth = {p for p in (case.truth.parents or ())}
        for item in independent:
            if item.candidate_parent and item.candidate_parent in truth:
                decisive[item.source_type.value] += 1
    total = n_cases or 1
    return {
        "n_cases": n_cases,
        "presence": {
            source: {"n_cases": count, "share": count / total,
                     "definition": "cases whose independent evidence includes this source"}
            for source, count in sorted(presence.items())
        },
        "declared_only": dict(sorted(declared_only.items())),
        "decisive": {
            source: {"n_items": count,
                     "definition": "independent evidence items of this source whose "
                                   "candidate parent is in the adjudicated parent set"}
            for source, count in sorted(decisive.items())
        },
        "definition": "presence is frequency; decisiveness is attribution. Only tool-generated "
                      "lineage fields (adapter/merge/training configs) may be decisive, because "
                      "declared metadata is the audit subject and never independent evidence.",
    }


# --- RQ10: stratification -----------------------------------------------------

#: Real-benchmark strata, defined from the acquisition plan rather than from any
#: measured outcome, so stratification cannot be tuned to the results.
_STRATA: tuple[tuple[str, str], ...] = (
    ("peft_adapters", "adapter-config lineage declared in the repository"),
    ("lora_adapters", "adapter/LoRA fine-tune lineage"),
    ("mergekit_merges", "mergekit merge configuration"),
    ("quantized_gguf", "quantized derivative (GGUF and friends)"),
    ("quantized_awq", "AWQ quantized derivative"),
    ("instruction_finetunes", "instruction finetune declared in model metadata"),
)


def _stratum(case: BenchmarkCase) -> str:
    if case.track is Track.CONTROLLED:
        return "controlled"
    for tag in case.tags:
        if tag.startswith("stratum:"):
            return tag.split(":", 1)[1]
    return "pre_phase_g"


def stratified_results(results: Sequence[CaseResult], cases: Sequence[BenchmarkCase],
                       *, system_metrics: dict) -> list[dict]:
    """Per-stratum action accuracy, coverage and repair safety."""
    stratum_of = {case.case_id: _stratum(case) for case in cases}
    buckets: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        buckets[stratum_of[result.case_id]].append(result)
    rows = []
    for stratum in sorted(buckets):
        subset = buckets[stratum]
        correct = sum(1 for r in subset if r.action_correct)
        attempts = sum(1 for r in subset if r.repair_attempted)
        false_repairs = sum(
            1 for r in subset if r.false_repair is True
        )
        abstained = sum(1 for r in subset if r.abstained)
        rows.append({
            "stratum": stratum,
            "n_cases": len(subset),
            "action_accuracy": proportion(correct, len(subset)),
            "coverage": proportion(len(subset) - abstained, len(subset)),
            "attempted_repairs": attempts,
            "false_repairs": false_repairs,
            "false_repair_rate": proportion(false_repairs, attempts) if attempts
            else proportion(0, 0),
        })
    return rows


# --- orchestration ------------------------------------------------------------

def run_phase_g(
    *,
    systems: Sequence[str] = DEFAULT_SYSTEMS,
    track: Track | str | None = None,
    root: Path | None = None,
    include_ablations: bool = True,
    include_extraction: bool = False,
) -> dict:
    """Run the whole Phase G study and return every analysis.

    The returned mapping is JSON-serialisable except for the
    ``per_case``/``raw`` members, which the CLI strips before writing.
    """
    track = Track(track) if isinstance(track, str) else track
    cases = load_benchmark(track, root=root)
    results = {system: run_system(system, cases) for system in systems}
    metrics = {
        system: compute_metrics(system_results, system=system)
        for system, system_results in results.items()
    }
    for system in systems:
        from .selective import selective_sweep

        metrics[system]["selective"] = [
            point.model_dump(mode="json") for point in selective_sweep(results[system])
        ]

    main = metrics.get("provenancelens", next(iter(metrics.values())))
    present_tracks = {case.track.value for case in cases}
    report: dict = {
        "benchmark": benchmark_summary(cases),
        "systems": {
            system: {
                "headline": headline_metrics(system_metrics),
                **{
                    f"headline_{name}": headline_metrics(system_metrics, track=name)
                    for name in ("real", "controlled") if name in present_tracks
                },
            }
            for system, system_metrics in metrics.items()
        },
        "comparisons": _system_comparison(metrics),
        "action_confusion": main["action"]["confusion"],
        "selective_risk_curve": selective_risk_curve(main),
        "failure_analysis": failure_analysis(results["provenancelens"], cases),
        "evidence_usage": evidence_usage(cases),
        "stratified_results": stratified_results(results["provenancelens"], cases,
                                                 system_metrics=main),
        "extraction_available": bool(include_extraction),
    }
    if include_ablations:
        ablation_runs = run_ablations(cases)
        report["ablations"] = {
            "suite": [spec.describe() for spec in ABLATIONS],
            "results": ablation_effects(ablation_runs),
            "results_real": ablation_effects(ablation_runs, track="real"),
            "results_controlled": ablation_effects(ablation_runs, track="controlled"),
        }
    report["per_case"] = {
        system: [result.model_dump(mode="json") for result in system_results]
        for system, system_results in results.items()
    }
    return report


def _system_comparison(metrics: dict) -> list[dict]:
    """Headline rows for every system, ordered by action accuracy."""
    rows = []
    for system, system_metrics in metrics.items():
        block = system_metrics
        rows.append({
            "system": system,
            "n_cases": block["n_cases"],
            "action_accuracy": block["action"]["accuracy"]["value"],
            "action_correct": block["action"]["accuracy"]["numerator"],
            "macro_f1": block["action"]["macro_f1"]["value"],
            "coverage": block["coverage"]["value"],
            "attempted_repairs": block["repair_safety"]["attempted_repairs"]["numerator"],
            "false_repairs": block["repair_safety"]["false_repairs"]["numerator"],
            "parent_exact_match": block["parent"]["value"],
            "relation_accuracy": block["relation"]["accuracy"]["value"],
            "abstention_rate": block["repair_safety"]["abstentions"]["value"],
        })
    rows.sort(key=lambda row: (-row["action_accuracy"], row["system"]))
    return rows


