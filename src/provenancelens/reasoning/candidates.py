"""Candidate lineage hypotheses aggregated from independent evidence.

Aggregation converts independent :class:`EvidenceItem` objects into
*hypotheses* without discarding the originals: every hypothesis keeps the
exact evidence items that support it, the source files and source kinds they
came from, and the raw identifiers encountered.

Three properties matter as much as the grouping itself:

1. **Declared evidence never enters this layer.** Items with
   ``role=DECLARED`` are the audit *subject*; counting them here would let
   declared metadata prove itself.
2. **Several records are not several sources.** Evidence is grouped by
   independent *source* (physical file plus control domain), so three fields
   of one training config count as one source. Source-kind and control-domain
   metadata stay on the hypothesis so the decision layer can tell an
   author-written note from a tool-generated artifact.
3. **One hypothesis per hypothesis.** Each distinct parent becomes its own
   single-parent hypothesis, so rival parents compete visibly instead of being
   silently reduced to a winner. Merge lineage is a separate hypothesis made
   of ordered source slots, never collapsed into one arbitrary parent.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ..resolution import ModelResolution, ResolutionStatus, resolve_identifier
from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    Reliability,
    SourceType,
)
from ..schemas.extraction import ExtractionIssue
from ..schemas.lineage import Relation

__all__ = [
    "ControlDomain",
    "CandidateMethod",
    "EvidenceCluster",
    "CandidateHypothesis",
    "CandidateSet",
    "control_domain",
    "aggregate_candidates",
]


class ControlDomain(str, Enum):
    """Who authored the evidence — the basis for source independence.

    ``AUTHOR_CONTROLLED`` artifacts are prose or specifications written by the
    repository owner. ``TOOL_GENERATED`` artifacts are produced by the
    training/adapter/merge toolchain and therefore record an actual run rather
    than a claim about one. ``SYSTEM_WRITE`` marks files written by the
    framework itself (e.g. ``config.json``), which record bookkeeping rather
    than lineage intent.
    """

    AUTHOR_CONTROLLED = "author_controlled"
    TOOL_GENERATED = "tool_generated"
    SYSTEM_WRITE = "system_write"


class CandidateMethod(str, Enum):
    SINGLE = "single"    # one direct parent
    MERGE = "merge"      # a set of merge source slots


# Source kinds written by the model author (claims) vs written by tooling.
_AUTHOR_CONTROLLED_KINDS = frozenset({
    SourceType.DECLARED_METADATA,
    SourceType.README,
    SourceType.OTHER,
})
_SYSTEM_WRITE_KINDS = frozenset({SourceType.CONFIG})
_TOOL_GENERATED_KINDS = frozenset({
    SourceType.ADAPTER_CONFIG,
    SourceType.MERGE_CONFIG,
    SourceType.TRAINING_CONFIG,
})


def control_domain(item: EvidenceItem) -> ControlDomain:
    if item.source_type in _AUTHOR_CONTROLLED_KINDS:
        return ControlDomain.AUTHOR_CONTROLLED
    if item.source_type in _SYSTEM_WRITE_KINDS:
        return ControlDomain.SYSTEM_WRITE
    return ControlDomain.TOOL_GENERATED


def _source_key(item: EvidenceItem) -> str:
    return item.source_name or f"<{item.source_type.value}>"


def _is_evidence_file(item: EvidenceItem) -> bool:
    """Only repository artifacts are evidence; system descriptions are not."""
    return item.source_type is not SourceType.OTHER


def _slot_of(item: EvidenceItem) -> str | None:
    """Merge source slot identifier for a merge-config item, else ``None``.

    The exact key path (``models[0].model``) identifies the slot. Repeated
    entries of the *same* model are collapsed later by resolved canonical id,
    so "one source model listed in several MergeKit slots" stays a single
    source instead of inflating support.
    """
    if item.source_type is not SourceType.MERGE_CONFIG or not item.key_path:
        return None
    return item.key_path


# Heuristic per-item weights live in :mod:`.fusion`; imported lazily to avoid a
# circular import at module load.
def _weight_of(item: EvidenceItem) -> float:
    from .fusion import ITEM_WEIGHTS

    return ITEM_WEIGHTS.get(item.reliability, 0.0) * (
        1.0 if item.explicitness is Explicitness.EXPLICIT else 0.5
    )


class EvidenceCluster(BaseModel):
    """One canonical parent and every independent item naming it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical: str
    items: tuple[EvidenceItem, ...] = ()
    raw_ids: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    source_kinds: tuple[SourceType, ...] = ()
    tool_generated_kinds: tuple[SourceType, ...] = ()
    control_domains: tuple[ControlDomain, ...] = ()
    explicit: bool = False
    relations: tuple[Relation, ...] = ()
    weight: float = 0.0
    first_index: int = 0

    @property
    def dominant_relation(self) -> Relation | None:
        """Most strongly supported relation of this cluster (``None`` if tied)."""
        weights: dict[Relation, float] = {}
        for item in self.items:
            if item.relation is None:
                continue
            weights[item.relation] = weights.get(item.relation, 0.0) + _weight_of(item)
        if not weights:
            return None
        ranked = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0].value))
        if len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < 1e-9:
            return None  # genuine tie: do not invent a relation
        return ranked[0][0]


class CandidateHypothesis(BaseModel):
    """A proposed lineage: a single parent, or a set of merge source slots."""

    model_config = ConfigDict(extra="forbid")

    method: CandidateMethod
    clusters: tuple[EvidenceCluster, ...] = ()
    unresolved: tuple[ModelResolution, ...] = ()
    complete: bool = False
    completeness: str = ""
    weight: float = 0.0
    first_index: int = 0

    @property
    def parents(self) -> tuple[str, ...]:
        return tuple(cluster.canonical for cluster in self.clusters)

    @property
    def support_items(self) -> tuple[EvidenceItem, ...]:
        return tuple(item for cluster in self.clusters for item in cluster.items)

    @property
    def relation(self) -> Relation | None:
        """Relation established by this hypothesis's evidence, or ``None``.

        Only relations actually stated by the evidence count. A candidate that
        merely names a parent (``config._name_or_path``) never invents one.
        """
        relations = {c.dominant_relation for c in self.clusters} - {None}
        if len(relations) == 1:
            return next(iter(relations))
        if len(relations) > 1:
            weights: dict[Relation, float] = {}
            for cluster in self.clusters:
                relation = cluster.dominant_relation
                if relation is not None:
                    weights[relation] = weights.get(relation, 0.0) + cluster.weight
            ranked = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0].value))
            if len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < 1e-9:
                return None
            return ranked[0][0]
        return None


class CandidateSet(BaseModel):
    """All hypotheses found for one repository plus unresolved references."""

    model_config = ConfigDict(extra="forbid")

    hypotheses: tuple[CandidateHypothesis, ...] = ()
    unresolved: tuple[ModelResolution, ...] = ()
    issues: tuple[ExtractionIssue, ...] = ()

    @property
    def has_usable_candidate(self) -> bool:
        return any(hypothesis.clusters for hypothesis in self.hypotheses)


def _resolve_with_index(
    item: EvidenceItem, index: dict[str, set[str]]
) -> ModelResolution:
    return resolve_identifier(item.candidate_parent, evidence_ids=index)


def _cluster_from_items(canonical: str, items: list[EvidenceItem]) -> EvidenceCluster:
    """Build an evidence cluster for one resolved parent."""
    ordered = sorted(items, key=lambda i: (i.source_name or "", i.key_path or ""))
    tool_kinds = sorted(
        {i.source_type for i in ordered if control_domain(i) is ControlDomain.TOOL_GENERATED},
        key=lambda k: k.value,
    )
    return EvidenceCluster(
        canonical=canonical,
        items=tuple(ordered),
        raw_ids=tuple(sorted({i.candidate_parent or canonical for i in ordered})),
        source_files=tuple(sorted({_source_key(i) for i in ordered})),
        source_kinds=tuple(sorted({i.source_type for i in ordered}, key=lambda k: k.value)),
        tool_generated_kinds=tuple(tool_kinds),
        control_domains=tuple(sorted(
            {control_domain(i) for i in ordered}, key=lambda d: d.value
        )),
        explicit=any(i.explicitness is Explicitness.EXPLICIT for i in ordered),
        relations=tuple(i.relation for i in ordered if i.relation),
        weight=sum(_weight_of(i) for i in ordered),
    )


def _merge_completeness(
    clusters: list[EvidenceCluster],
    slot_unresolved: list[ModelResolution],
    ambiguous_slots: list[str],
) -> tuple[str, bool]:
    """Describe how completely the independently observed merge set was seen."""
    distinct = sorted({c.canonical for c in clusters})
    statuses = {r.status for r in slot_unresolved}
    if ambiguous_slots:
        return "incomplete_ambiguous_slot", False
    if statuses & {ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNRESOLVED}:
        return "incomplete_unresolved", False
    if ResolutionStatus.INVALID in statuses:
        return "incomplete_invalid_references", False
    if len(distinct) < 2:
        return "single_source", False
    return "complete", True


def _merge_hypothesis(
    merge_items: list[tuple[str, EvidenceItem]],
    index: dict[str, set[str]],
    unresolved_sink: list[ModelResolution],
) -> CandidateHypothesis | None:
    """Build the merge hypothesis from merge-config slots (order-preserving)."""
    by_slot: dict[str, list[EvidenceItem]] = {}
    slot_order: list[str] = []
    for slot, item in merge_items:
        if slot not in by_slot:
            slot_order.append(slot)
            by_slot[slot] = []
        by_slot[slot].append(item)

    grouped: dict[str, list[EvidenceItem]] = {}
    slot_unresolved: list[ModelResolution] = []
    ambiguous_slots: list[str] = []
    for slot in slot_order:
        items = sorted(
            by_slot[slot], key=lambda i: (i.key_path or "", i.candidate_parent or "")
        )
        slot_targets: dict[str, list[EvidenceItem]] = {}
        for item in items:
            resolution = _resolve_with_index(item, index)
            if resolution.resolved is None:
                slot_unresolved.append(resolution)
                unresolved_sink.append(resolution)
                continue
            slot_targets.setdefault(resolution.resolved, []).append(item)
        if len(slot_targets) > 1:
            # One slot naming several distinct models (a sub-layer merge):
            # genuine ambiguity, never reduced to a single parent.
            ambiguous_slots.append(slot)
        for canonical, group in slot_targets.items():
            grouped.setdefault(canonical, []).extend(group)

    if not grouped:
        return None
    clusters = [
        _cluster_from_items(canonical, grouped[canonical]) for canonical in grouped
    ]
    completeness, complete = _merge_completeness(
        clusters, slot_unresolved, ambiguous_slots
    )
    return CandidateHypothesis(
        method=CandidateMethod.MERGE,
        clusters=tuple(clusters),
        unresolved=tuple(sorted(slot_unresolved, key=lambda r: r.raw)),
        complete=complete,
        completeness=completeness,
        weight=sum(cluster.weight for cluster in clusters),
        first_index=0,
    )


def aggregate_candidates(
    evidence: list[EvidenceItem],
    *,
    issues: list[ExtractionIssue] | tuple[ExtractionIssue, ...] = (),
) -> CandidateSet:
    """Build candidate hypotheses from independent evidence items.

    Deterministic: only exact ties are broken by input order (``first_index``).
    """
    independent = [
        item
        for item in evidence
        if item.role is EvidenceRole.INDEPENDENT
        and item.candidate_parent
        and item.reliability is not Reliability.NOT_APPLICABLE
        and _is_evidence_file(item)
    ]
    independent.sort(
        key=lambda i: (
            i.source_type.value,
            i.source_name or "",
            i.key_path or "",
            i.candidate_parent or "",
        )
    )

    # Alias index: canonical id -> every raw spelling the evidence used.
    index: dict[str, set[str]] = {}
    for item in independent:
        resolution = resolve_identifier(item.candidate_parent)
        if resolution.resolved is None:
            continue
        index.setdefault(resolution.resolved, set()).add(resolution.resolved)
        if item.candidate_parent:
            index[resolution.resolved].add(item.candidate_parent)

    grouped: dict[str, list[EvidenceItem]] = {}
    unresolved: list[ModelResolution] = []
    merge_items: list[tuple[str, EvidenceItem]] = []

    for position, item in enumerate(independent):
        resolution = _resolve_with_index(item, index)
        if resolution.resolved is None:
            unresolved.append(resolution)
            continue
        grouped.setdefault(resolution.resolved, []).append(item)
        slot = _slot_of(item)
        if slot is not None:
            merge_items.append((slot, item))

    order = {id(item): position for position, item in enumerate(independent)}
    hypotheses: list[CandidateHypothesis] = []
    merge = _merge_hypothesis(merge_items, index, unresolved)
    if merge is not None:
        hypotheses.append(merge)
    for canonical, items in grouped.items():
        cluster = _cluster_from_items(canonical, items)
        hypotheses.append(CandidateHypothesis(
            method=CandidateMethod.SINGLE,
            clusters=(cluster,),
            weight=cluster.weight,
            # deterministic tie-breaker: first evidence position of this parent
            first_index=min(order.get(id(i), len(independent)) for i in items),
        ))

    return CandidateSet(
        hypotheses=tuple(hypotheses),
        unresolved=tuple(sorted(unresolved, key=lambda r: r.raw)),
        issues=tuple(issues),
    )
