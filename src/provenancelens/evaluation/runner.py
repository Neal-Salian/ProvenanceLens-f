"""Evaluation runner: benchmark cases -> production decisions -> case results.

The runner never modifies the decision engine. It builds the same inputs the
production pipeline uses (declared lineage + structured evidence + extraction
issues) and records what the engine decided, plus how that decision compares
with the adjudicated label.

Scoring semantics used throughout:

* ``action_scored`` - the case has a binding expected action; ambiguous cases
  accept any action in ``acceptable_actions`` and are still scored, but they
  are also reported separately so abstention is never hidden.
* ``parent_scored`` - only when truth parents are KNOWN; multi-parent truth is
  compared as a *set*.
* ``false_repair`` - the system attempted ADD/REPLACE and the proposed lineage
  contradicts known truth (``None`` when the truth is not knowable).
"""

from __future__ import annotations

from ..parsers import extract_repository_evidence
from ..reasoning import DEFAULT_POLICY, DecisionPolicy, decide_lineage
from ..resolution import resolve_identifier
from ..schemas.audit import AuditDecision, Decision
from ..schemas.extraction import ExtractionIssue
from ..schemas.lineage import DeclaredLineage, Lineage, LineageEntry, Relation
from .schema import BenchmarkCase, CaseResult, TruthStatus

__all__ = ["case_inputs", "run_case", "build_lineage"]


def build_lineage(case: BenchmarkCase) -> DeclaredLineage:
    """Declared lineage exactly as the repository states it."""
    additional = list(case.declared_additional_base_models)
    return DeclaredLineage(
        base_model=case.declared_base_model,
        additional_base_models=additional,
        relation_raw=case.declared_relation_raw,
        relation=Relation.normalize(case.declared_relation_raw),
    )


def case_inputs(case: BenchmarkCase) -> tuple[DeclaredLineage, list, list[ExtractionIssue]]:
    """(declared lineage, evidence items, extraction issues) for one case."""
    declared = build_lineage(case)
    evidence = list(case.evidence)
    if case.snapshot_files:
        extraction = extract_repository_evidence(
            case.repository or case.case_id, case.snapshot_commit or "", case.snapshot_files
        )
        evidence = [*extraction.declared_evidence, *extraction.independent_evidence]
    issues = [ExtractionIssue(**issue) for issue in case.issues]
    return declared, evidence, issues


def _canonical(parents: tuple[str, ...]) -> frozenset[str]:
    resolved: set[str] = set()
    for parent in parents:
        resolution = resolve_identifier(parent)
        resolved.add(resolution.resolved or parent)
    return frozenset(resolved)


def _proposed(lineage: Lineage) -> tuple[tuple[str, ...], Relation | None]:
    parents = _canonical(tuple(lineage.parents))
    relations = {entry.relation for entry in lineage.entries} - {None}
    relation = next(iter(relations)) if len(relations) == 1 else None
    return tuple(sorted(parents)), relation


def score_decision(
    case: BenchmarkCase, decision: AuditDecision, *, system: str
) -> CaseResult:
    """Compare one production decision with the adjudicated label."""
    truth = case.truth
    expected_parents = tuple(sorted(_canonical(truth.parents))) if truth.parents else ()
    predicted_parents, predicted_relation = _proposed(decision.proposed_lineage)

    abstained = decision.decision is Decision.ABSTAIN
    repair_attempted = decision.decision in (Decision.ADD, Decision.REPLACE)

    action_scored = True
    action_correct = decision.decision in case.acceptable_actions

    parent_scored = truth.parents_status is TruthStatus.KNOWN and truth.parents is not None
    parent_correct = (frozenset(predicted_parents) == frozenset(expected_parents)
                      if parent_scored else None)

    relation_scored = truth.relation_status is TruthStatus.KNOWN and truth.relation is not None
    relation_correct = (
        (predicted_relation is truth.relation) if relation_scored else None
    )

    # Repair correctness only means something when truth is knowable. An attempt
    # on non-knowable truth is UNVERIFIABLE: it is neither credited nor blamed,
    # and it must be visible in its own counter (never folded into "correct").
    repair_verifiable = repair_attempted and parent_scored
    repair_correct = (
        (frozenset(predicted_parents) == frozenset(expected_parents))
        if repair_verifiable else None
    )
    false_repair = (
        (not repair_correct) if repair_verifiable
        else (None if repair_attempted else False)
    )

    return CaseResult(
        case_id=case.case_id,
        track=case.track,
        system=system,
        expected_action=case.expected_action,
        acceptable_actions=case.acceptable_actions,
        predicted_action=decision.decision,
        expected_parents=expected_parents,
        predicted_parents=predicted_parents,
        expected_relation=truth.relation,
        predicted_relation=predicted_relation,
        support_score=decision.support_score,
        conflicts=tuple(decision.conflicts),
        abstained=abstained,
        repair_attempted=repair_attempted,
        action_scored=action_scored,
        action_correct=action_correct,
        parent_scored=parent_scored,
        parent_correct=parent_correct,
        relation_scored=relation_scored,
        relation_correct=relation_correct,
        repair_verifiable=repair_verifiable,
        repair_correct=repair_correct,
        false_repair=false_repair,
        reasoning_summary=decision.reasoning_summary,
    )


def decide_case(
    case: BenchmarkCase, *, policy: DecisionPolicy = DEFAULT_POLICY, extra_evidence=None
) -> AuditDecision:
    """Run the unmodified production engine on one benchmark case."""
    declared, evidence, issues = case_inputs(case)
    evidence = [*evidence, *(extra_evidence or [])]
    candidates = None
    if issues or extra_evidence:
        from ..reasoning import aggregate_candidates

        candidates = aggregate_candidates(evidence, issues=issues)
    result = decide_lineage(
        case.repository or case.case_id,
        declared,
        evidence,
        policy=policy,
        candidates=candidates,
    )
    return result.decision


def run_case(
    case: BenchmarkCase, *, system: str = "provenancelens",
    policy: DecisionPolicy = DEFAULT_POLICY, extra_evidence=None,
) -> CaseResult:
    decision = decide_case(case, policy=policy, extra_evidence=extra_evidence)
    return score_decision(case, decision, system=system)


_ = LineageEntry  # re-exported implicitly through Lineage
