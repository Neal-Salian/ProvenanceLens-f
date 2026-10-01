"""Calibration infrastructure - deliberately NOT applied to support_score.

The ProvenanceLens ``support_score`` is a *heuristic evidence strength*. It is
not a probability, and reporting ECE/Brier/reliability diagrams computed from
it would be misleading.

This module therefore provides:

* a :class:`CalibratedScore` schema for a *future* calibrated probability that
  is fitted on a held-out calibration split;
* mathematically standard ECE/Brier implementations that **refuse** to run on
  uncalibrated inputs, so nobody can accidentally publish a fake calibration
  number;
* a :func:`calibration_status` helper explaining, in the output, why no
  calibration is reported yet.

Fitting is intentionally deferred: the current benchmark (26 synthetic +
3 adjudicated real cases) is far too small to support a calibration split, and
any fit/evaluate overlap would be leakage.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .schema import CaseResult

__all__ = [
    "CalibrationStatus",
    "CalibrationBlocker",
    "CalibratedScore",
    "CalibrationAssessment",
    "UncalibratedInputError",
    "expected_calibration_error",
    "brier_score",
    "calibration_status",
    "MIN_CASES_FOR_FIT",
]

#: A calibration split below this size is not informative enough to fit on.
MIN_CASES_FOR_FIT = 50


class CalibrationStatus(str, Enum):
    DEFERRED = "deferred"
    AVAILABLE = "available"


class CalibrationBlocker(str, Enum):
    RAW_SCORE_IS_NOT_A_PROBABILITY = "raw_score_is_not_a_probability"
    NO_FITTED_MAPPING = "no_fitted_mapping"
    INSUFFICIENT_CASES = "insufficient_cases"
    NO_HELD_OUT_SPLIT = "no_held_out_split"


class UncalibratedInputError(ValueError):
    """Raised when calibration metrics are requested for uncalibrated inputs."""


class CalibratedScore(BaseModel):
    """A probability produced by a mapping fitted on a held-out split."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    probability: float = Field(ge=0.0, le=1.0)
    #: Identifier of the fitted mapping (so results stay reproducible).
    mapping_id: str
    #: True when the case belonged to the split used for fitting.
    fitted_on: bool = False


class CalibrationAssessment(BaseModel):
    """Why calibration was (not) reported for a run."""

    model_config = ConfigDict(extra="forbid")

    status: CalibrationStatus
    blockers: tuple[CalibrationBlocker, ...] = ()
    n_cases: int = 0
    min_cases_for_fit: int = MIN_CASES_FOR_FIT
    statement: str = ""


_STATEMENT = (
    "support_score is a heuristic evidence strength on a 0..1 scale, not a probability: "
    "it is a capped sum of documented per-artifact contributions and carries no "
    "frequency interpretation. ECE, Brier score and reliability diagrams are therefore "
    "not reported for it. Fit a CalibratedScore mapping on a held-out calibration split "
    "(>= {min_cases} cases) and evaluate it on a disjoint split in a later phase."
)


def _require_calibrated(probabilities: list[float]) -> None:
    if any(not 0.0 <= p <= 1.0 for p in probabilities):
        raise UncalibratedInputError("probabilities must lie in [0, 1]")


def expected_calibration_error(
    probabilities: list[float], outcomes: list[int], *, n_bins: int = 10
) -> float:
    """Standard ECE. **Requires genuine probabilities**, not support scores."""
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must be the same length")
    if not probabilities:
        raise ValueError("no data")
    _require_calibrated(probabilities)
    total = len(probabilities)
    error = 0.0
    for index in range(n_bins):
        low = index / n_bins
        high = (index + 1) / n_bins
        in_bin = [
            (p, y) for p, y in zip(probabilities, outcomes)
            if (low <= p < high) or (index == n_bins - 1 and p == 1.0)
        ]
        if not in_bin:
            continue
        mean_confidence = sum(p for p, _ in in_bin) / len(in_bin)
        accuracy = sum(y for _, y in in_bin) / len(in_bin)
        error += (len(in_bin) / total) * abs(accuracy - mean_confidence)
    return error


def brier_score(probabilities: list[float], outcomes: list[int]) -> float:
    """Standard Brier score. **Requires genuine probabilities**."""
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must be the same length")
    if not probabilities:
        raise ValueError("no data")
    _require_calibrated(probabilities)
    return sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / len(probabilities)


def calibration_status(
    results: list[CaseResult], *, calibrated: list[CalibratedScore] | None = None,
    has_held_out_split: bool = False,
) -> CalibrationAssessment:
    """Explain the calibration status of a run (never fabricates numbers)."""
    scored = [r for r in results if r.action_scored]
    blockers: list[CalibrationBlocker] = []
    if not calibrated:
        blockers.append(CalibrationBlocker.RAW_SCORE_IS_NOT_A_PROBABILITY)
        blockers.append(CalibrationBlocker.NO_FITTED_MAPPING)
    if len(scored) < MIN_CASES_FOR_FIT:
        blockers.append(CalibrationBlocker.INSUFFICIENT_CASES)
    if not has_held_out_split:
        blockers.append(CalibrationBlocker.NO_HELD_OUT_SPLIT)
    return CalibrationAssessment(
        status=(CalibrationStatus.AVAILABLE if not blockers
                else CalibrationStatus.DEFERRED),
        blockers=tuple(blockers),
        n_cases=len(scored),
        statement=_STATEMENT.format(min_cases=MIN_CASES_FOR_FIT),
    )
