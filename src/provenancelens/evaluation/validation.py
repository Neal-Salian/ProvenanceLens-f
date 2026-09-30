"""Benchmark validation: invalid evaluation data must fail early.

The validator checks the *shape and semantics* of a benchmark only. It never
imports or calls the ProvenanceLens decision engine, so it cannot manufacture
an expected label from the system's own output; :mod:`tests.test_phase_f_benchmark`
asserts that separation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ..resolution import ResolutionStatus, resolve_identifier
from ..schemas.audit import Decision
from ..schemas.lineage import Relation
from .schema import (
    BenchmarkCase,
    LabelProvenance,
    MetadataState,
    Track,
    TruthStatus,
)

__all__ = ["Severity", "ValidationIssue", "BenchmarkValidationError", "validate_case",
           "validate_benchmark", "assert_valid_benchmark"]


class Severity(str, Enum):
    ERROR = "error"    # invalid benchmark: must be fixed
    WARNING = "warning"  # suspicious but usable; recorded, never hidden


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    code: str
    message: str
    severity: Severity = Severity.ERROR


class BenchmarkValidationError(ValueError):
    """Raised when a benchmark contains invalid evaluation data."""

    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__(
            "invalid benchmark:\n"
            + "\n".join(f"  [{i.severity.value}] {i.case_id}: {i.code}: {i.message}"
                        for i in issues)
        )


def _is_merge_case(case: BenchmarkCase) -> bool:
    parents = case.truth.parents or ()
    return len(parents) > 1 or case.truth.relation is Relation.MERGE


def validate_case(case: BenchmarkCase) -> list[ValidationIssue]:
    """Validate one case; returns issues (empty means valid)."""
    issues: list[ValidationIssue] = []

    def error(code: str, message: str) -> None:
        issues.append(ValidationIssue(
            case_id=case.case_id, code=code, message=message, severity=Severity.ERROR,
        ))

    def warning(code: str, message: str) -> None:
        issues.append(ValidationIssue(
            case_id=case.case_id, code=code, message=message, severity=Severity.WARNING,
        ))

    # --- ids and labels ---------------------------------------------------
    if not case.case_id.strip():
        error("empty_case_id", "case_id must not be empty")
    if case.expected_action is Decision.REPLACE and case.truth.metadata_state is not MetadataState.INCORRECT:
        error("replace_without_incorrect_metadata",
              "REPLACE requires adjudicated metadata_state=incorrect")
    if case.expected_action is Decision.ADD and case.truth.metadata_state is not MetadataState.MISSING:
        error("add_without_missing_metadata",
              "ADD requires adjudicated metadata_state=missing")
    if case.expected_action is Decision.KEEP and case.truth.metadata_state is MetadataState.INCORRECT:
        error("keep_with_incorrect_metadata",
              "KEEP must not be expected for known-incorrect metadata")
    if case.truth.metadata_state is MetadataState.INCORRECT and case.repairable is False:
        warning("incorrect_but_not_repairable",
                "metadata is incorrect but the case is marked unrepairable")

    # --- ambiguity must not masquerade as certainty -----------------------
    if case.truth.parents_status is TruthStatus.AMBIGUOUS and case.truth.parents is not None:
        warning("ambiguous_with_single_label",
                "ambiguous parent truth should use parent_set_alternatives")
    if (case.truth.parents_status is not TruthStatus.KNOWN
            and case.repairable
            and case.expected_action in (Decision.ADD, Decision.REPLACE)):
        error("action_on_ambiguous_truth",
              f"{case.expected_action.value} requires known parent truth; "
              f"status is {case.truth.parents_status.value}")
    if case.truth.parents_status is TruthStatus.AMBIGUOUS and not case.truth.parent_set_alternatives:
        error("ambiguous_without_alternatives",
              "AMBIGUOUS parent truth must record at least one alternative set")
    if (case.truth.relation_status is not TruthStatus.KNOWN
            and case.expected_action is Decision.ADD
            and case.truth.metadata_state is MetadataState.MISSING):
        warning("add_with_unknown_relation",
                "ADD with unknown relation truth: only the parent can be scored")

    # --- relation labels --------------------------------------------------
    if case.truth.relation is not None and case.truth.relation_status is not TruthStatus.KNOWN:
        error("relation_status_mismatch",
              "a relation label requires relation_status=known")
    declared_relation = case.declared_relation_raw
    if declared_relation is not None and declared_relation.strip():
        normalized = Relation.normalize(declared_relation)
        if normalized is None:
            warning("declared_relation_unmapped",
                    f"declared base_model_relation {declared_relation!r} is not canonical")

    # --- merge semantics --------------------------------------------------
    if case.truth.parents:
        if len(set(case.truth.parents)) != len(case.truth.parents):
            error("duplicate_parents", "expected parents must be a set (no duplicates)")
        if case.truth.relation is Relation.MERGE and len(case.truth.parents) < 2:
            warning("merge_with_single_parent",
                    "merge relation with a single expected parent")
        if case.truth.relation is not Relation.MERGE and _is_merge_case(case):
            warning("multi_parent_without_merge_relation",
                    "multiple expected parents but relation is not merge")

    # --- identifier quality ----------------------------------------------
    for parent in (case.truth.parents or ()):
        resolution = resolve_identifier(parent)
        if resolution.status is ResolutionStatus.INVALID:
            error("invalid_expected_parent",
                  f"expected parent {parent!r} is not a model reference")
        elif resolution.resolved != parent:
            warning("non_canonical_expected_parent",
                    f"expected parent {parent!r} is not canonical (resolved: "
                    f"{resolution.resolved!r})")

    # --- fixture / snapshot references ------------------------------------
    if case.track is Track.REAL:
        if case.adjudication.provenance is not LabelProvenance.MANUAL_ADJUDICATION:
            error("real_case_without_adjudication",
                  "REAL cases require manual adjudication")
        if not case.repository:
            error("real_case_without_repository", "REAL cases require a repository id")
        if not case.snapshot_commit:
            error("real_case_without_commit", "REAL cases require a snapshot commit")
        if not case.snapshot_files:
            error("real_case_without_files", "REAL cases require the frozen file set")
        if not case.adjudication.adjudicator.strip():
            error("adjudication_without_adjudicator",
                  "an adjudication must name its adjudicator")
    else:
        if case.adjudication.provenance is not LabelProvenance.SYNTHETIC_CONSTRUCTION:
            error("controlled_case_wrong_provenance",
                  "CONTROLLED cases must be labelled by construction")
        if (
            not case.evidence
            and not case.snapshot_files
            and "no-evidence" not in case.tags
        ):
            # An empty-evidence case is legitimate ("nothing was retrieved"), but
            # it must be opted into explicitly so it is never a silent omission.
            error("controlled_case_without_evidence",
                  "CONTROLLED cases need evidence (or the explicit 'no-evidence' tag)")

    if not case.truth.rationale.strip():
        error("truth_without_rationale", "every label needs a rationale")

    # --- action acceptability --------------------------------------------
    if case.expected_action not in case.acceptable_actions:
        warning("expected_action_not_acceptable",
                "expected_action should be listed among acceptable_actions")
    return issues


def validate_benchmark(
    cases: list[BenchmarkCase], *, allow_warnings: bool = True
) -> list[ValidationIssue]:
    """Validate a whole benchmark, including cross-case rules."""
    issues: list[ValidationIssue] = []
    seen: dict[str, int] = {}
    for case in cases:
        issues.extend(validate_case(case))
        seen[case.case_id] = seen.get(case.case_id, 0) + 1
    for case_id, count in seen.items():
        if count > 1:
            issues.append(ValidationIssue(
                case_id=case_id, code="duplicate_case_id",
                message=f"case id appears {count} times",
                severity=Severity.ERROR,
            ))

    errors = [i for i in issues if i.severity is Severity.ERROR]
    if errors and not allow_warnings:
        raise BenchmarkValidationError(errors)
    return issues


def assert_valid_benchmark(
    cases: list[BenchmarkCase], *, strict: bool = True
) -> list[ValidationIssue]:
    """Raise on any error; return all issues (including warnings) otherwise."""
    issues = validate_benchmark(cases)
    errors = [i for i in issues if i.severity is Severity.ERROR]
    if errors:
        raise BenchmarkValidationError(errors)
    _ = strict
    return issues


class _ValidationReport(BaseModel):  # pragma: no cover - convenience container
    issues: tuple[ValidationIssue, ...] = Field(default_factory=tuple)
