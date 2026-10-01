"""Phase D controlled decision cases (14 specified scenarios + variants).

Each case uses Phase 3 structured :class:`EvidenceItem` objects, never the
Phase 2 string bundles, so the new engine is tested on the evidence type it
actually consumes.
"""

from __future__ import annotations

import pytest

from fixtures.phase_d_evidence import (
    A,
    B,
    C,
    adapter_evidence,
    declared,
    declared_item,
    evidence,
    issue,
    merge_evidence,
    training_evidence,
)
from provenancelens.schemas import (
    ConflictKind,
    Decision,
    Explicitness,
    Reliability,
    SourceType,
)
from provenancelens.schemas.lineage import Relation


def decide(declared_lineage, items, *, issues=()):
    from provenancelens.reasoning import aggregate_candidates, decide_lineage

    candidates = aggregate_candidates(list(items), issues=list(issues))
    return decide_lineage("org/target", declared_lineage, list(items), candidates=candidates)


# --- CASE 1: KEEP -----------------------------------------------------------


def test_case1_keep_when_independent_evidence_supports_declared_lineage():
    result = decide(
        declared(A, "finetune"),
        [
            training_evidence(A, relation=Relation.FINETUNE),
            evidence(SourceType.README, "README.md", A, Relation.FINETUNE, Reliability.MEDIUM),
        ],
    )
    decision = result.decision
    assert decision.decision is Decision.KEEP
    assert decision.proposed_lineage.parents == [A]
    assert decision.support_score >= 0.55
    assert decision.conflicts == []
    assert decision.recommended_patch is None
    assert "KEEP" in decision.reasoning_summary


def test_case1b_declared_metadata_alone_is_not_keep():
    """The declared claim exists, but nothing independent supports it."""
    result = decide(declared(A, "finetune"), [declared_item(A, "finetune")])
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.recommended_patch is None


# --- CASE 2: ADD from one very-high source ----------------------------------


def test_case2_add_from_single_very_high_adapter_source():
    result = decide(declared(), [adapter_evidence(A)])
    decision = result.decision
    assert decision.decision is Decision.ADD
    assert decision.proposed_lineage.parents == [A]
    assert decision.proposed_lineage.entries[0].relation is Relation.ADAPTER
    assert decision.support_score == pytest.approx(0.75)
    patch = decision.recommended_patch
    assert patch is not None
    assert patch.new_base_model == A
    assert patch.new_relation is Relation.ADAPTER
    assert patch.old_base_model is None


def test_case2b_phase2_two_source_rule_is_gone():
    """Exactly one independent source is enough when it is explicit and strong."""
    result = decide(declared(), [adapter_evidence(A)])
    assert result.decision.decision is Decision.ADD
    sources = {item.source_name for item in result.decision.supporting_evidence}
    assert len(sources) == 1


# --- CASE 3: REPLACE --------------------------------------------------------


def test_case3_replace_when_strong_evidence_contradicts_declared_lineage():
    result = decide(
        declared(A, "finetune"),
        [
            adapter_evidence(B),
            training_evidence(B, relation=Relation.FINETUNE, key_path="base_model_or_path"),
        ],
    )
    decision = result.decision
    assert decision.decision is Decision.REPLACE
    assert decision.proposed_lineage.parents == [B]
    assert decision.support_score == pytest.approx(1.0)
    assert decision.recommended_patch is not None
    assert decision.recommended_patch.old_base_model == A
    assert decision.recommended_patch.new_base_model == B
    assert any(c.kind is ConflictKind.DECLARED_VS_INDEPENDENT for c in decision.conflicts)


def test_case3b_single_very_high_source_never_replaces():
    result = decide(declared(A, "finetune"), [adapter_evidence(B)])
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.proposed_lineage.is_empty
    assert result.decision.recommended_patch is None
    assert "0.90" in result.decision.reasoning_summary


def test_case3c_config_name_or_path_alone_never_replaces():
    result = decide(
        declared(A, "finetune"),
        [evidence(SourceType.CONFIG, "config.json", B, None, Reliability.MEDIUM, key_path="_name_or_path")],
    )
    assert result.decision.decision is Decision.ABSTAIN


# --- CASE 4: weak conflict ---------------------------------------------------


def test_case4_weak_hint_against_declared_never_repairs():
    """Declared A + a HIGH config for A + one WEAK prose hint naming B.

    The declared lineage is independently corroborated and the WEAK hint is
    below the conflict bar, so the engine keeps the metadata unchanged - a
    conservative non-repair. It must never become a REPLACE.
    """
    result = decide(
        declared(A, "finetune"),
        [
            training_evidence(A, relation=Relation.FINETUNE, key_path="base_model_or_path"),
            evidence(SourceType.README, "README.md", B, Relation.FINETUNE, Reliability.WEAK),
        ],
    )
    decision = result.decision
    assert decision.decision is not Decision.REPLACE
    assert decision.decision in (Decision.KEEP, Decision.ABSTAIN)
    assert decision.recommended_patch is None
    assert decision.proposed_lineage.parents in ([A], [])


def test_case4b_single_weak_phrase_against_declared_is_never_replace():
    result = decide(
        declared(A, "finetune"),
        [evidence(SourceType.README, "README.md", B, Relation.FINETUNE, Reliability.WEAK)],
    )
    assert result.decision.decision is Decision.ABSTAIN


# --- CASE 5: no evidence -----------------------------------------------------


def test_case5_no_evidence_abstains():
    result = decide(declared(A, "finetune"), [])
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.support_score == 0.0
    assert result.decision.proposed_lineage.is_empty
    assert result.decision.recommended_patch is None
    assert result.decision.supporting_evidence == []


def test_case5b_no_evidence_and_no_declaration_abstains():
    result = decide(declared(), [])
    assert result.decision.decision is Decision.ABSTAIN


# --- CASE 6: multiple strong candidates --------------------------------------


def test_case6_multiple_strong_candidates_abstain():
    result = decide(
        declared(),
        [adapter_evidence(A), adapter_evidence(B, source_name="adapter_config_b.json")],
    )
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert decision.proposed_lineage.is_empty
    assert any(c.kind is ConflictKind.COMPETING_CANDIDATES for c in decision.conflicts)
    assert decision.contradictory_evidence


# --- CASE 7: version ambiguity ----------------------------------------------


def test_case7_unresolvable_bare_name_abstains():
    result = decide(
        declared(),
        [training_evidence("Mistral 7B")],
    )
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert any(c.kind is ConflictKind.VERSION_AMBIGUITY for c in decision.conflicts)


def test_case7b_ambiguity_blocks_keep_too():
    result = decide(
        declared(A, "finetune"),
        [
            training_evidence(A, relation=Relation.FINETUNE, key_path="base_model_or_path"),
            training_evidence(
                "Mistral 7B", source_name="train_eval.yaml", key_path="model_name_or_path",
            ),
        ],
    )
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert any(c.kind is ConflictKind.VERSION_AMBIGUITY for c in decision.conflicts)


# --- CASE 8: config parent without relation ---------------------------------


def test_case8_config_parent_without_relation_abstains():
    result = decide(
        declared(),
        [evidence(SourceType.CONFIG, "config.json", A, None, Reliability.MEDIUM, key_path="_name_or_path")],
    )
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert decision.support_score == pytest.approx(0.30)
    assert decision.proposed_lineage.is_empty
    assert decision.recommended_patch is None


def test_case8b_unsupported_relation_is_never_invented():
    result = decide(
        declared(),
        [
            adapter_evidence(A),
            evidence(SourceType.TRAINING_CONFIG, "train.yaml", A, None, Reliability.HIGH, key_path="model_name_or_path"),
        ],
    )
    # adapter relation is established; the hint never adds a different one
    assert result.decision.proposed_lineage.entries[0].relation is Relation.ADAPTER


# --- CASE 9 / 10 / 11: merges ----------------------------------------------


def test_case9_merge_exact_match_keeps():
    result = decide(declared(A, "merge", (B,)), merge_evidence([A, B]))
    decision = result.decision
    assert decision.decision is Decision.KEEP
    assert sorted(decision.proposed_lineage.parents) == sorted([A, B])
    assert decision.proposed_lineage.entries[0].relation is Relation.MERGE
    assert decision.recommended_patch is None


def test_case10_merge_without_declaration_adds():
    result = decide(declared(), merge_evidence([A, B]))
    decision = result.decision
    assert decision.decision is Decision.ADD
    assert sorted(decision.proposed_lineage.parents) == sorted([A, B])
    assert all(entry.relation is Relation.MERGE for entry in decision.proposed_lineage.entries)
    assert decision.recommended_patch is not None


def test_case11_incomplete_merge_evidence_never_replaces():
    result = decide(declared(A, "merge", (B, C)), merge_evidence([A, B]))
    decision = result.decision
    assert decision.decision is not Decision.REPLACE
    assert decision.recommended_patch is None
    # the declared set is preserved (not narrowed to the observed subset)
    assert sorted(decision.proposed_lineage.parents) == sorted([A, B, C]) or decision.proposed_lineage.is_empty


def test_case11b_incomplete_merge_with_unknown_declared_relation_abstains():
    result = decide(declared(A, "blend", (B, C)), merge_evidence([A, B]))
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert any(
        c.kind is ConflictKind.UNKNOWN_DECLARED_RELATION for c in decision.conflicts
    )


def test_case11c_single_source_merge_config_is_not_a_merge_add():
    result = decide(declared(), merge_evidence([A]))
    assert result.decision.decision is Decision.ABSTAIN


# --- CASE 12: relation conflict ---------------------------------------------


def test_case12_relation_conflict_is_structured_and_conservative():
    result = decide(declared(A, "finetune"), [adapter_evidence(A)])
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert any(c.kind is ConflictKind.RELATION_CONFLICT for c in decision.conflicts)
    assert decision.recommended_patch is None


def test_case12b_decisive_relation_conflict_repairs_only_the_relation():
    result = decide(
        declared(A, "finetune"),
        [
            adapter_evidence(A),
            training_evidence(A, relation=Relation.ADAPTER, key_path="base_model_or_path"),
        ],
    )
    decision = result.decision
    assert decision.decision is Decision.REPLACE
    assert decision.proposed_lineage.parents == [A]  # parent unchanged
    assert decision.proposed_lineage.entries[0].relation is Relation.ADAPTER
    assert "relation only" in decision.reasoning_summary


# --- CASE 13 / 14: tool and parser failures ---------------------------------


def test_case13_tool_failure_does_not_block_strong_evidence():
    result = decide(declared(), [adapter_evidence(A)], issues=[issue()])
    decision = result.decision
    assert decision.decision is Decision.ADD
    assert decision.proposed_lineage.parents == [A]
    assert any(c.kind is ConflictKind.TOOL_FAILURE for c in decision.conflicts)


def test_case14_tool_failure_with_weak_evidence_abstains():
    result = decide(
        declared(),
        [evidence(SourceType.README, "README.md", A, Relation.FINETUNE, Reliability.MEDIUM)],
        issues=[issue()],
    )
    decision = result.decision
    assert decision.decision is Decision.ABSTAIN
    assert any(c.kind is ConflictKind.TOOL_FAILURE for c in decision.conflicts)


def test_parser_failure_issue_is_never_decided_by_itself():
    """A failure alone changes no decision: the same evidence decides the same way."""
    strong = [adapter_evidence(A)]
    weak = [evidence(SourceType.README, "README.md", A, Relation.FINETUNE, Reliability.MEDIUM)]
    with_failure_strong = decide(declared(), strong, issues=[issue()])
    without_failure_strong = decide(declared(), strong)
    assert (
        with_failure_strong.decision.decision
        is without_failure_strong.decision.decision
    )
    with_failure_weak = decide(declared(), weak, issues=[issue()])
    without_failure_weak = decide(declared(), weak)
    assert (
        with_failure_weak.decision.decision
        is without_failure_weak.decision.decision
    )


# --- extras: warnings vs errors, unsupported relations ----------------------


def test_warning_issue_does_not_become_a_tool_failure_conflict():
    result = decide(
        declared(), [adapter_evidence(A)],
        issues=[issue(message="rejected local path", severity="warning")],
    )
    assert not any(
        c.kind is ConflictKind.TOOL_FAILURE for c in result.decision.conflicts
    )


def test_implicit_explicitness_halves_item_weight():
    explicit = decide(declared(), [adapter_evidence(A)])
    implicit = decide(
        declared(),
        [evidence(
            SourceType.ADAPTER_CONFIG, "adapter_config.json", A, Relation.ADAPTER,
            Reliability.VERY_HIGH, key_path="base_model_name_or_path",
            explicitness=Explicitness.IMPLICIT,
        )],
    )
    assert explicit.decision.support_score == pytest.approx(0.75)
    assert implicit.decision.support_score == pytest.approx(0.375)
    assert implicit.decision.decision is Decision.ABSTAIN
