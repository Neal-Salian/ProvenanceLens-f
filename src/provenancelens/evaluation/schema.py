"""Strongly typed benchmark schema for LineageRepairBench.

Design rules that keep the evaluation honest:

* **Tracks are never mixed.** ``CONTROLLED`` cases are synthetic and labelled by
  construction; ``REAL`` cases are adjudicated from frozen repository evidence.
  The provenance of every label is recorded explicitly.
* **Ambiguity is a first-class label state.** Ground truth distinguishes
  ``KNOWN`` / ``AMBIGUOUS`` / ``UNKNOWN`` for parents and relations, so an
  unknowable case is never silently scored as a wrong prediction.
* **Labels are not the system's own output.** Nothing in this module (or in
  :mod:`provenancelens.evaluation.validation`) calls the decision engine; the
  label provenance field makes the source of each label auditable.
* **Raw support score stays a heuristic strength.** It is never typed as a
  probability; calibrated scores are a separate, explicitly opt-in concept
  (see :mod:`provenancelens.evaluation.calibration`).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.audit import Conflict, Decision
from ..schemas.evidence import EvidenceItem
from ..schemas.lineage import Relation

__all__ = [
    "BENCHMARK_VERSION",
    "Track",
    "TruthStatus",
    "MetadataState",
    "LabelProvenance",
    "GroundTruth",
    "Adjudication",
    "BenchmarkCase",
    "CaseResult",
    "BenchmarkRun",
    "CountMetric",
    "ClassificationMetrics",
    "RepairSafetyMetrics",
    "TrackMetrics",
]

#: Bump when case definitions or label semantics change.
BENCHMARK_VERSION = "1.0"


class Track(str, Enum):
    """Which kind of evidence/labelling a case uses."""

    CONTROLLED = "controlled"  # synthetic evidence, labelled by construction
    REAL = "real"              # frozen repository snapshot, manually adjudicated


class TruthStatus(str, Enum):
    """How confidently ground truth is known for one field."""

    KNOWN = "known"
    AMBIGUOUS = "ambiguous"  # defensible alternatives exist
    UNKNOWN = "unknown"      # not establishable from the available evidence


class MetadataState(str, Enum):
    """Condition of the declared metadata relative to adjudicated truth."""

    VALID = "valid"            # declared lineage matches truth
    MISSING = "missing"        # no direct lineage declared at all
    INCOMPLETE = "incomplete"  # parent declared, relation missing or undeclared
    INCORRECT = "incorrect"    # declared lineage contradicts truth
    UNDETERMINED = "undetermined"  # cannot be classified from the evidence


class LabelProvenance(str, Enum):
    """Where a label came from (never: "the system's own output")."""

    SYNTHETIC_CONSTRUCTION = "synthetic_construction"
    MANUAL_ADJUDICATION = "manual_adjudication"


class GroundTruth(BaseModel):
    """Adjudicated truth for one case, with explicit certainty."""

    model_config = ConfigDict(extra="forbid")

    parents: tuple[str, ...] | None = None
    parents_status: TruthStatus = TruthStatus.UNKNOWN
    relation: Relation | None = None
    relation_status: TruthStatus = TruthStatus.UNKNOWN
    metadata_state: MetadataState = MetadataState.UNDETERMINED
    #: Alternative parent sets when ``parents_status`` is AMBIGUOUS.
    parent_set_alternatives: tuple[tuple[str, ...], ...] = ()
    rationale: str

    @property
    def parents_knowable(self) -> bool:
        return self.parents_status is TruthStatus.KNOWN and self.parents is not None


class Adjudication(BaseModel):
    """Audit trail for one label (required for REAL cases)."""

    model_config = ConfigDict(extra="forbid")

    provenance: LabelProvenance
    adjudicator: str
    evidence_used: tuple[str, ...] = ()
    evidence_excerpt: str | None = None
    notes: str = ""


class BenchmarkCase(BaseModel):
    """One evaluation case: evidence in, adjudicated truth attached."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    track: Track
    title: str
    repository: str | None = None
    snapshot_commit: str | None = None
    #: Frozen artifact contents the case is built from (REAL track).
    snapshot_files: dict[str, str] | None = None
    #: Explicit structured evidence (CONTROLLED track, and injected evidence).
    evidence: tuple[EvidenceItem, ...] = ()
    #: Structured extraction issues that model tool/parser failures.
    issues: tuple[dict[str, Any], ...] = ()
    declared_base_model: str | None = None
    declared_relation_raw: str | None = None
    declared_additional_base_models: tuple[str, ...] = ()
    truth: GroundTruth
    expected_action: Decision
    #: Additional actions accepted when the case is genuinely ambiguous.
    acceptable_actions: tuple[Decision, ...] = ()
    adjudication: Adjudication
    repairable: bool = True
    tags: tuple[str, ...] = ()


class CaseResult(BaseModel):
    """Per-case evaluation output (what the runner records)."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    track: Track
    system: str
    expected_action: Decision
    acceptable_actions: tuple[Decision, ...] = ()
    predicted_action: Decision
    expected_parents: tuple[str, ...] | None = None
    predicted_parents: tuple[str, ...] = ()
    expected_relation: Relation | None = None
    predicted_relation: Relation | None = None
    #: Raw heuristic evidence strength, 0..1. NOT a probability.
    support_score: float = 0.0
    conflicts: tuple[Conflict, ...] = ()
    abstained: bool = False
    repair_attempted: bool = False
    action_scored: bool = False
    action_correct: bool | None = None
    parent_scored: bool = False
    parent_correct: bool | None = None
    relation_scored: bool = False
    relation_correct: bool | None = None
    repair_verifiable: bool = False
    repair_correct: bool | None = None
    false_repair: bool | None = None
    reasoning_summary: str = ""
    notes: str = ""


class BenchmarkRun(BaseModel):
    """Aggregate output of one evaluation run (one system, one suite)."""

    model_config = ConfigDict(extra="forbid")

    benchmark_version: str = BENCHMARK_VERSION
    system: str
    suite: str
    cases: tuple[CaseResult, ...] = ()
    metrics: dict[str, Any] = Field(default_factory=dict)
    extraction: dict[str, Any] | None = None
    #: Run provenance: package/benchmark version, label summary, LLM usage.
    provenance: dict[str, Any] = Field(default_factory=dict)


# --- metric containers (denominators are explicit by design) ----------------


class CountMetric(BaseModel):
    """A ratio with its denominator always visible."""

    model_config = ConfigDict(extra="forbid")

    numerator: int
    denominator: int
    value: float | None = None  # None when the denominator is zero (never 0.0)
    definition: str = ""


class ClassificationMetrics(BaseModel):
    """Accuracy plus per-class precision/recall/F1."""

    model_config = ConfigDict(extra="forbid")

    labels: tuple[str, ...]
    accuracy: CountMetric
    per_class: dict[str, CountMetric]
    macro_precision: CountMetric
    macro_recall: CountMetric
    macro_f1: CountMetric
    confusion: dict[str, dict[str, int]] = Field(default_factory=dict)


class RepairSafetyMetrics(BaseModel):
    """Repair safety with explicit denominators."""

    model_config = ConfigDict(extra="forbid")

    attempted_repairs: CountMetric
    false_repairs: CountMetric
    unverifiable_repairs: CountMetric
    abstentions: CountMetric
    definition: str


class TrackMetrics(BaseModel):
    """Metrics for one track of one system."""

    model_config = ConfigDict(extra="forbid")

    track: Track
    system: str
    n_cases: int
    action: ClassificationMetrics | None = None
    parent: CountMetric | None = None
    relation: ClassificationMetrics | None = None
    #: Coverage-conditioned views (abstention still never counts as correct).
    parent_selective: CountMetric | None = None
    relation_selective: CountMetric | None = None
    coverage: CountMetric | None = None
    repair_safety: RepairSafetyMetrics | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
