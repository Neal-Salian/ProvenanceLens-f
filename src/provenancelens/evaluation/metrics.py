"""Transparent metrics with explicit denominators.

Definitions used here (and reported verbatim in every run):

* parent exact-match accuracy - over cases whose adjudicated parent truth is
  ``KNOWN``; multi-parent truth is compared as a **set**, order-insensitive.
* relation accuracy / macro P, R, F1 - over cases whose relation truth is
  ``KNOWN``. A case is correct only when the proposed relation equals the
  adjudicated one; ABSTAIN counts as "no relation proposed" and is therefore
  wrong on those cases (abstentions are reported separately as well).
* action accuracy / macro P, R, F1 - over all scored cases; ambiguous cases
  accept any action in ``acceptable_actions``.
* **false repair** - the system attempted ADD or REPLACE and the proposed
  lineage contradicts *known* adjudicated truth::

      false_repair_rate = incorrect attempted repairs / total attempted repairs

  Attempts whose truth is not knowable are reported separately as
  ``unverifiable_repairs``; they are never counted as correct, and never
  counted as false either. An additional incidence over all scored cases is
  reported as ``false_repair_incidence`` so denominators are never ambiguous.
* abstention rate - abstained / scored cases.

Zero denominators yield ``value=None`` (never 0.0), so "no data" is
distinguishable from "zero errors".
"""

from __future__ import annotations

from collections import Counter

from ..schemas.audit import Decision
from .schema import (
    CaseResult,
    ClassificationMetrics,
    CountMetric,
    RepairSafetyMetrics,
    Track,
    TrackMetrics,
)

__all__ = [
    "ratio",
    "classification_from_pairs",
    "action_metrics",
    "classification_metrics",
    "parent_accuracy",
    "parent_accuracy_selective",
    "relation_accuracy_selective",
    "coverage",
    "relation_metrics",
    "repair_safety",
    "compute_track_metrics",
    "compute_metrics",
]

FALSE_REPAIR_DEFINITION = (
    "false_repair_rate = incorrect attempted repairs / total attempted repairs; an "
    "attempted repair is ADD or REPLACE whose proposed lineage contradicts adjudicated "
    "truth that is KNOWN. Attempts on non-knowable truth are reported separately as "
    "unverifiable repairs."
)

ACTION_LABELS = tuple(d.value for d in Decision)


def ratio(numerator: int, denominator: int, definition: str) -> CountMetric:
    """A ratio with a visible denominator; ``None`` when undefined."""
    return CountMetric(
        numerator=numerator,
        denominator=denominator,
        value=(numerator / denominator) if denominator else None,
        definition=definition,
    )


def classification_from_pairs(
    pairs: list[tuple[str, str]], *, labels: tuple[str, ...], name: str
) -> ClassificationMetrics:
    """Accuracy and per-class P/R/F1 from (expected, predicted) label pairs.

    Used for both actions and relations so the confusion matrix always reflects
    the labels actually being scored.
    """
    total = len(pairs)
    correct = sum(1 for expected, predicted in pairs if expected == predicted)

    true_positive: Counter[str] = Counter()
    false_positive: Counter[str] = Counter()
    false_negative: Counter[str] = Counter()
    confusion: dict[str, dict[str, int]] = {}

    for expected, predicted in pairs:
        confusion.setdefault(expected, {})
        confusion[expected][predicted] = confusion[expected].get(predicted, 0) + 1
        if expected == predicted:
            true_positive[predicted] += 1
        else:
            if expected in labels:
                false_negative[expected] += 1
            if predicted in labels:
                false_positive[predicted] += 1

    per_class: dict[str, CountMetric] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for label in labels:
        tp = true_positive[label]
        predicted_count = tp + false_positive[label]
        actual_count = tp + false_negative[label]
        precision = tp / predicted_count if predicted_count else None
        recall = tp / actual_count if actual_count else None
        if precision is None or recall is None or (precision + recall) == 0:
            f1 = None
        else:
            f1 = 2 * precision * recall / (precision + recall)
        per_class[label] = ratio(
            tp, predicted_count, f"{name} true positives for {label}"
        )
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        if f1 is not None:
            f1s.append(f1)

    def macro(values: list[float], definition: str) -> CountMetric:
        numerator = round(sum(values), 6)
        return CountMetric(
            numerator=len(values), denominator=len(values),
            value=(numerator / len(values)) if values else None,
            definition=definition,
        )

    return ClassificationMetrics(
        labels=labels,
        accuracy=ratio(correct, total, f"{name} correct / scored cases"),
        per_class=per_class,
        macro_precision=macro(precisions, f"unweighted mean of per-class {name} precision"),
        macro_recall=macro(recalls, f"unweighted mean of per-class {name} recall"),
        macro_f1=macro(f1s, f"unweighted mean of per-class {name} F1"),
        confusion=confusion,
    )


def action_metrics(results: list[CaseResult]) -> ClassificationMetrics:
    """Action classification over every scored case."""
    pairs = [
        (r.expected_action.value, r.predicted_action.value)
        for r in results if r.action_scored
    ]
    return classification_from_pairs(pairs, labels=ACTION_LABELS, name="action")


def parent_accuracy(results: list[CaseResult]) -> CountMetric:
    scored = [r for r in results if r.parent_scored]
    correct = sum(1 for r in scored if r.parent_correct)
    return ratio(
        correct, len(scored),
        "exact parent-set match over cases with KNOWN parent truth "
        "(multi-parent compared as a set)",
    )


#: ``none`` counts as its own predicted class: "no relation was established" is a
#: real outcome and must not be forced into a relation class.
RELATION_LABELS = ("finetune", "adapter", "merge", "quantized", "none")


def relation_metrics(results: list[CaseResult]) -> ClassificationMetrics:
    """Relation classification over cases whose relation truth is knowable."""
    pairs = [
        (
            r.expected_relation.value if r.expected_relation else "none",
            r.predicted_relation.value if r.predicted_relation else "none",
        )
        for r in results if r.relation_scored
    ]
    return classification_from_pairs(pairs, labels=RELATION_LABELS, name="relation")


def parent_accuracy_selective(results: list[CaseResult]) -> CountMetric:
    """Parent accuracy among non-abstaining predictions only.

    Reported *in addition to* the strict metric (where abstention counts as
    wrong): abstention is never counted as correct, but the coverage-conditioned
    view shows what the system does when it does answer.
    """
    scored = [r for r in results if r.parent_scored and not r.abstained]
    correct = sum(1 for r in scored if r.parent_correct)
    return ratio(
        correct, len(scored),
        "parent-set match among non-abstaining predictions with KNOWN parent truth",
    )


def relation_accuracy_selective(results: list[CaseResult]) -> CountMetric:
    """Relation accuracy among non-abstaining predictions only."""
    scored = [r for r in results if r.relation_scored and not r.abstained]
    correct = sum(1 for r in scored if r.relation_correct)
    return ratio(
        correct, len(scored),
        "relation match among non-abstaining predictions with KNOWN relation truth",
    )


def coverage(results: list[CaseResult]) -> CountMetric:
    """Non-abstaining predictions over scored cases."""
    scored = [r for r in results if r.action_scored]
    answered = [r for r in scored if not r.abstained]
    return ratio(
        len(answered), len(scored),
        "non-ABSTAIN predictions / scored cases (abstention is never counted as correct)",
    )


def repair_safety(results: list[CaseResult]) -> RepairSafetyMetrics:
    scored = [r for r in results if r.action_scored]
    attempts = [r for r in scored if r.repair_attempted]
    false_repairs = [r for r in attempts if r.false_repair is True]
    unverifiable = [r for r in attempts if r.false_repair is None]
    abstentions = [r for r in scored if r.abstained]
    return RepairSafetyMetrics(
        attempted_repairs=ratio(len(attempts), len(scored),
                                "attempted repairs (ADD or REPLACE) / scored cases"),
        false_repairs=ratio(
            len(false_repairs), len(attempts),
            "incorrect attempted repairs / attempted repairs (the false repair rate)",
        ),
        unverifiable_repairs=ratio(
            len(unverifiable), len(attempts),
            "attempted repairs whose correctness cannot be verified / attempted repairs",
        ),
        abstentions=ratio(len(abstentions), len(scored), "ABSTAIN predictions / scored cases"),
        definition=FALSE_REPAIR_DEFINITION,
    )


def compute_track_metrics(
    results: list[CaseResult], *, track: Track, system: str
) -> TrackMetrics:
    subset = [r for r in results if r.track is track]
    return TrackMetrics(
        track=track,
        system=system,
        n_cases=len(subset),
        action=action_metrics(subset),
        parent=parent_accuracy(subset),
        relation=relation_metrics(subset),
        parent_selective=parent_accuracy_selective(subset),
        relation_selective=relation_accuracy_selective(subset),
        coverage=coverage(subset),
        repair_safety=repair_safety(subset),
        extra={
            "n_scored_cases": sum(1 for r in subset if r.action_scored),
            "n_ambiguous_parent_truth": sum(
                1 for r in subset if not r.parent_scored
            ),
        },
    )


def compute_metrics(results: list[CaseResult], *, system: str) -> dict:
    """Aggregate metrics overall and per track."""
    metrics: dict = {
        "system": system,
        "n_cases": len(results),
        "action": action_metrics(results).model_dump(mode="json"),
        "parent": parent_accuracy(results).model_dump(mode="json"),
        "relation": relation_metrics(results).model_dump(mode="json"),
        "parent_selective": parent_accuracy_selective(results).model_dump(mode="json"),
        "relation_selective": relation_accuracy_selective(results).model_dump(mode="json"),
        "coverage": coverage(results).model_dump(mode="json"),
        "repair_safety": repair_safety(results).model_dump(mode="json"),
        "false_repair_definition": FALSE_REPAIR_DEFINITION,
        "by_track": {},
    }
    for track in Track:
        track_results = [r for r in results if r.track is track]
        if track_results:
            metrics["by_track"][track.value] = compute_track_metrics(
                results, track=track, system=system
            ).model_dump(mode="json")
    return metrics
