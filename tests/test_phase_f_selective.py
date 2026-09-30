"""Selective prediction, calibration guardrails, and extraction evaluation."""

from __future__ import annotations

import pytest

from provenancelens.evaluation.calibration import (
    MIN_CASES_FOR_FIT,
    CalibrationBlocker,
    CalibrationStatus,
    CalibratedScore,
    UncalibratedInputError,
    brier_score,
    calibration_status,
    expected_calibration_error,
)
from provenancelens.evaluation.extraction_eval import (
    ClaimLabel,
    ExtractionFixture,
    default_fixtures,
    evaluate_fixture,
    evaluate_fixtures,
)
from provenancelens.evaluation.schema import CaseResult, Track
from provenancelens.evaluation.selective import (
    DEFAULT_THRESHOLDS,
    observed_thresholds,
    selective_sweep,
    threshold_row,
)
from provenancelens.prose import ProseFailureCode
from provenancelens.schemas.audit import Decision
from provenancelens.schemas.lineage import Relation


def _result(case_id: str, predicted: Decision, support: float, *,
            expected: Decision = Decision.ADD, correct: bool = True,
            false_repair: bool | None = None) -> CaseResult:
    return CaseResult(
        case_id=case_id, track=Track.CONTROLLED, system="unit",
        expected_action=expected, acceptable_actions=(expected,),
        predicted_action=predicted, support_score=support,
        abstained=predicted is Decision.ABSTAIN,
        repair_attempted=predicted in (Decision.ADD, Decision.REPLACE),
        action_scored=True, action_correct=correct,
        repair_verifiable=False, repair_correct=None, false_repair=false_repair,
    )


# --- selective prediction ---------------------------------------------------


def test_threshold_row_computes_coverage_and_selective_accuracy():
    results = [
        _result("a", Decision.ADD, 0.90),
        _result("b", Decision.ADD, 0.40, correct=False),
        _result("c", Decision.ABSTAIN, 0.80),
    ]
    row = threshold_row(results, 0.5)
    assert row.accepted == 1 and row.coverage == pytest.approx(1 / 3)
    assert row.selective_accuracy == pytest.approx(1.0)
    assert row.abstentions == 1


def test_coverage_decreases_as_the_threshold_rises():
    results = [_result(f"c{i}", Decision.ADD, score) for i, score in
               enumerate([0.2, 0.5, 0.8, 0.95])]
    by_threshold = {
        point.threshold: point for point in selective_sweep(results, thresholds=[0.0, 0.5, 0.9])
    }
    assert by_threshold[0.0].accepted == 4
    assert by_threshold[0.5].accepted == 3   # scores 0.5, 0.8, 0.95
    assert by_threshold[0.9].accepted == 1   # only 0.95 clears 0.9


def test_abstentions_are_never_accepted_regardless_of_support_score():
    results = [_result("a", Decision.ABSTAIN, 1.0)]
    row = threshold_row(results, 0.0)
    assert row.accepted == 0 and row.coverage == 0.0
    assert row.selective_accuracy is None  # nothing accepted: no credit


def test_sweep_includes_observed_scores_and_default_grid():
    results = [_result("a", Decision.ADD, 0.37)]
    thresholds = [point.threshold for point in selective_sweep(results)]
    assert 0.37 in thresholds
    for value in DEFAULT_THRESHOLDS:
        assert value in thresholds


def test_false_repair_columns_track_the_threshold():
    results = [
        _result("safe", Decision.ADD, 0.95, false_repair=False),
        _result("risky", Decision.REPLACE, 0.60, expected=Decision.REPLACE,
                correct=False, false_repair=True),
    ]
    low = threshold_row(results, 0.0)
    high = threshold_row(results, 0.9)
    assert low.false_repairs == 1 and low.false_repair_rate == pytest.approx(0.5)
    assert high.accepted == 1 and high.false_repairs == 0


def test_observed_thresholds_are_sorted_and_unique():
    results = [_result("a", Decision.ADD, 0.5), _result("b", Decision.ADD, 0.5),
               _result("c", Decision.ADD, 0.1)]
    assert observed_thresholds(results) == [0.1, 0.5]


def test_empty_results_give_undefined_not_zero():
    row = threshold_row([], 0.0)
    assert row.coverage is None and row.selective_accuracy is None
    assert row.false_repair_rate is None


# --- calibration guardrails -------------------------------------------------


def test_ece_and_brier_math_on_a_perfectly_calibrated_set():
    """A calibrated predictor emits the observed frequency (0 or 1 here)."""
    probabilities = [0.0] * 10 + [1.0] * 10
    outcomes = [0] * 10 + [1] * 10
    assert expected_calibration_error(probabilities, outcomes, n_bins=10) == pytest.approx(0.0)
    assert brier_score(probabilities, outcomes) == pytest.approx(0.0)


def test_ece_detects_overconfidence():
    """Predicting 0.9 when the outcome is always 0 is 0.9 miscalibrated."""
    assert expected_calibration_error([0.9] * 10, [0] * 10) == pytest.approx(0.9)
    assert expected_calibration_error([0.1] * 10, [1] * 10) == pytest.approx(0.9)


def test_calibration_metrics_reject_bad_inputs():
    with pytest.raises(ValueError):
        expected_calibration_error([0.5], [1, 0])
    with pytest.raises(ValueError):
        expected_calibration_error([], [])
    with pytest.raises(UncalibratedInputError):
        brier_score([1.5], [1])


def test_calibration_status_refuses_to_report_raw_support_scores():
    results = [_result(f"c{i}", Decision.ADD, 0.9) for i in range(3)]
    status = calibration_status(results)
    assert status.status is CalibrationStatus.DEFERRED
    assert CalibrationBlocker.RAW_SCORE_IS_NOT_A_PROBABILITY in status.blockers
    assert CalibrationBlocker.INSUFFICIENT_CASES in status.blockers
    assert CalibrationBlocker.NO_HELD_OUT_SPLIT in status.blockers
    assert "not a probability" in status.statement
    assert MIN_CASES_FOR_FIT == 50


def test_calibrated_scores_require_a_fitted_mapping():
    results = [_result(f"c{i}", Decision.ADD, 0.9) for i in range(60)]
    calibrated = [
        CalibratedScore(case_id=r.case_id, probability=0.8, mapping_id="isotonic-v1",
                        fitted_on=False)
        for r in results
    ]
    status = calibration_status(results, calibrated=calibrated, has_held_out_split=True)
    assert status.status is CalibrationStatus.AVAILABLE
    assert expected_calibration_error([s.probability for s in calibrated],
                                      [1] * len(calibrated)) == pytest.approx(0.2)


# --- extraction evaluation --------------------------------------------------


def test_default_fixtures_are_frozen_and_labelled():
    fixtures = default_fixtures()
    assert len(fixtures) == 11
    assert len({f.fixture_id for f in fixtures}) == len(fixtures)
    assert any(f.expected_claims for f in fixtures)
    assert any(f.expected_rejections for f in fixtures)


def test_explicit_claim_fixture_is_extracted():
    fixture = next(f for f in default_fixtures() if f.fixture_id.endswith("explicit-adapter"))
    metrics, report = evaluate_fixture(fixture)
    assert metrics.claim_precision.value == 1.0
    assert metrics.claim_recall.value == 1.0
    assert report.evidence[0].relation is Relation.ADAPTER


def test_rejection_fixtures_reject_with_the_expected_reason():
    fixture = next(f for f in default_fixtures() if f.fixture_id.endswith("injection"))
    metrics, report = evaluate_fixture(fixture)
    assert report.evidence == []
    assert ProseFailureCode.INJECTION_DETECTED.value in metrics.rejections_by_code
    assert metrics.rejection_accuracy.value == 1.0


def test_relation_downgrade_fixture_keeps_parent_without_relation():
    fixture = next(f for f in default_fixtures() if f.fixture_id.endswith("unstated-relation"))
    metrics, report = evaluate_fixture(fixture)
    assert metrics.claim_recall.value == 1.0
    assert report.evidence[0].candidate_parent == "org/model-x"
    assert report.evidence[0].relation is None


def test_ambiguous_fixture_keeps_the_bare_name_unresolved():
    fixture = next(f for f in default_fixtures() if f.fixture_id.endswith("bare-name"))
    _metrics, report = evaluate_fixture(fixture)
    assert report.evidence[0].candidate_parent == "Mistral 7B"
    assert "resolution=ambiguous" in (report.evidence[0].note or "")


def test_aggregate_extraction_metrics_are_exact():
    metrics = evaluate_fixtures(default_fixtures())
    assert metrics.n_fixtures == 11
    # every labelled claim is recovered, and nothing extra is accepted
    assert metrics.false_positives == 0
    assert metrics.claim_precision.value == 1.0
    assert metrics.claim_recall.value == 1.0
    assert metrics.rejection_accuracy.value == 1.0
    # five fixtures expect a rejection, one failure each
    assert sum(metrics.rejections_by_code.values()) == 5


def test_extraction_metrics_count_a_missed_claim_as_false_negative():
    fixture = ExtractionFixture(
        fixture_id="EXTRACT-XX-missed",
        prose="# Card\n\n## Training\n\nThis model was fine-tuned from org/base-model.\n",
        model_output='{"claims": []}',
        expected_claims=(ClaimLabel(candidate_parent="org/base-model",
                                    relation=Relation.FINETUNE),),
    )
    metrics, _report = evaluate_fixture(fixture)
    assert metrics.false_negatives == 1
    assert metrics.claim_recall.value == 0.0
