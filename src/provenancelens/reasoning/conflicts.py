"""Structured conflict detection over candidates vs declared lineage.

A *conflict* here means structured evidence disagrees with the declared
subject, or the evidence is internally contradictory. Two things are
deliberately NOT conflicts and must never inflate the conflict list:

* absence of corroboration (an unmentioned parent is not a contradiction),
* mere incompleteness of an independently observed merge source set.

Every conflict keeps the :class:`EvidenceItem` objects that caused it, so a
reader can re-derive the conflict from the frozen evidence.
"""

from __future__ import annotations

from enum import Enum

from ..resolution import ResolutionStatus, resolve_identifier
from ..schemas.audit import Conflict, ConflictKind
from ..schemas.extraction import ExtractionIssue
from ..schemas.lineage import DeclaredLineage
from .candidates import CandidateHypothesis, CandidateMethod
from .fusion import DEFAULT_POLICY, DecisionPolicy, SupportAssessment

__all__ = [
    "DeclaredComparison",
    "compare_declared_lineage",
    "compare_sets",
    "declared_resolution",
    "declared_resolution_index",
    "detect_conflicts",
    "is_competing",
]


class DeclaredComparison(str, Enum):
    """How a declared lineage compares to independently observed evidence."""

    EXACT_MATCH = "exact_match"
    INDEPENDENT_SUBSET = "independent_subset"  # evidence saw fewer parents
    DECLARED_SUBSET = "declared_subset"        # evidence saw more parents
    PARTIAL_OVERLAP = "partial_overlap"
    NO_OVERLAP = "no_overlap"
    NOTHING_DECLARED = "nothing_declared"
    RELATION_DIFFERS = "relation_differs"
    NOT_COMPARABLE = "not_comparable"


def declared_resolution(
    declared: DeclaredLineage, index: dict[str, set[str]] | None = None
) -> tuple[frozenset[str], list[str]]:
    """Resolve declared parents; returns (resolved set, unresolved raws)."""
    resolved: set[str] = set()
    unresolved: list[str] = []
    for raw in declared.base_models:
        resolution = resolve_identifier(raw, evidence_ids=index or {})
        if resolution.resolved is None:
            unresolved.append(raw)
        else:
            resolved.add(resolution.resolved)
    return frozenset(resolved), unresolved


def declared_resolution_index(declared: DeclaredLineage) -> dict[str, set[str]]:
    """Alias index covering declared ids too (for referent matching)."""
    index: dict[str, set[str]] = {}
    for raw in declared.base_models:
        resolution = resolve_identifier(raw)
        if resolution.resolved is None:
            continue
        index.setdefault(resolution.resolved, set()).add(resolution.resolved)
        index[resolution.resolved].add(raw)
    return index


def compare_sets(declared: frozenset[str], observed: frozenset[str]) -> DeclaredComparison:
    if not declared:
        return DeclaredComparison.NOTHING_DECLARED
    if not observed:
        return DeclaredComparison.NOT_COMPARABLE
    if declared == observed:
        return DeclaredComparison.EXACT_MATCH
    if observed < declared:
        return DeclaredComparison.INDEPENDENT_SUBSET
    if declared < observed:
        return DeclaredComparison.DECLARED_SUBSET
    if declared & observed:
        return DeclaredComparison.PARTIAL_OVERLAP
    return DeclaredComparison.NO_OVERLAP


def compare_declared_lineage(
    declared: DeclaredLineage,
    candidate: CandidateHypothesis,
    declared_parents: frozenset[str],
) -> DeclaredComparison:
    """Set-aware comparison of declared lineage vs observed candidate."""
    comparison = compare_sets(declared_parents, frozenset(candidate.parents))
    if comparison is not DeclaredComparison.EXACT_MATCH:
        return comparison
    declared_relation = declared.relation
    candidate_relation = candidate.relation
    if (
        declared_relation is not None
        and candidate_relation is not None
        and declared_relation is not candidate_relation
    ):
        return DeclaredComparison.RELATION_DIFFERS
    return comparison


def detect_conflicts(
    candidates: tuple[CandidateHypothesis, ...],
    declared: DeclaredLineage,
    declared_parents: frozenset[str],
    supports: dict[int, SupportAssessment],
    *,
    issues: tuple[ExtractionIssue, ...] = (),
    unresolved: tuple[object, ...] = (),
    policy: DecisionPolicy = DEFAULT_POLICY,
) -> list[Conflict]:
    """Return structured conflicts for the observed evidence.

    ``supports`` is keyed by the candidate's position in ``candidates``.
    """
    conflicts: list[Conflict] = []
    first = candidates[0] if candidates else None
    first_support = supports.get(0) if first is not None else None

    conflicts.extend(_unresolved_conflicts(candidates, unresolved))

    # A parent that is one of a *complete* merge reading's sources is part of
    # that explanation, not a rival claim competing with it.
    complete_merge_parents = frozenset(
        parent
        for candidate in candidates
        if candidate.method is CandidateMethod.MERGE and candidate.complete
        for parent in candidate.parents
    )

    competing = [
        (index, other)
        for index, other in enumerate(candidates[1:], start=1)
        if index in supports
        and supports[index].support >= policy.min_support_affirmative
        and first is not None
        and is_competing(first, other)
        and not (
            complete_merge_parents
            and set(other.parents) <= complete_merge_parents
        )
    ]
    if competing and first is not None and first_support is not None:
        index, other = competing[0]
        other_support = supports[index]
        conflicts.append(Conflict(
            kind=ConflictKind.COMPETING_CANDIDATES,
            description=(
                "multiple incompatible lineage hypotheses are comparably supported: "
                f"{', '.join(first.parents)} (support {first_support.support:.2f}) vs "
                f"{', '.join(other.parents)} (support {other_support.support:.2f})"
            ),
            evidence=list(first.support_items) + list(other.support_items),
        ))

    if first is not None and first_support is not None:
        # A mismatch is only a *conflict* when the observed hypothesis is itself
        # supportable at the affirmative bar. A weak hint that merely names a
        # different model is missing corroboration, not a contradiction.
        if first_support.support >= policy.min_support_affirmative:
            if first.method is CandidateMethod.MERGE:
                conflicts.extend(
                    _merge_conflicts(declared, first, first_support, declared_parents)
                )
            else:
                conflicts.extend(
                    _single_conflicts(declared, first, declared_parents)
                )
                if _relation_disagrees(declared, first_support):
                    conflicts.append(Conflict(
                        kind=ConflictKind.RELATION_CONFLICT,
                        description=(
                            f"declared base_model_relation {declared.relation_raw!r} "
                            f"({declared.relation.value}) disagrees with independent "
                            f"evidence ({first_support.relation.value})"
                        ),
                        evidence=list(first.support_items),
                    ))

    if declared.relation_raw is not None and declared.relation is None:
        conflicts.append(Conflict(
            kind=ConflictKind.UNKNOWN_DECLARED_RELATION,
            description=(
                f"declared base_model_relation {declared.relation_raw!r} is not a "
                "supported canonical relation (finetune/adapter/merge/quantized); "
                "it is preserved but never interpreted"
            ),
        ))

    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        conflicts.append(Conflict(
            kind=ConflictKind.TOOL_FAILURE,
            description=(
                "evidence collection/parsing reported problems, so corroboration may "
                "be missing for reasons unrelated to the repository: "
                + "; ".join(f"{i.source_name}: {i.message}" for i in errors)
            ),
        ))

    return conflicts


def _relation_disagrees(declared: DeclaredLineage, support: SupportAssessment) -> bool:
    return (
        declared.relation is not None
        and support.relation is not None
        and declared.relation is not support.relation
    )


def is_competing(top: CandidateHypothesis, other: CandidateHypothesis) -> bool:
    """True when ``other`` is incompatible with the leading hypothesis.

    A parent that is *part of* an observed merge source set is not a rival
    hypothesis but a member of it; a merge set containing the leading parent is
    a superset explanation, not a contradiction. Only genuinely disjoint sets
    (or two single parents that differ) compete.
    """
    top_parents = set(top.parents)
    other_parents = set(other.parents)
    if top.method is CandidateMethod.MERGE or other.method is CandidateMethod.MERGE:
        return not (other_parents & top_parents)
    return other_parents != top_parents


def _unresolved_conflicts(
    candidates: tuple[CandidateHypothesis, ...],
    extra: tuple[object, ...] = (),
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    seen: set[str] = set()
    resolutions = list(extra)
    for candidate in candidates:
        resolutions.extend(candidate.unresolved)
    for resolution in resolutions:
        if resolution.status is ResolutionStatus.INVALID:
            continue  # rejected values are reported by the parsers, not here
        if resolution.raw in seen:
            continue
        seen.add(resolution.raw)
        kind = (
            ConflictKind.UNRESOLVED_MODEL_ID
            if resolution.status is ResolutionStatus.UNRESOLVED
            else ConflictKind.VERSION_AMBIGUITY
        )
        conflicts.append(Conflict(
            kind=kind,
            description=(
                f"model reference {resolution.raw!r} could not be safely resolved "
                f"({resolution.reason})"
                + (
                    f"; distinct targets seen in the evidence: "
                    f"{', '.join(resolution.alternatives)}"
                    if resolution.alternatives else ""
                )
            ),
        ))
    return conflicts


def _single_conflicts(
    declared: DeclaredLineage,
    candidate: CandidateHypothesis,
    declared_parents: frozenset[str],
) -> list[Conflict]:
    comparison = compare_sets(declared_parents, frozenset(candidate.parents))
    if comparison in (DeclaredComparison.NOTHING_DECLARED, DeclaredComparison.EXACT_MATCH):
        return []
    if comparison is DeclaredComparison.INDEPENDENT_SUBSET:
        # Single-parent hypotheses cannot be "a strict subset"; treat as mismatch.
        pass
    return [Conflict(
        kind=ConflictKind.DECLARED_VS_INDEPENDENT,
        description=(
            f"declared lineage ({', '.join(sorted(declared_parents))}) does not match "
            f"the independently supported parent(s) ({', '.join(candidate.parents)})"
        ),
        evidence=list(candidate.support_items),
    )]


def _merge_conflicts(
    declared: DeclaredLineage,
    candidate: CandidateHypothesis,
    support: SupportAssessment,
    declared_parents: frozenset[str],
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    comparison = compare_sets(declared_parents, frozenset(candidate.parents))
    if comparison is DeclaredComparison.EXACT_MATCH:
        if _relation_disagrees(declared, support):
            conflicts.append(Conflict(
                kind=ConflictKind.RELATION_CONFLICT,
                description=(
                    f"declared base_model_relation {declared.relation_raw!r} disagrees "
                    f"with the independently observed merge relation "
                    f"({support.relation.value})"
                ),
                evidence=list(candidate.support_items),
            ))
        return conflicts
    if comparison is DeclaredComparison.INDEPENDENT_SUBSET:
        # Missing corroboration, NOT a contradiction: never blocks KEEP/REPLACE.
        return conflicts
    if comparison in (
        DeclaredComparison.DECLARED_SUBSET, DeclaredComparison.PARTIAL_OVERLAP,
    ):
        conflicts.append(Conflict(
            kind=ConflictKind.MULTIPLE_MERGE_SOURCES,
            description=(
                "independently observed merge sources "
                f"({', '.join(candidate.parents)}) are not identical to the declared "
                f"source set ({', '.join(sorted(declared_parents))})"
            ),
            evidence=list(candidate.support_items),
        ))
        return conflicts
    if comparison is DeclaredComparison.NO_OVERLAP:
        conflicts.append(Conflict(
            kind=ConflictKind.DECLARED_VS_INDEPENDENT,
            description=(
                f"declared lineage ({', '.join(sorted(declared_parents))}) shares no "
                f"source with the observed merge sources "
                f"({', '.join(candidate.parents)})"
            ),
            evidence=list(candidate.support_items),
        ))
    return conflicts
