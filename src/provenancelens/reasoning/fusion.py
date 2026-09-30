"""Reliability-aware, deterministic evidence fusion.

``support_score`` summarizes *heuristic* evidence strength. It is NOT a
probability, NOT calibrated, and NOT "90% chance the repair is correct": a
score of 0.90 means "the evidence we can see is strong by our documented
rubric", nothing more. Empirical calibration can later map evidence-strength
features onto a probability without rewriting the decision pipeline, because
everything the rubric consumes is exposed here (per-item weight, explicitness,
source kinds, control domains, relation completeness).

The rubric is intentionally small enough to defend line by line:

* one explicit evidence file is a *bounded* contribution (weight table below),
* repeated records of the same file add at most one file's worth of support,
* a hypothesis' support is the capped sum of its per-file contributions,
* the relation must additionally be complete before it can travel with a
  proposal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.evidence import Explicitness, Reliability, SourceType
from ..schemas.lineage import Lineage, LineageEntry, Relation
from .candidates import (
    CandidateHypothesis,
    CandidateMethod,
    ControlDomain,
    EvidenceCluster,
)

__all__ = [
    "ITEM_WEIGHTS",
    "DecisionPolicy",
    "DEFAULT_POLICY",
    "SupportAssessment",
    "LineagePlan",
    "compute_support",
]


# Heuristic per-item contributions by reliability tier. Not probabilities:
# they encode "how much does one explicit record of this kind mean on a
# 0..1 support scale", where 1.0 means "a single, maximally strong,
# tool-generated record plus corroboration".
ITEM_WEIGHTS: dict[Reliability, float] = {
    Reliability.VERY_HIGH: 0.75,
    Reliability.HIGH: 0.55,
    Reliability.MEDIUM_HIGH: 0.45,
    Reliability.MEDIUM: 0.30,
    Reliability.WEAK: 0.12,
    Reliability.NOT_APPLICABLE: 0.0,  # declared metadata never supports itself
}

# Reliability tiers strong enough to identify a direct parent on their own.
# MEDIUM (config hints) and WEAK (indirect hints) are excluded on purpose.
PARENT_IDENTIFYING_TIERS: frozenset[Reliability] = frozenset({
    Reliability.VERY_HIGH, Reliability.HIGH, Reliability.MEDIUM_HIGH,
})

# How much a *corroborating* hint may add once explicit evidence has already
# identified the lineage. A hint (config bookkeeping, author prose) confirms a
# claim identified elsewhere; it must never outweigh an explicit artifact.
# 1.0 = hints count fully (plain sum), 0.0 = hints ignored.
CORROBORATION_DISCOUNT = 0.5


class DecisionPolicy(BaseModel):
    """Named policy thresholds (heuristic, deliberately few and documented)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_support_keep: float
    min_support_add: float
    min_support_replace: float
    min_support_affirmative: float   # KEEP or ADD is defensible at all
    min_support_decisive: float      # strong enough to *change* declared metadata
    require_complete_merge_sources: bool = True
    forbid_replace_on_author_controlled_only: bool = True


# Justification of the default values (see README "Decision thresholds").
# The scale is: one explicit VERY_HIGH artifact (adapter_config parent) = 0.75,
# one explicit HIGH artifact (merge/training config) = 0.55, one explicit
# MEDIUM artifact (config hint) = 0.30, one WEAK hint = 0.12, and support for a
# hypothesis is the capped sum of per-(file, reliability) contributions.
DEFAULT_POLICY = DecisionPolicy(
    # Accepting existing metadata or adding it needs real independent support:
    # exactly one explicit HIGH artifact, or a MEDIUM artifact plus a hint.
    min_support_keep=0.55,
    min_support_add=0.55,
    # Changing existing metadata is the highest-risk action, so it needs a
    # strictly higher bar than 0.75: no single source can reach it, and reaching
    # it requires corroboration of a tool-generated record.
    min_support_replace=0.90,
    min_support_affirmative=0.55,  # "an affirmative finding exists at all"
    min_support_decisive=0.90,     # "strong enough to change declared metadata"
)


class SupportAssessment(BaseModel):
    """Explained support score for one candidate hypothesis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    support: float
    declared_agreement: bool = False
    relation: Relation | None = None
    relation_support: float = 0.0
    relation_complete: bool = False
    parent_identifying: bool = False
    author_controlled_only: bool = False
    tool_kinds: tuple[SourceType, ...] = ()
    contributing_files: tuple[str, ...] = ()
    completeness: str = ""

    def meets(self, threshold: float) -> bool:
        return self.support >= threshold


class LineagePlan(BaseModel):
    """The lineage a candidate proposes (used as ``proposed_lineage``)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    method: CandidateMethod
    entries: tuple[LineageEntry, ...]
    relation: Relation | None
    support: SupportAssessment

    @classmethod
    def single(
        cls, parent: str, relation: Relation | None, support: SupportAssessment
    ) -> LineagePlan:
        return cls(
            method=CandidateMethod.SINGLE,
            entries=(LineageEntry(parent=parent, relation=relation),),
            relation=relation,
            support=support,
        )

    @classmethod
    def merge(
        cls,
        entries: tuple[LineageEntry, ...],
        support: SupportAssessment,
    ) -> LineagePlan:
        return cls(
            method=CandidateMethod.MERGE,
            entries=tuple(entries),
            relation=support.relation,
            support=support,
        )

    def to_lineage(self) -> Lineage:
        return Lineage(entries=list(self.entries))


def _file_contributions(clusters: list[EvidenceCluster]) -> tuple[list[float], list[float]]:
    """Per-(file, reliability) contributions, split into identifying and hints.

    Keeping the "several records are not several sources" rule explicit: the
    same file contributes at most once per reliability tier, so three fields of
    one training config cannot outvote one explicit artifact.
    """
    best: dict[tuple[str, Reliability], float] = {}
    for cluster in clusters:
        for item in cluster.items:
            key = (item.source_name or item.source_type.value, item.reliability)
            value = ITEM_WEIGHTS.get(item.reliability, 0.0) * (
                1.0 if item.explicitness is Explicitness.EXPLICIT else 0.5
            )
            best[key] = max(best.get(key, 0.0), value)
    identifying: list[float] = []
    hints: list[float] = []
    for key in sorted(best, key=lambda k: (k[0], k[1].value)):
        if key[1] in PARENT_IDENTIFYING_TIERS:
            identifying.append(best[key])
        else:
            hints.append(best[key])
    return identifying, hints


def compute_support(
    candidate: CandidateHypothesis,
    declared_parents: frozenset[str] = frozenset(),
    *,
    policy: DecisionPolicy = DEFAULT_POLICY,
) -> SupportAssessment:
    """Fuse a candidate's evidence into an explained support score."""
    clusters = list(candidate.clusters)
    identifying, hints = _file_contributions(clusters)
    identifying_total = min(1.0, sum(identifying))
    if identifying_total == 0.0:
        # Only hints exist: report them as-is, they simply never identify a parent.
        support = min(1.0, sum(hints))
    else:
        support = min(
            1.0, identifying_total + CORROBORATION_DISCOUNT * sum(hints)
        )

    relation = candidate.relation
    relation_complete = bool(
        relation is not None
        and clusters
        and all(c.relations and relation in c.relations for c in clusters)
    )
    relation_support = min(
        1.0,
        sum(
            c.weight for c in clusters
            if relation is not None and relation in (c.relations or ())
        ),
    )

    parent_identifying = any(
        any(
            item.reliability in PARENT_IDENTIFYING_TIERS
            and item.explicitness is Explicitness.EXPLICIT
            for item in cluster.items
        )
        for cluster in clusters
    )
    author_controlled_only = bool(clusters) and all(
        ControlDomain.AUTHOR_CONTROLLED in cluster.control_domains
        and ControlDomain.TOOL_GENERATED not in cluster.control_domains
        for cluster in clusters
    )
    tool_kinds = tuple(sorted(
        {kind for cluster in clusters for kind in cluster.tool_generated_kinds},
        key=lambda k: k.value,
    ))
    files = tuple(sorted({f for cluster in clusters for f in cluster.source_files}))
    declared_agreement = bool(
        declared_parents and set(candidate.parents) == set(declared_parents)
    )
    _ = policy  # thresholds are consumed by the decision engine, not here

    return SupportAssessment(
        support=round(support, 4),
        declared_agreement=declared_agreement,
        relation=relation,
        relation_support=round(relation_support, 4),
        relation_complete=relation_complete,
        parent_identifying=parent_identifying,
        author_controlled_only=author_controlled_only,
        tool_kinds=tool_kinds,
        contributing_files=files,
        completeness=candidate.completeness,
    )
