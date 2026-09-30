"""Optional local-LLM comparator (opt-in, local-only, never part of the default run).

The deterministic system abstains whenever no *structured* artifact identifies a
parent.  A large share of real repositories document their lineage only in a
model card, so the obvious question is whether a small local open-weight model
can recover that coverage - and, critically, whether it does so without
introducing an unsafe repair.

This module answers exactly that, and it is deliberately fenced off:

* it never runs unless explicitly requested (CLI ``llm-compare``); the default
  Phase G study, the test suite and the report digest stay LLM-free;
* it refuses to run unless the model is **already installed locally** - the
  study never pulls a model, and :func:`run_local_llm_comparator` fails closed
  rather than downloading anything;
* claims go through the Phase E validator before becoming evidence, so a
  hallucinated or malformed claim is rejected rather than trusted;
* only validated evidence is handed to the unmodified engine, and the
  comparison is reported per case against the adjudicated truth;
* results are written to a separate artifact with their own digest, because a
  local model's output is environment-dependent and must never be mixed into
  the deterministic digest of the main study.

Usage::

    python -m provenancelens.evaluation.phase_g_cli llm-compare --model llama3.2:3b
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .dataset import load_benchmark
from .runner import case_inputs, decide_case, score_decision
from .schema import BenchmarkCase, Track

__all__ = [
    "DEFAULT_MODEL",
    "LLMComparatorUnavailable",
    "llm_comparator_targets",
    "run_local_llm_comparator",
    "comparator_summary",
]

#: Small, already-installed-by-the-operator local model.  ProvenanceLens never
#: installs or pulls a model; this is only a default *name* to try.
DEFAULT_MODEL = "llama3.2:3b"

#: Cap on how many cards are sent to the model in one comparator run.
MAX_TARGETS = 12


class LLMComparatorUnavailable(RuntimeError):
    """Raised when the local runtime or the requested model is not available."""


def llm_comparator_targets(cases: Sequence[BenchmarkCase]) -> list[BenchmarkCase]:
    """Cases where local-LLM extraction is worth trying.

    Selection is made from *ground truth and declared metadata only*, never from
    the system's own decisions, so the comparator cannot be accused of only
    showing the model the cases it happened to get right.  A target is a real
    case whose card carries a canonical lineage statement that the structured
    parsers did not turn into evidence: officially documented lineage with
    incomplete declared metadata.
    """
    targets = []
    for case in cases:
        if case.track is not Track.REAL or not case.snapshot_files:
            continue
        if case.truth.metadata_state.value not in ("incomplete", "valid"):
            continue
        _, evidence, _ = case_inputs(case)
        if any(item.role.value == "independent" and item.source_type.value
               in ("adapter_config", "merge_config", "training_config", "config")
               for item in evidence):
            continue  # structured evidence already exists; nothing to recover
        readme = case.snapshot_files.get("README.md")
        if not readme or "huggingface.co/" not in readme.lower():
            continue
        targets.append(case)
    return targets[:MAX_TARGETS]


def _build_extractor(model_name: str) -> Any:
    try:
        from ..llm_runtime import build_default_chat_model, llm_availability
    except Exception as exc:  # pragma: no cover - optional extras missing
        raise LLMComparatorUnavailable(f"local LLM runtime unavailable: {exc}") from exc
    try:
        availability = llm_availability(model=model_name)
    except Exception as exc:  # pragma: no cover - runtime unreachable
        raise LLMComparatorUnavailable(
            f"local LLM runtime is not reachable: {exc}; ProvenanceLens never "
            f"starts or downloads a model for you"
        ) from exc
    if not availability.available:
        raise LLMComparatorUnavailable(
            f"model {model_name!r} is not installed locally "
            f"(installed: {', '.join(availability.installed_models) or 'none'}); "
            f"install it manually if you want this optional experiment"
        )
    from ..prose.extractor import LLMProseExtractor

    return LLMProseExtractor(build_default_chat_model(model=model_name),
                             model_name=model_name)


def run_local_llm_comparator(
    cases: Sequence[BenchmarkCase] | None = None,
    *,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Run the optional comparator and return a JSON-serialisable report."""
    from .. import __version__

    benchmark = list(cases if cases is not None else load_benchmark("real"))
    targets = llm_comparator_targets(benchmark)
    extractor = _build_extractor(model)

    rows: list[dict] = []
    for case in targets:
        readme = case.snapshot_files.get("README.md", "")
        baseline = decide_case(case)
        try:
            report = extractor.extract(
                readme, source_name="README.md", repository=case.repository,
                revision=case.snapshot_commit,
            )
            extra = list(report.evidence)
            failure_detail = None
        except Exception as exc:  # fail closed: a model error is not evidence
            extra, failure_detail = [], f"{type(exc).__name__}: {str(exc)[:200]}"
        from ..schemas.extraction import ExtractionIssue

        declared, evidence, issues = case_inputs(case)
        from ..reasoning import DEFAULT_POLICY, decide_lineage
        from ..reasoning import aggregate_candidates

        combined = [*evidence, *extra]
        candidates = aggregate_candidates(combined, issues=issues) if issues else None
        decision = decide_lineage(
            case.repository, declared, combined, policy=DEFAULT_POLICY,
            candidates=candidates,
        ).decision
        result = score_decision(case, decision, system="provenancelens+local_llm")
        rows.append({
            "case_id": case.case_id,
            "repository": case.repository,
            "expected_action": case.expected_action.value,
            "truth_metadata_state": case.truth.metadata_state.value,
            "truth_parents": list(case.truth.parents or ()),
            "deterministic": {
                "action": baseline.decision.value,
                "support_score": baseline.support_score,
                "action_correct": score_decision(case, baseline,
                                                system="provenancelens").action_correct,
            },
            "with_local_llm": {
                "action": decision.decision.value,
                "support_score": decision.support_score,
                "action_correct": result.action_correct,
                "repair_attempted": result.repair_attempted,
                "false_repair": result.false_repair,
                "predicted_parents": list(result.predicted_parents),
            },
            "claims_reported": getattr(report, "claims_reported", 0) if failure_detail is None else 0,
            "claims_accepted": getattr(report, "claims_accepted", 0) if failure_detail is None else 0,
            "evidence_items": len(extra),
            "rejections": [
                {"code": failure.code.value, "detail": failure.detail[:160]}
                for failure in (getattr(report, "failures", []) if failure_detail is None else [])
            ],
            "error": failure_detail,
        })

    from ..prose.prompt import prompt_digest

    summary = comparator_summary(rows)
    return {
        "experiment": "optional_local_llm_comparator",
        "status": "ran",
        "model": model,
        "package_version": __version__,
        "prompt_version": extractor.prompt_version,
        "prompt_digest": prompt_digest(),
        "temperature": 0.0,
        "targets_selected_by": "ground truth and declared metadata only, never by "
                               "the system's own decisions",
        "selection_rule": "real cases with incomplete or valid declared metadata, no "
                          "structured lineage evidence, and a model card containing a "
                          "canonical huggingface.co reference",
        "determinism": "not part of the deterministic report digest: local model output "
                       "depends on the installed model build and runtime version",
        "summary": summary,
        "rows": rows,
    }


def comparator_summary(rows: Sequence[dict]) -> dict:
    """Aggregate the comparator without ever hiding a false repair."""
    n = len(rows)
    recovered = [r for r in rows if r["with_local_llm"]["action_correct"]
                 and not r["deterministic"]["action_correct"]]
    broken = [r for r in rows if r["deterministic"]["action_correct"]
              and not r["with_local_llm"]["action_correct"]]
    attempts = [r for r in rows if r["with_local_llm"]["repair_attempted"]]
    false_repairs = [r for r in attempts if r["with_local_llm"]["false_repair"] is True]
    return {
        "n_cases": n,
        "deterministic_correct": sum(1 for r in rows if r["deterministic"]["action_correct"]),
        "with_local_llm_correct": sum(1 for r in rows if r["with_local_llm"]["action_correct"]),
        "recovered_by_llm": len(recovered),
        "regressed_by_llm": len(broken),
        "claims_reported": sum(r["claims_reported"] for r in rows),
        "claims_accepted": sum(r["claims_accepted"] for r in rows),
        "claim_acceptance_rate": (
            sum(r["claims_accepted"] for r in rows)
            / sum(r["claims_reported"] for r in rows)
            if sum(r["claims_reported"] for r in rows) else None
        ),
        "repair_attempts": len(attempts),
        "false_repairs": len(false_repairs),
        "false_repair_case_ids": [r["case_id"] for r in false_repairs],
        "recovered_case_ids": [r["case_id"] for r in recovered],
        "regressed_case_ids": [r["case_id"] for r in broken],
    }


def write_comparator_report(report: dict, directory: Path) -> Path:
    """Write the comparator artifact, kept separate from the main study."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "llm_comparator.json"
    path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")
    return path
