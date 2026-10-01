"""Selective prediction over the heuristic support score.

Definitions (documented in the README as well):

    coverage           = non-ABSTAIN predictions / scored predictions
    selective_accuracy = correct predictions among non-ABSTAIN predictions
    abstention_rate    = ABSTAIN predictions / scored predictions

For a threshold ``t`` a prediction is *accepted* when the system did not
abstain **and** its raw support score is at least ``t``. Higher thresholds
trade coverage for accuracy; the false-repair column shows the safety cost at
each operating point.

Important: ``support_score`` is a heuristic evidence strength, not a
probability. This module therefore reports a *threshold sweep*, never a
calibration curve.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, ConfigDict

from .schema import CaseResult

__all__ = [
    "DEFAULT_THRESHOLDS",
    "SelectivePoint",
    "selective_sweep",
    "coverage_and_accuracy",
    "threshold_row",
]

#: Default sweep: 0.00 .. 1.00 in 0.05 steps, plus the observed score values.
DEFAULT_THRESHOLDS: tuple[float, ...] = tuple(round(0.05 * i, 2) for i in range(0, 21))


class SelectivePoint(BaseModel):
    """One operating point of the accuracy/coverage trade-off."""

    model_config = ConfigDict(extra="forbid")

    threshold: float
    n_scored: int
    accepted: int
    coverage: float | None
    selective_accuracy: float | None
    correct: int
    attempted_repairs: int
    false_repairs: int
    false_repair_rate: float | None
    abstentions: int
    abstention_rate: float | None


def coverage_and_accuracy(results: list[CaseResult]) -> tuple[float | None, float | None, int, int]:
    """(coverage, selective accuracy, accepted count, correct count)."""
    scored = [r for r in results if r.action_scored]
    accepted = [r for r in scored if not r.abstained]
    correct = sum(1 for r in accepted if r.action_correct)
    coverage = len(accepted) / len(scored) if scored else None
    selective = correct / len(accepted) if accepted else None
    return coverage, selective, len(accepted), correct


def threshold_row(results: list[CaseResult], threshold: float) -> SelectivePoint:
    """Metrics at one support-score threshold."""
    scored = [r for r in results if r.action_scored]
    accepted = [
        r for r in scored
        if not r.abstained and r.support_score >= threshold
    ]
    correct = sum(1 for r in accepted if r.action_correct)
    repairs = [r for r in accepted if r.repair_attempted]
    false_repairs = [r for r in repairs if r.false_repair is True]
    abstentions = [r for r in scored if r.abstained]
    coverage = len(accepted) / len(scored) if scored else None
    return SelectivePoint(
        threshold=round(threshold, 4),
        n_scored=len(scored),
        accepted=len(accepted),
        coverage=coverage,
        selective_accuracy=(correct / len(accepted)) if accepted else None,
        correct=correct,
        attempted_repairs=len(repairs),
        false_repairs=len(false_repairs),
        false_repair_rate=(len(false_repairs) / len(repairs)) if repairs else None,
        abstentions=len(abstentions),
        abstention_rate=(len(abstentions) / len(scored)) if scored else None,
    )


def selective_sweep(
    results: list[CaseResult],
    *,
    thresholds: Iterable[float] | None = None,
) -> list[SelectivePoint]:
    """Sweep thresholds plus every distinct observed support score."""
    values = set(thresholds or DEFAULT_THRESHOLDS)
    values.update(round(r.support_score, 4) for r in results if r.action_scored)
    return [threshold_row(results, value) for value in sorted(values)]


def observed_thresholds(results: list[CaseResult]) -> list[float]:
    """Only the support scores actually observed (no interpolation)."""
    return sorted({round(r.support_score, 4) for r in results if r.action_scored})
