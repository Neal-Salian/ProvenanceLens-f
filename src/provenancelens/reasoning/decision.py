"""Conservative KEEP / ADD / REPLACE / ABSTAIN decision engine (Phase D).

This engine is deliberately separate from :mod:`provenancelens.reasoning.legacy`
(the Phase 2 regression baseline) and repairs the flaws documented for it:

* declared metadata contributes **zero** independent support,
* evidence is fused by reliability/explicitness/source, not by counting
  mentions,
* a single explicit ``VERY_HIGH`` artifact may be sufficient (Phase 2 required
  two sources unconditionally),
* REPLACE requires a *contradiction* plus decisive, relation-complete,
  non-author-controlled support, with no unresolved reference left that could
  denote the declared model,
* anything short of a safe repair is ABSTAIN with an explanation.

Every branch records which requirement failed, so ``reasoning_summary`` reads
as a short audit record instead of a narrative, and ``rejected_reasons``
explains why stronger actions were not taken.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..schemas.audit import (
    AuditDecision,
    Conflict,
    ConflictKind,
    Decision,
    SuggestedPatch,
)
from ..schemas.evidence import EvidenceItem, SourceType
from ..schemas.lineage import DeclaredLineage, Lineage, LineageEntry, Relation
from .candidates import (
    CandidateHypothesis,
    CandidateMethod,
    CandidateSet,
    aggregate_candidates,
)
from .conflicts import (
    DeclaredComparison,
    compare_declared_lineage,
    declared_resolution,
    detect_conflicts,
)
from .fusion import (
    DEFAULT_POLICY,
    DecisionPolicy,
    LineagePlan,
    SupportAssessment,
    compute_support,
)

__all__ = ["DecisionResult", "decide_lineage"]

_BLOCKING_CONFLICTS = (
    ConflictKind.COMPETING_CANDIDATES,
    ConflictKind.VERSION_AMBIGUITY,
    ConflictKind.UNRESOLVED_MODEL_ID,
    ConflictKind.UNKNOWN_DECLARED_RELATION,
    ConflictKind.MULTIPLE_MERGE_SOURCES,
)


class DecisionResult(BaseModel):
    """Full Phase D reasoning output: the decision plus its explanation."""

    model_config = ConfigDict(extra="forbid")

    decision: AuditDecision
    candidates: CandidateSet
    supports: tuple[SupportAssessment, ...] = ()
    plan: LineagePlan | None = None
    comparison: DeclaredComparison | None = None
    rejected_reasons: tuple[str, ...] = ()


def decide_lineage(
    model_id: str,
    declared: DeclaredLineage,
    evidence: list[EvidenceItem],
    *,
    policy: DecisionPolicy = DEFAULT_POLICY,
    candidates: CandidateSet | None = None,
) -> DecisionResult:
    """Decide one repository's direct-lineage metadata from evidence.

    ``declared`` is the audit subject. ``evidence`` may also contain declared
    items — aggregation structurally excludes them from support, so a declared
    claim can never prove itself.
    """
    candidate_set = candidates if candidates is not None else aggregate_candidates(evidence)
    declared_parents, _declared_unresolved = declared_resolution(declared)

    ranked: list[tuple[CandidateHypothesis, SupportAssessment]] = []
    supports_by_position: dict[int, SupportAssessment] = {}
    for index, hypothesis in enumerate(candidate_set.hypotheses):
        support = compute_support(hypothesis, declared_parents, policy=policy)
        supports_by_position[index] = support
        if hypothesis.clusters:
            ranked.append((hypothesis, support))
    complete_merge_parents = frozenset(
        parent
        for hypothesis in candidate_set.hypotheses
        if hypothesis.method is CandidateMethod.MERGE and hypothesis.complete
        for parent in hypothesis.parents
    )
    ranked.sort(
        key=lambda row: _rank_key(row[0], row[1], complete_merge_parents, policy)
    )
    ordered = tuple(row[0] for row in ranked)
    ordered_supports = {i: s for i, (_h, s) in enumerate(ranked)}
    support_list = tuple(row[1] for row in ranked)

    conflicts = detect_conflicts(
        ordered, declared, declared_parents, ordered_supports,
        issues=candidate_set.issues,
        unresolved=candidate_set.unresolved,
        policy=policy,
    )
    rejected = _rejection_reasons(ordered, ranked, declared_parents)

    # --- nothing to work with ---------------------------------------------
    if not ranked:
        return DecisionResult(
            decision=AuditDecision.abstain(
                model_id=model_id,
                current_lineage=declared,
                reasoning_summary=_no_evidence_summary(declared, candidate_set),
                conflicts=conflicts,
            ),
            candidates=candidate_set,
            supports=support_list,
            rejected_reasons=rejected,
        )

    winner, support = ranked[0]
    runners_up = [h for h in ordered[1:]]

    # --- hard blockers, regardless of anything else ------------------------
    blocking = _blocking_conflicts(conflicts)
    if blocking:
        return DecisionResult(
            decision=AuditDecision.abstain(
                model_id=model_id,
                current_lineage=declared,
                reasoning_summary=_blocking_summary(blocking, declared, candidate_set),
                support_score=support.support,
                conflicts=conflicts,
                contradictory_evidence=[
                    item for h in runners_up for item in h.support_items
                ],
            ),
            candidates=candidate_set,
            supports=support_list,
            rejected_reasons=rejected,
        )

    plan = _plan_for(winner, support)
    comparison = compare_declared_lineage(declared, winner, declared_parents)
    declared_present = bool(declared_parents)

    # --- nothing declared: ADD or ABSTAIN ----------------------------------
    if not declared_present:
        reasons = _add_blockers(winner, support, policy)
        if reasons:
            return _abstain_result(
                model_id, declared, candidate_set, support_list, rejected, conflicts,
                summary=(
                    "ABSTAIN: no direct lineage is declared and the independent "
                    "evidence does not safely establish one (" + "; ".join(reasons)
                    + "). Nothing is guessed."
                ),
                support_score=support.support,
                supporting=list(winner.support_items),
            )
        assert plan is not None
        decision = AuditDecision(
            model_id=model_id,
            current_lineage=declared,
            decision=Decision.ADD,
            proposed_lineage=plan.to_lineage(),
            support_score=support.support,
            supporting_evidence=list(winner.support_items),
            conflicts=conflicts,
            reasoning_summary=(
                f"ADD: no direct lineage is declared. {len(plan.entries)} independently "
                f"extracted source(s) ({', '.join(plan.to_lineage().parents)}) with "
                f"relation {_relation_label(support.relation)} are identified by "
                f"tool-generated evidence ({_kinds_label(support)}), support "
                f"{support.support:.2f} >= {policy.min_support_add:.2f}. Declared metadata "
                "is never used as its own support. Proposed as a patch only; nothing is "
                "written to the repository."
            ),
            recommended_patch=_patch_for(plan, declared),
        )
        return DecisionResult(
            decision=decision, candidates=candidate_set, supports=support_list,
            plan=plan, comparison=comparison, rejected_reasons=rejected,
        )

    # --- declared lineage corroborated exactly ----------------------------
    if comparison is DeclaredComparison.EXACT_MATCH:
        reasons = _keep_blockers(winner, support, policy, conflicts)
        if reasons:
            return _abstain_result(
                model_id, declared, candidate_set, support_list, rejected, conflicts,
                summary=(
                    "ABSTAIN: the observed evidence matches the declared parent but the "
                    "existing metadata cannot be safely accepted (" + "; ".join(reasons)
                    + "). The declared metadata is left untouched."
                ),
                support_score=support.support,
                supporting=list(winner.support_items),
            )
        assert plan is not None
        decision = AuditDecision(
            model_id=model_id,
            current_lineage=declared,
            decision=Decision.KEEP,
            proposed_lineage=plan.to_lineage(),
            support_score=support.support,
            supporting_evidence=list(winner.support_items),
            conflicts=conflicts,
            reasoning_summary=(
                f"KEEP: the declared lineage ({', '.join(sorted(declared_parents))}) is "
                f"independently supported by {', '.join(support.contributing_files)} "
                f"(support {support.support:.2f} >= {policy.min_support_keep:.2f}) with no "
                "material contradiction. Existing metadata is preserved unchanged."
            ),
        )
        return DecisionResult(
            decision=decision, candidates=candidate_set, supports=support_list,
            plan=plan, comparison=comparison, rejected_reasons=rejected,
        )

    # --- same parent, contradicting relation -------------------------------
    if comparison is DeclaredComparison.RELATION_DIFFERS:
        reasons = _relation_repair_blockers(support, policy, conflicts)
        if reasons:
            return _abstain_result(
                model_id, declared, candidate_set, support_list, rejected, conflicts,
                summary=(
                    f"ABSTAIN: the declared relation {declared.relation_raw!r} "
                    f"({declared.relation.value}) contradicts the independent evidence "
                    f"({support.relation and support.relation.value}) and a relation "
                    "repair is not safe (" + "; ".join(reasons) + "). The parent is "
                    "corroborated, but the relation is left untouched."
                ),
                support_score=support.support,
                supporting=list(winner.support_items),
            )
        assert plan is not None
        decision = AuditDecision(
            model_id=model_id,
            current_lineage=declared,
            decision=Decision.REPLACE,
            proposed_lineage=plan.to_lineage(),
            support_score=support.support,
            supporting_evidence=list(winner.support_items),
            conflicts=conflicts,
            reasoning_summary=(
                f"REPLACE (relation only): the declared parent "
                f"({', '.join(sorted(declared_parents))}) is corroborated, but the "
                f"declared relation {declared.relation_raw!r} is decisively contradicted "
                f"by {', '.join(support.contributing_files)}, which establish relation "
                f"{support.relation.value if support.relation else 'unspecified'} with "
                f"support {support.support:.2f} >= {policy.min_support_replace:.2f}. "
                "Proposed as a patch only."
            ),
            recommended_patch=_patch_for(plan, declared),
        )
        return DecisionResult(
            decision=decision, candidates=candidate_set, supports=support_list,
            plan=plan, comparison=comparison, rejected_reasons=rejected,
        )

    # --- merge: evidence saw fewer sources than declared -------------------
    if (
        comparison is DeclaredComparison.INDEPENDENT_SUBSET
        and winner.method is CandidateMethod.MERGE
    ):
        # An uninterpretable declared relation is already refused by the hard
        # UNKNOWN_DECLARED_RELATION blocker above, so reaching this point means
        # the declared relation is either absent or itself supported.
        decision = AuditDecision(
            model_id=model_id,
            current_lineage=declared,
            decision=Decision.KEEP,
            proposed_lineage=_declared_lineage(declared),
            support_score=support.support,
            supporting_evidence=list(winner.support_items),
            conflicts=conflicts,
            reasoning_summary=(
                f"KEEP: every independently observed merge source "
                f"({', '.join(winner.parents)}) is contained in the declared source set "
                f"({', '.join(sorted(declared_parents))}). The remaining declared "
                "source(s) lack independent corroboration, which is missing evidence "
                "rather than a contradiction; support "
                f"{support.support:.2f} >= {policy.min_support_keep:.2f}. The declared "
                "set is preserved unchanged."
            ),
        )
        return DecisionResult(
            decision=decision, candidates=candidate_set, supports=support_list,
            comparison=comparison, rejected_reasons=rejected,
        )

    # --- genuine contradiction: REPLACE only if decisively safe ------------
    reasons = _replace_blockers(winner, support, policy, conflicts, declared)
    if reasons:
        return _abstain_result(
            model_id, declared, candidate_set, support_list, rejected, conflicts,
            summary=(
                "ABSTAIN: the independent evidence conflicts with the declared lineage "
                f"({', '.join(sorted(declared_parents))}), but replacing it is not safe "
                "(" + "; ".join(reasons) + "). The existing metadata is left untouched."
            ),
            support_score=support.support,
            supporting=list(winner.support_items),
        )
    assert plan is not None
    decision = AuditDecision(
        model_id=model_id,
        current_lineage=declared,
        decision=Decision.REPLACE,
        proposed_lineage=plan.to_lineage(),
        support_score=support.support,
        supporting_evidence=list(winner.support_items),
        contradictory_evidence=[
            item for h in runners_up for item in h.support_items
        ],
        conflicts=conflicts,
        reasoning_summary=(
            f"REPLACE: the declared lineage ({', '.join(sorted(declared_parents))}) is "
            f"contradicted by independently extracted evidence "
            f"({', '.join(plan.to_lineage().parents)}, relation "
            f"{_relation_label(support.relation)}) from "
            f"{', '.join(support.contributing_files)}: support {support.support:.2f} >= "
            f"{policy.min_support_replace:.2f}, the relation is established by that "
            "evidence, no reference remained unresolved, and the contradicting evidence "
            "is tool-generated rather than author prose. Proposed as a patch only."
        ),
        recommended_patch=_patch_for(plan, declared),
    )
    return DecisionResult(
        decision=decision, candidates=candidate_set, supports=support_list,
        plan=plan, comparison=comparison, rejected_reasons=rejected,
    )


# --- helpers ----------------------------------------------------------------


def _rank_key(
    candidate: CandidateHypothesis,
    support: SupportAssessment,
    complete_merge_parents: frozenset[str],
    policy: DecisionPolicy,
) -> tuple[int, float, int]:
    """Deterministic hypothesis ranking.

    A single-parent reading that is one of a *complete* merge reading's sources
    is a partial explanation of the same evidence. Unless that partial reading
    carries decisive support of its own, the complete structural reading is
    ranked first, because it accounts for strictly more of the evidence.
    """
    partial_reading = (
        candidate.method is CandidateMethod.SINGLE
        and bool(complete_merge_parents)
        and set(candidate.parents) <= complete_merge_parents
        and support.support < policy.min_support_decisive
    )
    return (1 if partial_reading else 0, -support.support, candidate.first_index)


def _relation_label(relation: Relation | None) -> str:
    return relation.value if relation is not None else "unspecified"


def _kinds_label(support: SupportAssessment) -> str:
    return ", ".join(k.value for k in support.tool_kinds) or "no tool-generated source"


def _abstain_result(
    model_id: str,
    declared: DeclaredLineage,
    candidates: CandidateSet,
    supports: tuple[SupportAssessment, ...],
    rejected: tuple[str, ...],
    conflicts: list[Conflict],
    *,
    summary: str,
    support_score: float = 0.0,
    supporting: list[EvidenceItem] | None = None,
    contradictory: list[EvidenceItem] | None = None,
    extra_conflicts: list[Conflict] | None = None,
) -> DecisionResult:
    all_conflicts = list(conflicts) + list(extra_conflicts or [])
    return DecisionResult(
        decision=AuditDecision.abstain(
            model_id=model_id,
            current_lineage=declared,
            reasoning_summary=summary,
            support_score=support_score,
            conflicts=all_conflicts,
            supporting_evidence=supporting or [],
            contradictory_evidence=contradictory or [],
        ),
        candidates=candidates,
        supports=supports,
        rejected_reasons=rejected,
    )


def _blocking_conflicts(conflicts: list[Conflict]) -> list[Conflict]:
    return [c for c in conflicts if c.kind in _BLOCKING_CONFLICTS]


def _blocking_summary(
    blocking: list[Conflict],
    declared: DeclaredLineage,
    candidates: CandidateSet,
) -> str:
    kinds = sorted({c.kind.value for c in blocking})
    if any(c.kind is ConflictKind.COMPETING_CANDIDATES for c in blocking):
        head = (
            "ABSTAIN: several incompatible lineage hypotheses are comparably supported, "
            "so selecting one would be a guess."
        )
    elif any(
        c.kind in (ConflictKind.VERSION_AMBIGUITY, ConflictKind.UNRESOLVED_MODEL_ID)
        for c in blocking
    ):
        head = (
            "ABSTAIN: at least one model reference could not be safely resolved "
            f"({'; '.join(c.description for c in blocking)}). Lineage repair requires "
            "identifying the exact model, so no repair is proposed."
        )
    elif any(c.kind is ConflictKind.UNKNOWN_DECLARED_RELATION for c in blocking):
        head = (
            f"ABSTAIN: the declared base_model_relation {declared.relation_raw!r} is not "
            "a supported canonical relation (finetune/adapter/merge/quantized). It is "
            "preserved and never reinterpreted automatically."
        )
    elif any(c.kind is ConflictKind.MULTIPLE_MERGE_SOURCES for c in blocking):
        head = (
            "ABSTAIN: the independently observed merge source set contradicts the "
            "declared set, and merging on incomplete evidence is unsafe."
        )
    else:
        head = "ABSTAIN: unresolved structured conflicts block any safe repair."
    _ = candidates
    return f"{head} (conflict kinds: {', '.join(kinds)})"


def _plan_for(
    candidate: CandidateHypothesis, support: SupportAssessment
) -> LineagePlan | None:
    if not candidate.clusters:
        return None
    if candidate.method is CandidateMethod.MERGE:
        entries = tuple(
            LineageEntry(parent=cluster.canonical, relation=cluster.dominant_relation)
            for cluster in candidate.clusters
        )
        return LineagePlan.merge(entries, support)
    return LineagePlan.single(candidate.clusters[0].canonical, support.relation, support)


def _declared_lineage(declared: DeclaredLineage) -> Lineage:
    return Lineage(entries=[
        LineageEntry(parent=parent, relation=declared.relation)
        for parent in declared.base_models
    ])


def _patch_for(plan: LineagePlan, declared: DeclaredLineage) -> SuggestedPatch | None:
    if not plan.entries:
        return None
    first = plan.entries[0]
    return SuggestedPatch(
        old_base_model=declared.base_model,
        new_base_model=first.parent,
        old_relation_raw=declared.relation_raw,
        new_relation=first.relation,
    )


def _states_no_relation(candidate: CandidateHypothesis) -> bool:
    """True when no evidence item for this hypothesis states a relation."""
    return not any(c.relations for c in candidate.clusters)


def _add_blockers(
    candidate: CandidateHypothesis,
    support: SupportAssessment,
    policy: DecisionPolicy,
) -> list[str]:
    reasons: list[str] = []
    if support.support < policy.min_support_add:
        reasons.append(
            f"support {support.support:.2f} < {policy.min_support_add:.2f}"
        )
    if not support.parent_identifying:
        reasons.append(
            "no parent-identifying evidence (explicit very_high/high/medium_high) is "
            "present; a hint cannot create a parent"
        )
    if support.relation is None:
        reasons.append("no independent evidence establishes the transformation relation")
    elif not support.relation_complete:
        reasons.append("the relation is only partially established by the evidence")
    if candidate.method is CandidateMethod.MERGE:
        if policy.require_complete_merge_sources and not candidate.complete:
            reasons.append(
                f"the merge source set is not completely observed ({candidate.completeness})"
            )
        if len({c.canonical for c in candidate.clusters}) < 2:
            reasons.append("a merge hypothesis needs at least two distinct sources")
    if support.author_controlled_only and not support.tool_kinds:
        reasons.append(
            "only author-controlled documents support the proposal; no tool-generated "
            "artifact identifies the parent"
        )
    return reasons


def _keep_blockers(
    candidate: CandidateHypothesis,
    support: SupportAssessment,
    policy: DecisionPolicy,
    conflicts: list[Conflict],
) -> list[str]:
    reasons: list[str] = []
    if support.support < policy.min_support_keep:
        reasons.append(f"support {support.support:.2f} < {policy.min_support_keep:.2f}")
    if not support.parent_identifying:
        reasons.append("no parent-identifying independent evidence")
    if support.relation is None and _states_no_relation(candidate):
        reasons.append("neither declared nor independent evidence establishes a relation")
    if any(c.kind is ConflictKind.RELATION_CONFLICT for c in conflicts):
        reasons.append("a declared-vs-independent relation contradiction remains")
    if any(c.kind is ConflictKind.DECLARED_VS_INDEPENDENT for c in conflicts):
        reasons.append("unresolved parent conflicts remain")
    if (
        candidate.method is CandidateMethod.MERGE
        and not candidate.complete
        and candidate.completeness != "independent_subset"
    ):
        reasons.append(
            f"the merge source set is not completely observed ({candidate.completeness})"
        )
    return reasons


def _relation_repair_blockers(
    support: SupportAssessment,
    policy: DecisionPolicy,
    conflicts: list[Conflict],
) -> list[str]:
    reasons: list[str] = []
    if support.support < policy.min_support_replace:
        reasons.append(
            f"support {support.support:.2f} < {policy.min_support_replace:.2f}"
        )
    if support.relation is None:
        reasons.append("the replacement relation is not established by any evidence")
    elif not support.relation_complete:
        reasons.append("the replacement relation is only partially established")
    if support.author_controlled_only:
        reasons.append("the contradicting evidence is author-controlled documentation only")
    if any(c.kind is ConflictKind.DECLARED_VS_INDEPENDENT for c in conflicts):
        reasons.append("the parent identity is itself in conflict")
    return reasons


def _replace_blockers(
    candidate: CandidateHypothesis,
    support: SupportAssessment,
    policy: DecisionPolicy,
    conflicts: list[Conflict],
    declared: DeclaredLineage,
) -> list[str]:
    reasons: list[str] = []
    if support.support < policy.min_support_replace:
        reasons.append(
            f"support {support.support:.2f} < {policy.min_support_replace:.2f}; a single "
            "source is never decisive enough to overwrite existing metadata"
        )
    if support.relation is None:
        reasons.append("the replacement relation is not established by any evidence")
    elif not support.relation_complete:
        reasons.append("the replacement relation is only partially established")
    if support.author_controlled_only:
        reasons.append("the contradicting evidence is author-controlled documentation only")
    if declared.relation_raw is not None and declared.relation is None:
        reasons.append("the declared relation is not interpretable")
    if any(c.kind is ConflictKind.MULTIPLE_MERGE_SOURCES for c in conflicts):
        reasons.append(
            "independently observed merge sources contradict the declared source set"
        )
    if candidate.method is CandidateMethod.MERGE and not candidate.complete:
        reasons.append(
            f"the observed merge source set is not complete ({candidate.completeness})"
        )
    return reasons


def _rejection_reasons(
    ordered: tuple[CandidateHypothesis, ...],
    ranked: list[tuple[CandidateHypothesis, SupportAssessment]],
    declared_parents: frozenset[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    for candidate, support in ranked[1:]:
        reasons.append(
            f"rejected {', '.join(candidate.parents)} "
            f"(support {support.support:.2f} below the winning hypothesis)"
        )
    if ordered and declared_parents and set(ordered[0].parents) != set(declared_parents):
        reasons.append(
            f"declared parents ({', '.join(sorted(declared_parents))}) differ from the "
            f"observed hypothesis ({', '.join(ordered[0].parents)})"
        )
    return tuple(reasons)


def _no_evidence_summary(declared: DeclaredLineage, candidates: CandidateSet) -> str:
    if candidates.unresolved:
        return (
            "ABSTAIN: no usable independent lineage evidence. The only model references "
            "found could not be safely resolved, so no repair is possible."
        )
    return (
        "ABSTAIN: no independent evidence identifying a direct parent was extracted "
        f"(declared lineage: {', '.join(declared.base_models) or 'none'}). Declared "
        "metadata is the subject of the audit and can never support itself; lack of "
        "evidence is reported as ABSTAIN, never guessed."
    )
