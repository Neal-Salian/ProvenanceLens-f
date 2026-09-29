"""Audit result schemas: decisions, conflicts, patches, full audit output."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence import EvidenceItem
from .lineage import DeclaredLineage, Lineage, Relation


class Decision(str, Enum):
    KEEP = "KEEP"
    ADD = "ADD"
    REPLACE = "REPLACE"
    ABSTAIN = "ABSTAIN"


class ConflictKind(str, Enum):
    DECLARED_VS_INDEPENDENT = "declared_vs_independent"
    COMPETING_CANDIDATES = "competing_candidates"
    RELATION_CONFLICT = "relation_conflict"
    VERSION_AMBIGUITY = "version_ambiguity"
    MULTIPLE_MERGE_SOURCES = "multiple_merge_sources"
    TOOL_FAILURE = "tool_failure"
    UNKNOWN_DECLARED_RELATION = "unknown_declared_relation"
    OTHER = "other"


class Conflict(BaseModel):
    """A structured conflict discovered during the audit."""

    model_config = ConfigDict(extra="forbid")

    kind: ConflictKind
    description: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class SuggestedPatch(BaseModel):
    """An optional, never-auto-applied metadata repair suggestion."""

    model_config = ConfigDict(extra="forbid")

    old_base_model: str | None = None
    new_base_model: str | None = None
    old_relation_raw: str | None = None
    new_relation: Relation | None = None

    @model_validator(mode="after")
    def _require_something_to_set(self) -> SuggestedPatch:
        if self.new_base_model is None and self.new_relation is None:
            raise ValueError("suggested patch must set new_base_model and/or new_relation")
        return self


class AuditDecision(BaseModel):
    """Full evidence-backed result of auditing one model repository."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    current_lineage: DeclaredLineage
    decision: Decision
    proposed_lineage: Lineage = Field(default_factory=Lineage)
    support_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    contradictory_evidence: list[EvidenceItem] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    reasoning_summary: str
    recommended_patch: SuggestedPatch | None = None

    @model_validator(mode="after")
    def _check_decision_consistency(self) -> AuditDecision:
        if self.decision is Decision.ABSTAIN:
            if not self.proposed_lineage.is_empty:
                raise ValueError("ABSTAIN must not propose a lineage")
            if self.recommended_patch is not None:
                raise ValueError("ABSTAIN must not recommend a patch")
        elif self.proposed_lineage.is_empty:
            raise ValueError(f"{self.decision.value} must propose a lineage")
        return self

    @classmethod
    def abstain(
        cls,
        model_id: str,
        current_lineage: DeclaredLineage,
        reasoning_summary: str,
        *,
        support_score: float = 0.0,
        conflicts: list[Conflict] | None = None,
        supporting_evidence: list[EvidenceItem] | None = None,
        contradictory_evidence: list[EvidenceItem] | None = None,
    ) -> AuditDecision:
        """Build a safe abstention result (no proposal, no patch)."""
        return cls(
            model_id=model_id,
            current_lineage=current_lineage,
            decision=Decision.ABSTAIN,
            support_score=support_score,
            supporting_evidence=supporting_evidence or [],
            contradictory_evidence=contradictory_evidence or [],
            conflicts=conflicts or [],
            reasoning_summary=reasoning_summary,
        )
