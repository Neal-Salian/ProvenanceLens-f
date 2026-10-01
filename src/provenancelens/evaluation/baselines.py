"""Deterministic evaluation baselines.

Each baseline is a faithful, documented stand-in for one plausible strategy -
none is deliberately weakened, and each reports the same per-case fields as the
full system so metrics are comparable.

1. ``declared_metadata`` - trust the repository; never infer.
2. ``config_only`` - the production engine restricted to framework config evidence.
3. ``prose_only`` - the production engine restricted to prose/model-card evidence.
4. ``majority_count`` - pick the candidate with the most evidence records; ties abstain.
5. ``rule_priority`` - fixed source hierarchy, no conflict/fusion logic.
6. ``always_keep`` - trivial reference (never the main comparator).

All of them are deterministic and run offline; the optional "ask a
full-context LLM" strategy is exposed as an interface only
(:class:`LLMOracleBaseline`) because it would require live local inference.
"""

from __future__ import annotations

from ..schemas.audit import AuditDecision, Decision
from ..schemas.evidence import EvidenceItem, Reliability, SourceType
from ..schemas.lineage import DeclaredLineage, Lineage, LineageEntry, Relation
from .runner import build_lineage, case_inputs, score_decision
from .schema import BenchmarkCase, CaseResult

__all__ = [
    "BASELINES",
    "BASELINE_NAMES",
    "SOURCE_PRIORITY",
    "run_baseline",
    "declared_metadata_baseline",
    "config_only_baseline",
    "prose_only_baseline",
    "majority_count_baseline",
    "rule_priority_baseline",
    "always_keep_baseline",
    "LLMOracleBaseline",
]

#: Fixed hierarchy used by the rule-priority baseline (documented, not tuned).
SOURCE_PRIORITY: tuple[tuple[SourceType, float], ...] = (
    (SourceType.ADAPTER_CONFIG, 4.0),
    (SourceType.MERGE_CONFIG, 3.0),
    (SourceType.TRAINING_CONFIG, 2.0),
    (SourceType.CONFIG, 1.0),
    (SourceType.README, 1.0),
    (SourceType.OTHER, 0.5),
)

_PROSE_TYPES = frozenset({SourceType.README, SourceType.OTHER})


def _decision(
    case: BenchmarkCase, action: Decision, parents: tuple[str, ...] = (),
    relation: Relation | None = None, *, declared: DeclaredLineage | None = None,
    support: float = 0.0, summary: str = "",
) -> AuditDecision:
    """Assemble an AuditDecision while honouring its invariants."""
    declared = declared if declared is not None else build_lineage(case)
    if action is Decision.ABSTAIN:
        return AuditDecision.abstain(
            case.repository or case.case_id, declared, summary,
            support_score=support,
        )
    proposed = Lineage(entries=[
        LineageEntry(parent=parent, relation=relation) for parent in parents
    ])
    patch = None
    if action in (Decision.ADD, Decision.REPLACE):
        from ..schemas.audit import SuggestedPatch

        patch = SuggestedPatch(
            old_base_model=declared.base_model,
            new_base_model=parents[0] if parents else None,
            old_relation_raw=declared.relation_raw,
            new_relation=relation,
        )
    return AuditDecision(
        model_id=case.repository or case.case_id,
        current_lineage=declared,
        decision=action,
        proposed_lineage=proposed,
        support_score=support,
        conflicts=[],
        reasoning_summary=summary or f"{action.value} (baseline)",
        recommended_patch=patch,
    )


# --- 1. declared metadata ---------------------------------------------------


def declared_metadata_baseline(case: BenchmarkCase) -> AuditDecision:
    """Trust the declaration; never infer lineage from evidence."""
    declared = build_lineage(case)
    if not declared.base_models:
        return _decision(
            case, Decision.ABSTAIN, declared=declared,
            summary="declared_metadata baseline: no lineage is declared and this "
                    "baseline never infers one",
        )
    return _decision(
        case, Decision.KEEP, parents=declared.base_models, relation=declared.relation,
        declared=declared,
        summary="declared_metadata baseline: existing declaration accepted unchanged",
    )


# --- 2 / 3. restricted-evidence baselines -----------------------------------


def _filtered_engine_baseline(
    case: BenchmarkCase, *, keep, system_note: str
) -> AuditDecision:
    """Run the production engine on a restricted evidence subset."""
    from ..reasoning import aggregate_candidates, decide_lineage

    declared, evidence, issues = case_inputs(case)
    subset = [item for item in evidence if keep(item)]
    if not subset:
        return _decision(
            case, Decision.ABSTAIN, declared=declared,
            summary=f"{system_note}: no evidence of this kind is available",
        )
    candidates = aggregate_candidates(subset, issues=issues)
    result = decide_lineage(
        case.repository or case.case_id, declared, subset, candidates=candidates
    )
    return result.decision


def config_only_baseline(case: BenchmarkCase) -> AuditDecision:
    """Production engine restricted to framework config evidence."""
    return _filtered_engine_baseline(
        case,
        keep=lambda item: item.source_type is SourceType.CONFIG,
        system_note="config_only baseline",
    )


def prose_only_baseline(case: BenchmarkCase) -> AuditDecision:
    """Production engine restricted to model-card/prose evidence."""
    return _filtered_engine_baseline(
        case,
        keep=lambda item: item.source_type in _PROSE_TYPES,
        system_note="prose_only baseline",
    )


# --- 4. majority evidence count --------------------------------------------


def majority_count_baseline(case: BenchmarkCase) -> AuditDecision:
    """Pick the parent named by the most evidence records; ties abstain."""
    declared, evidence, _ = case_inputs(case)
    counts: dict[str, int] = {}
    relation_of: dict[str, Relation | None] = {}
    for item in evidence:
        parent = item.candidate_parent or ""
        if not parent:
            continue
        counts[parent] = counts.get(parent, 0) + 1
        relation_of.setdefault(parent, item.relation)
    if not counts:
        return _decision(case, Decision.ABSTAIN, declared=declared,
                         summary="majority_count baseline: no evidence")
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return _decision(
            case, Decision.ABSTAIN, declared=declared,
            summary="majority_count baseline: tie between candidates, abstaining",
        )
    parent = ranked[0][0]
    relation = relation_of.get(parent)
    if not declared.base_models:
        action = Decision.ADD
    elif parent in declared.base_models:
        action = Decision.KEEP
    else:
        action = Decision.REPLACE
    return _decision(
        case, action, parents=(parent,), relation=relation, declared=declared,
        support=min(1.0, ranked[0][1] / 3.0),
        summary=f"majority_count baseline: {parent} has the most records ({ranked[0][1]})",
    )


# --- 5. fixed source hierarchy ---------------------------------------------


def rule_priority_baseline(case: BenchmarkCase) -> AuditDecision:
    """Use the highest-priority artifact only; no fusion or conflict logic."""
    declared, evidence, _ = case_inputs(case)
    best_priority = -1.0
    best_reliability = -1.0
    winner: EvidenceItem | None = None
    for item in evidence:
        priority = next(
            (value for kind, value in SOURCE_PRIORITY if kind is item.source_type), 0.0
        )
        reliability_rank = list(Reliability).index(item.reliability)
        key = (priority, reliability_rank)
        if key > (best_priority, best_reliability):
            best_priority, best_reliability = priority, float(reliability_rank)
            winner = item
    if winner is None or not winner.candidate_parent:
        return _decision(case, Decision.ABSTAIN, declared=declared,
                         summary="rule_priority baseline: no usable artifact")
    parent = winner.candidate_parent
    relation = winner.relation
    if not declared.base_models:
        action = Decision.ADD
    elif parent in declared.base_models:
        action = Decision.KEEP
    else:
        action = Decision.REPLACE
    return _decision(
        case, action, parents=(parent,), relation=relation, declared=declared,
        support=min(1.0, best_priority / 4.0),
        summary=f"rule_priority baseline: {winner.source_type.value} is the highest "
                "priority artifact present",
    )


# --- 6. trivial reference ---------------------------------------------------


def always_keep_baseline(case: BenchmarkCase) -> AuditDecision:
    """Trivial reference: propose the declaration unchanged, or abstain."""
    return declared_metadata_baseline(case)


class LLMOracleBaseline:
    """Optional interface for a full-context LLM strategy.

    Not a required test dependency: it needs live local inference, so it is
    only a documented extension point. The prompt asks the model for the whole
    lineage, and its answer is still converted into the same AuditDecision
    shape so metrics remain comparable.
    """

    name = "llm_full_context"

    def __init__(self, extractor, *, max_parents: int = 4) -> None:
        self._extractor = extractor
        self._max_parents = max_parents

    def run(self, case: BenchmarkCase) -> AuditDecision:
        declared = build_lineage(case)
        _, evidence, _ = case_inputs(case)
        prose = " ".join(
            item.evidence_span or ""
            for item in evidence
            if item.source_type in _PROSE_TYPES
        ).strip()
        if not prose:
            return _decision(case, Decision.ABSTAIN, declared=declared,
                             summary="llm_full_context: no prose to summarise")
        report = self._extractor.extract(prose, source_name="combined-prose",
                                        repository=case.repository)
        parents = tuple(dict.fromkeys(item.candidate_parent for item in report.evidence
                                      if item.candidate_parent))[: self._max_parents]
        if not parents:
            return _decision(
                case, Decision.ABSTAIN, declared=declared,
                summary="llm_full_context: no grounded claim was returned",
            )
        relation = report.evidence[0].relation
        if not declared.base_models:
            action = Decision.ADD
        elif set(parents) == set(declared.base_models):
            action = Decision.KEEP
        else:
            action = Decision.REPLACE
        return _decision(
            case, action, parents=parents, relation=relation, declared=declared,
            summary="llm_full_context: answer taken from grounded prose claims",
        )


BASELINES = {
    "declared_metadata": declared_metadata_baseline,
    "config_only": config_only_baseline,
    "prose_only": prose_only_baseline,
    "majority_count": majority_count_baseline,
    "rule_priority": rule_priority_baseline,
    "always_keep": always_keep_baseline,
}

BASELINE_NAMES = tuple(BASELINES)


def run_baseline(name: str, case: BenchmarkCase) -> CaseResult:
    """Evaluate one baseline on one case and score it like any other system."""
    decision = BASELINES[name](case)
    return score_decision(case, decision, system=name)
