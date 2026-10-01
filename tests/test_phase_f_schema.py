"""Benchmark schema and validation rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from provenancelens.evaluation.schema import (
    Adjudication,
    BenchmarkCase,
    GroundTruth,
    LabelProvenance,
    MetadataState,
    Track,
    TruthStatus,
)
from provenancelens.evaluation.validation import (
    BenchmarkValidationError,
    assert_valid_benchmark,
    validate_benchmark,
    validate_case,
)
from provenancelens.schemas.audit import Decision
from provenancelens.schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from provenancelens.schemas.lineage import Relation

EVIDENCE_PATH = Path(__file__).resolve().parent.parent / "src" / "provenancelens" / "evaluation"


def _case(**overrides) -> BenchmarkCase:
    base = dict(
        case_id="CASE-1",
        track=Track.CONTROLLED,
        title="unit case",
        evidence=(),
        declared_base_model="org/base",
        declared_relation_raw="finetune",
        truth=GroundTruth(
            parents=("org/base",),
            parents_status=TruthStatus.KNOWN,
            relation=Relation.FINETUNE,
            relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.VALID,
            rationale="constructed",
        ),
        expected_action=Decision.KEEP,
        acceptable_actions=(Decision.KEEP,),
        adjudication=Adjudication(
            provenance=LabelProvenance.SYNTHETIC_CONSTRUCTION, adjudicator="unit test",
        ),
    )
    base.update(overrides)
    return BenchmarkCase(**base)


def _codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def test_valid_case_has_no_errors():
    case = _case(evidence=(
        EvidenceItem(
            source_type=SourceType.TRAINING_CONFIG,
            role=EvidenceRole.INDEPENDENT,
            extraction_method=ExtractionMethod.DETERMINISTIC,
            reliability=Reliability.HIGH,
            source_name="train.yaml",
            candidate_parent="org/base",
        ),
    ))
    assert _codes(validate_case(case)) == set()


def test_duplicate_case_ids_are_rejected():
    issues = validate_benchmark([_case(), _case()])
    assert "duplicate_case_id" in _codes(issues)


def test_replace_requires_incorrect_metadata():
    case = _case(expected_action=Decision.REPLACE,
                  acceptable_actions=(Decision.REPLACE,))
    assert "replace_without_incorrect_metadata" in _codes(validate_case(case))


def test_add_requires_missing_metadata():
    case = _case(expected_action=Decision.ADD, acceptable_actions=(Decision.ADD,))
    assert "add_without_missing_metadata" in _codes(validate_case(case))


def test_keep_is_rejected_for_known_wrong_declaration():
    case = _case(
        truth=GroundTruth(
            parents=("org/other",), parents_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.INCORRECT, rationale="declared is wrong",
        ),
        expected_action=Decision.KEEP,
    )
    assert "keep_with_incorrect_metadata" in _codes(validate_case(case))


def test_valid_state_without_declaration_is_rejected():
    """Found by running the benchmark: labels must describe existing metadata."""
    case = _case(declared_base_model=None, declared_relation_raw=None)
    assert "state_without_declaration" in _codes(validate_case(case))


def test_missing_state_with_declaration_is_rejected():
    case = _case(
        truth=GroundTruth(
            parents=("org/base",), parents_status=TruthStatus.KNOWN,
            relation=Relation.FINETUNE, relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.MISSING, rationale="nothing declared",
        ),
        expected_action=Decision.ADD, acceptable_actions=(Decision.ADD,),
    )
    assert "missing_but_declared" in _codes(validate_case(case))


def test_ambiguous_truth_cannot_expect_a_repair():
    case = _case(
        declared_base_model=None, declared_relation_raw=None,
        truth=GroundTruth(
            parents=("org/base",), parents_status=TruthStatus.AMBIGUOUS,
            metadata_state=MetadataState.UNDETERMINED,
            parent_set_alternatives=(("org/base",), ("org/other",)),
            rationale="two readings",
        ),
        expected_action=Decision.ADD, acceptable_actions=(Decision.ADD,),
    )
    assert "action_on_ambiguous_truth" in _codes(validate_case(case))


def test_ambiguous_truth_without_alternatives_is_rejected():
    case = _case(
        truth=GroundTruth(
            parents=None, parents_status=TruthStatus.AMBIGUOUS,
            metadata_state=MetadataState.UNDETERMINED, rationale="ambiguous",
        ),
        expected_action=Decision.ABSTAIN, acceptable_actions=(Decision.ABSTAIN,),
        declared_base_model=None, declared_relation_raw=None,
    )
    assert "ambiguous_without_alternatives" in _codes(validate_case(case))


def test_invalid_relation_label_is_rejected_by_the_schema():
    with pytest.raises(Exception):
        GroundTruth(
            parents=("org/base",), parents_status=TruthStatus.KNOWN,
            relation="distilled",  # type: ignore[arg-type]
            relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.VALID, rationale="bad label",
        )


def test_relation_label_requires_known_status():
    case = _case(
        truth=GroundTruth(
            parents=("org/base",), parents_status=TruthStatus.KNOWN,
            relation=Relation.FINETUNE, relation_status=TruthStatus.UNKNOWN,
            metadata_state=MetadataState.VALID, rationale="inconsistent",
        ),
    )
    assert "relation_status_mismatch" in _codes(validate_case(case))


def test_merge_set_semantics_are_validated():
    case = _case(
        declared_base_model="org/a", declared_relation_raw="merge",
        declared_additional_base_models=("org/b",),
        truth=GroundTruth(
            parents=("org/a", "org/a"), parents_status=TruthStatus.KNOWN,
            relation=Relation.MERGE, relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.VALID, rationale="duplicated parent",
        ),
    )
    assert "duplicate_parents" in _codes(validate_case(case))


def test_single_parent_merge_relation_is_flagged():
    case = _case(
        truth=GroundTruth(
            parents=("org/a",), parents_status=TruthStatus.KNOWN,
            relation=Relation.MERGE, relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.VALID, rationale="merge with one parent",
        ),
    )
    assert "merge_with_single_parent" in _codes(validate_case(case))


def test_invalid_expected_parent_is_rejected():
    case = _case(
        truth=GroundTruth(
            parents=("/data/checkpoints/step-1000",),
            parents_status=TruthStatus.KNOWN,
            relation=Relation.FINETUNE, relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.VALID, rationale="path is not a model id",
        ),
    )
    assert "invalid_expected_parent" in _codes(validate_case(case))


def test_real_case_requires_manual_adjudication_and_snapshot():
    case = _case(
        track=Track.REAL,
        repository="org/repo",
        adjudication=Adjudication(
            provenance=LabelProvenance.SYNTHETIC_CONSTRUCTION, adjudicator="unit",
        ),
    )
    codes = _codes(validate_case(case))
    assert {"real_case_without_adjudication", "real_case_without_commit",
            "real_case_without_files"} <= codes


def test_real_case_without_adjudicator_is_rejected():
    case = _case(
        track=Track.REAL, repository="org/repo", snapshot_commit="a" * 40,
        snapshot_files={"README.md": "# x"},
        adjudication=Adjudication(
            provenance=LabelProvenance.MANUAL_ADJUDICATION, adjudicator=" ",
        ),
    )
    assert "adjudication_without_adjudicator" in _codes(validate_case(case))


def test_controlled_case_needs_evidence_or_explicit_tag():
    case = _case()
    assert "controlled_case_without_evidence" in _codes(validate_case(case))
    assert "controlled_case_without_evidence" not in _codes(validate_case(_case(tags=("no-evidence",))))


def test_truth_requires_rationale():
    case = _case(truth=GroundTruth(
        parents=("org/base",), parents_status=TruthStatus.KNOWN,
        metadata_state=MetadataState.VALID, rationale="   ",
    ))
    assert "truth_without_rationale" in _codes(validate_case(case))


def test_assert_valid_benchmark_raises_on_errors():
    with pytest.raises(BenchmarkValidationError):
        assert_valid_benchmark([_case(), _case()])


def test_validator_never_imports_the_decision_engine():
    """No leakage: labels cannot be manufactured from the system's own output."""
    text = (EVIDENCE_PATH / "validation.py").read_text(encoding="utf-8")
    for forbidden in ("decide_lineage", "audit_repository", "aggregate_candidates",
                      "from ..reasoning", "import reasoning"):
        assert forbidden not in text, f"validation.py references {forbidden}"
    dataset_text = (EVIDENCE_PATH / "dataset.py").read_text(encoding="utf-8")
    assert "decide_lineage" not in dataset_text
    real_text = (EVIDENCE_PATH / "real.py").read_text(encoding="utf-8")
    assert "decide_lineage" not in real_text
    controlled_text = (EVIDENCE_PATH / "controlled.py").read_text(encoding="utf-8")
    assert "decide_lineage" not in controlled_text
