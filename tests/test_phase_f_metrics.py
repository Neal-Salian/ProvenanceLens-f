"""Metric correctness: scoring semantics, false repairs, denominators."""

from __future__ import annotations

import pytest

from provenancelens.evaluation.metrics import (
    action_metrics,
    classification_from_pairs,
    compute_metrics,
    coverage,
    parent_accuracy,
    parent_accuracy_selective,
    ratio,
    relation_metrics,
    repair_safety,
)
from provenancelens.evaluation.schema import CaseResult, Track
from provenancelens.schemas.audit import Decision
from provenancelens.schemas.lineage import Relation


def _result(
    case_id: str,
    expected: Decision,
    predicted: Decision,
    *,
    track: Track = Track.CONTROLLED,
    expected_parents: tuple[str, ...] | None = None,
    predicted_parents: tuple[str, ...] = (),
    parent_scored: bool = False,
    parent_correct: bool | None = None,
    expected_relation: Relation | None = None,
    predicted_relation: Relation | None = None,
    relation_scored: bool = False,
    relation_correct: bool | None = None,
    support: float = 0.5,
    repair_attempted: bool | None = None,
    false_repair: bool | None = None,
) -> CaseResult:
    attempted = (
        predicted in (Decision.ADD, Decision.REPLACE) if repair_attempted is None
        else repair_attempted
    )
    return CaseResult(
        case_id=case_id,
        track=track,
        system="unit",
        expected_action=expected,
        acceptable_actions=(expected,),
        predicted_action=predicted,
        expected_parents=expected_parents,
        predicted_parents=predicted_parents,
        expected_relation=expected_relation,
        predicted_relation=predicted_relation,
        support_score=support,
        abstained=predicted is Decision.ABSTAIN,
        repair_attempted=attempted,
        action_scored=True,
        action_correct=expected is predicted,
        parent_scored=parent_scored,
        parent_correct=parent_correct,
        relation_scored=relation_scored,
        relation_correct=relation_correct,
        repair_verifiable=attempted and parent_scored,
        repair_correct=(parent_correct if (attempted and parent_scored) else None),
        false_repair=false_repair,
    )


# --- ratio semantics --------------------------------------------------------


def test_ratio_uses_none_for_zero_denominator():
    metric = ratio(0, 0, "empty")
    assert metric.value is None and metric.denominator == 0


def test_ratio_reports_explicit_denominator():
    metric = ratio(1, 4, "quarter")
    assert metric.value == pytest.approx(0.25) and metric.denominator == 4


# --- action metrics ---------------------------------------------------------


def test_action_accuracy_and_confusion():
    results = [
        _result("a", Decision.KEEP, Decision.KEEP),
        _result("b", Decision.ADD, Decision.ADD),
        _result("c", Decision.ABSTAIN, Decision.REPLACE),
    ]
    metrics = action_metrics(results)
    assert metrics.accuracy.numerator == 2 and metrics.accuracy.denominator == 3
    assert metrics.confusion["ABSTAIN"] == {"REPLACE": 1}


def test_macro_f1_is_the_unweighted_mean():
    metrics = classification_from_pairs(
        [("x", "x"), ("y", "x"), ("z", "z")], labels=("x", "y", "z"), name="toy"
    )
    # x: P=1/2 R=1/1 F1=2/3 ; y: no predictions -> undefined, excluded
    # z: P=1 R=1 F1=1
    assert metrics.macro_f1.denominator == 2
    assert metrics.macro_f1.value == pytest.approx((2 / 3 + 1) / 2)


def test_macro_is_none_when_nothing_is_defined():
    metrics = classification_from_pairs([], labels=("x",), name="empty")
    assert metrics.macro_f1.value is None
    assert metrics.accuracy.value is None


# --- parent metrics ---------------------------------------------------------


def test_parent_accuracy_only_counts_knowable_cases():
    results = [
        _result("a", Decision.KEEP, Decision.KEEP, parent_scored=True, parent_correct=True),
        _result("b", Decision.KEEP, Decision.KEEP, parent_scored=False, parent_correct=None),
        _result("c", Decision.REPLACE, Decision.REPLACE, parent_scored=True, parent_correct=False),
    ]
    metric = parent_accuracy(results)
    assert (metric.numerator, metric.denominator) == (1, 2)


def test_parent_selective_excludes_abstentions():
    results = [
        _result("a", Decision.KEEP, Decision.KEEP, parent_scored=True, parent_correct=True),
        _result("b", Decision.KEEP, Decision.ABSTAIN, parent_scored=True, parent_correct=False),
    ]
    assert parent_accuracy(results).denominator == 2   # strict: abstention is wrong
    assert parent_accuracy_selective(results).denominator == 1  # coverage-conditioned


def test_coverage_counts_non_abstaining_predictions():
    results = [
        _result("a", Decision.KEEP, Decision.KEEP),
        _result("b", Decision.KEEP, Decision.ABSTAIN),
        _result("c", Decision.ADD, Decision.ADD),
    ]
    metric = coverage(results)
    assert (metric.numerator, metric.denominator) == (2, 3)


# --- relation metrics -------------------------------------------------------


def test_relation_none_is_its_own_predicted_class():
    results = [
        _result("a", Decision.ADD, Decision.ADD, expected_relation=Relation.FINETUNE,
                predicted_relation=Relation.FINETUNE, relation_scored=True,
                relation_correct=True),
        _result("b", Decision.ABSTAIN, Decision.ABSTAIN, expected_relation=Relation.MERGE,
                predicted_relation=None, relation_scored=True, relation_correct=False),
    ]
    metrics = relation_metrics(results)
    assert metrics.accuracy.numerator == 1 and metrics.accuracy.denominator == 2
    assert metrics.confusion["merge"] == {"none": 1}


def test_relation_metrics_use_relation_labels_not_actions():
    """A guard against the earlier bug: the confusion matrix must be about relations."""
    results = [
        _result("a", Decision.ABSTAIN, Decision.ADD, expected_relation=Relation.ADAPTER,
                predicted_relation=Relation.ADAPTER, relation_scored=True,
                relation_correct=True),
    ]
    metrics = relation_metrics(results)
    assert metrics.accuracy.numerator == 1
    assert metrics.confusion == {"adapter": {"adapter": 1}}


# --- repair safety ----------------------------------------------------------


def test_false_repair_rate_definition_and_denominator():
    results = [
        _result("good", Decision.ADD, Decision.ADD, parent_scored=True, parent_correct=True,
                false_repair=False),
        _result("bad", Decision.REPLACE, Decision.REPLACE, parent_scored=True,
                parent_correct=False, false_repair=True),
        _result("unverifiable", Decision.ADD, Decision.ADD, parent_scored=False,
                false_repair=None),
    ]
    metrics = repair_safety(results)
    assert metrics.false_repairs.numerator == 1
    assert metrics.false_repairs.denominator == 3  # all attempts
    assert metrics.false_repairs.value == pytest.approx(1 / 3)
    assert metrics.unverifiable_repairs.numerator == 1
    assert "incorrect attempted repairs" in metrics.definition
    assert "total attempted repairs" in metrics.definition


def test_zero_attempted_repairs_gives_none_not_zero():
    results = [_result("a", Decision.KEEP, Decision.KEEP)]
    metrics = repair_safety(results)
    assert metrics.false_repairs.denominator == 0
    assert metrics.false_repairs.value is None


def test_all_abstain_system_scores_conservatively():
    results = [
        _result(f"c{i}", Decision.ADD, Decision.ABSTAIN, expected_parents=("org/x",),
                parent_scored=True, parent_correct=False)
        for i in range(4)
    ]
    action = action_metrics(results)
    assert action.accuracy.numerator == 0
    assert parent_accuracy(results).value == 0.0
    assert coverage(results).value == 0.0
    assert repair_safety(results).false_repairs.value is None  # no repairs attempted


def test_no_abstain_system_is_scored_on_every_case():
    results = [
        _result(f"c{i}", Decision.ADD, Decision.ADD, expected_parents=("org/x",),
                predicted_parents=("org/x",), parent_scored=True, parent_correct=True,
                false_repair=False)
        for i in range(3)
    ]
    assert action_metrics(results).accuracy.value == 1.0
    assert coverage(results).value == 1.0
    assert repair_safety(results).false_repairs.value == 0.0


def test_compute_metrics_reports_per_track():
    results = [
        _result("c1", Decision.KEEP, Decision.KEEP, track=Track.CONTROLLED),
        _result("r1", Decision.ADD, Decision.ADD, track=Track.REAL),
    ]
    metrics = compute_metrics(results, system="unit")
    assert metrics["by_track"]["controlled"]["n_cases"] == 1
    assert metrics["by_track"]["real"]["n_cases"] == 1
    assert metrics["n_cases"] == 2
    assert "false_repair_rate" in metrics["false_repair_definition"]
