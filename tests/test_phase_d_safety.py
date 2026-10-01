"""Phase D false-repair safety invariants and determinism properties.

These are the "must never happen" guarantees of the reasoning layer, plus the
properties that make the engine auditable: order-insensitivity, no duplicate
inflation, no weak-hint flips, and a bounded support score.
"""

from __future__ import annotations

import itertools
import random

import pytest

from fixtures.phase_d_evidence import (
    A,
    B,
    adapter_evidence,
    declared,
    declared_item,
    evidence,
    merge_evidence,
    training_evidence,
)
from provenancelens.reasoning import (
    DEFAULT_POLICY,
    CandidateMethod,
    aggregate_candidates,
    compute_support,
    decide_lineage,
)
from provenancelens.resolution import ResolutionStatus, resolve_identifier
from provenancelens.schemas import (
    ConflictKind,
    Decision,
    Explicitness,
    Reliability,
    SourceType,
)
from provenancelens.schemas.lineage import Relation


def decide(declared_lineage, items, *, issues=()):
    candidates = aggregate_candidates(list(items), issues=list(issues))
    return decide_lineage("org/target", declared_lineage, list(items), candidates=candidates)


# --- declared metadata is never its own proof --------------------------------


def test_declared_items_never_create_a_hypothesis():
    candidates = aggregate_candidates([
        declared_item(A, "finetune"),
        declared_item(B, "adapter", source_name="LICENSE"),
    ])
    assert candidates.hypotheses == ()
    assert candidates.has_usable_candidate is False


def test_declared_duplication_does_not_increase_support():
    declared_lineage = declared(A, "finetune")
    once = decide(declared_lineage, [adapter_evidence(A)])
    many = decide(
        declared_lineage,
        [adapter_evidence(A)] + [declared_item(A, "finetune", source_name=f"f{i}.md")
                                 for i in range(5)],
    )
    assert many.decision.support_score == once.decision.support_score
    assert many.decision.decision is once.decision.decision


def test_declared_metadata_alone_never_repairs():
    for decision_name in Decision:
        result = decide(declared(A, "finetune"), [declared_item(A, "finetune")])
        assert result.decision.decision is Decision.ABSTAIN


# --- missing corroboration vs contradiction ----------------------------------


def test_no_independent_evidence_always_abstains():
    result = decide(declared(), [declared_item(A)])
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.proposed_lineage.is_empty


def test_missing_corroboration_is_not_a_conflict():
    """A declared parent that no evidence mentions must not be a conflict."""
    result = decide(
        declared(B, "finetune"),
        [evidence(SourceType.README, "README.md", "org/model-c", Relation.FINETUNE,
                  Reliability.WEAK)],
    )
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.conflicts == []


def test_genuine_contradiction_is_reported_as_such():
    result = decide(declared(B, "finetune"), [adapter_evidence(A)])
    assert result.decision.decision is Decision.ABSTAIN
    assert any(
        conflict.kind is ConflictKind.DECLARED_VS_INDEPENDENT
        for conflict in result.decision.conflicts
    )


# --- weak evidence and name similarity --------------------------------------


def test_weak_name_similarity_only_never_changes_declared_lineage():
    result = decide(
        declared(A, "finetune"),
        [evidence(SourceType.README, "README.md", A + "-v2", Relation.FINETUNE, Reliability.WEAK)],
    )
    assert result.decision.decision is not Decision.REPLACE
    assert result.decision.recommended_patch is None


def test_organization_similarity_is_not_evidence():
    # "org/model-a" and "org2/model-a" are different models; no merging happens
    candidates = aggregate_candidates([adapter_evidence(A), adapter_evidence("org2/model-a",
                                                                           source_name="adapter_config_b.json")])
    assert {h.parents for h in candidates.hypotheses if h.method is CandidateMethod.SINGLE} == {
        (A,), ("org2/model-a",),
    }


def test_unresolved_model_id_blocks_when_resolution_is_required():
    result = decide(declared(), [training_evidence("some/local/checkpoint")])
    assert result.decision.decision is Decision.ABSTAIN


@pytest.mark.parametrize("raw", ["Mistral 7B", "llama-3-8b", "gpt2"])
def test_ambiguous_bare_names_never_resolve(raw: str):
    resolution = resolve_identifier(raw)
    assert resolution.resolved is None
    assert resolution.status in (
        ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNRESOLVED
    )


def test_ambiguous_version_forces_abstain_even_with_strong_tier():
    result = decide(
        declared(),
        [evidence(SourceType.ADAPTER_CONFIG, "adapter_config.json", "Mistral 7B",
                  "adapter", Reliability.VERY_HIGH, key_path="base_model_name_or_path")],
    )
    assert result.decision.decision is Decision.ABSTAIN


def test_multiple_incompatible_strong_candidates_never_pick_one():
    result = decide(
        declared(),
        [
            adapter_evidence(A),
            adapter_evidence(B, source_name="adapter_config_b.json"),
            adapter_evidence("org/model-c", source_name="adapter_config_c.json"),
        ],
    )
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.proposed_lineage.is_empty


# --- one strong source may support, never a repair of its own ----------------


def test_single_very_high_explicit_source_may_support_add():
    result = decide(declared(), [adapter_evidence(A)])
    assert result.decision.decision is Decision.ADD


def test_single_very_high_explicit_source_never_replaces():
    result = decide(declared(B, "finetune"), [adapter_evidence(A)])
    assert result.decision.decision is Decision.ABSTAIN


# --- merges -----------------------------------------------------------------


def test_incomplete_merge_never_replaces_a_complete_declared_set():
    result = decide(
        declared(A, "merge", (B, "org/model-c")),
        merge_evidence([A, B]),
    )
    assert result.decision.decision is not Decision.REPLACE
    assert result.decision.recommended_patch is None


def test_merge_candidate_order_does_not_change_comparison():
    forwards = decide(declared(A, "merge", (B,)), merge_evidence([A, B]))
    backwards = decide(declared(B, "merge", (A,)), merge_evidence([B, A]))
    assert forwards.decision.decision is backwards.decision.decision is Decision.KEEP
    assert set(forwards.decision.proposed_lineage.parents) == set(
        backwards.decision.proposed_lineage.parents
    )


def test_repeated_merge_source_is_one_source_not_several():
    """MergeKit lists one model in several slots: still a single source model."""
    candidates = aggregate_candidates([
        evidence(SourceType.MERGE_CONFIG, "mergekit_config.yml", A, "merge",
                 Reliability.HIGH, key_path="models[0].model"),
        evidence(SourceType.MERGE_CONFIG, "mergekit_config.yml", A, "merge",
                 Reliability.HIGH, key_path="models[1].model"),
        evidence(SourceType.MERGE_CONFIG, "mergekit_config.yml", B, "merge",
                 Reliability.HIGH, key_path="models[2].model"),
    ])
    merge = next(h for h in candidates.hypotheses if h.method is CandidateMethod.MERGE)
    assert set(merge.parents) == {A, B}
    assert merge.complete is True
    support = compute_support(merge, frozenset({A, B}))
    # one file is one source: repeating a model cannot inflate support
    assert support.support == pytest.approx(0.55)


def test_single_source_merge_is_not_a_merge_hypothesis_for_add():
    result = decide(declared(), merge_evidence([A]))
    assert result.decision.decision is Decision.ABSTAIN


# --- relations --------------------------------------------------------------


def test_relation_is_never_invented_from_a_parent_mention():
    result = decide(
        declared(),
        [evidence(SourceType.CONFIG, "config.json", A, None, Reliability.MEDIUM, key_path="_name_or_path")],
    )
    assert result.decision.proposed_lineage.is_empty


def test_training_config_parent_never_gains_an_invented_relation():
    """A training config names a parent but does not state the relationship."""
    result = decide(
        declared(),
        [training_evidence(A)],
    )
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.proposed_lineage.is_empty
    assert "no independent evidence establishes the transformation relation" in (
        result.decision.reasoning_summary
    )


# --- abstain never patches ---------------------------------------------------


@pytest.mark.parametrize("declared_lineage,items", [
    (declared(), []),
    (declared(A, "finetune"), [adapter_evidence(B)]),
    (declared(), [adapter_evidence(A), adapter_evidence(B, source_name="b.json")]),
    (declared(), [training_evidence("Mistral 7B")]),
    (declared(A, "finetune"), [declared_item(A, "finetune")]),
])
def test_abstain_never_proposes_a_patch(declared_lineage, items):
    result = decide(declared_lineage, items)
    if result.decision.decision is Decision.ABSTAIN:
        assert result.decision.recommended_patch is None
        assert result.decision.proposed_lineage.is_empty


# --- determinism / ordering properties --------------------------------------


def _sample_pool():
    return [
        adapter_evidence(A),
        training_evidence(A, relation=Relation.FINETUNE, key_path="base_model_or_path"),
        training_evidence(B, source_name="train_b.yaml", key_path="base_model_or_path"),
        evidence(SourceType.README, "README.md", A, Relation.FINETUNE, Reliability.MEDIUM),
        evidence(SourceType.CONFIG, "config.json", "org/model-c", None, Reliability.MEDIUM,
                 key_path="_name_or_path"),
        *merge_evidence([A, B]),
    ]


def test_evidence_order_does_not_change_the_decision():
    pool = _sample_pool()
    baseline = None
    for permutation in itertools.permutations(range(len(pool))):
        subset = [pool[i] for i in permutation]
        candidates = aggregate_candidates(subset)
        result = decide_lineage("org/target", declared(A, "finetune"), subset, candidates=candidates)
        signature = (
            result.decision.decision,
            round(result.decision.support_score, 6),
            result.decision.proposed_lineage.parents,
        )
        if baseline is None:
            baseline = signature
        assert signature == baseline, f"order changed the decision: {permutation}"


def test_duplicate_identical_evidence_does_not_inflate_support():
    single = decide(declared(), [adapter_evidence(A)])
    duplicated = decide(
        declared(),
        [adapter_evidence(A) for _ in range(5)],
    )
    assert duplicated.decision.support_score == single.decision.support_score
    assert duplicated.decision.decision is single.decision.decision


def test_repeating_one_file_with_three_fields_is_one_source():
    items = [
        evidence(SourceType.TRAINING_CONFIG, "train.yaml", A, None, Reliability.HIGH,
                 key_path="model_name_or_path"),
        evidence(SourceType.TRAINING_CONFIG, "train.yaml", A, None, Reliability.HIGH,
                 key_path="base_model"),
        evidence(SourceType.TRAINING_CONFIG, "train.yaml", A, None, Reliability.HIGH,
                 key_path="pretrained_model_name_or_path"),
    ]
    candidates = aggregate_candidates(items)
    support = compute_support(candidates.hypotheses[0], frozenset())
    assert support.support == pytest.approx(0.55)  # one file, one contribution


def test_adding_unrelated_weak_evidence_does_not_flip_a_strong_decision():
    base = decide(declared(), [adapter_evidence(A)])
    with_noise = decide(
        declared(),
        [
            adapter_evidence(A),
            evidence(SourceType.README, "NOTES.md", "org/unrelated-model",
                     Relation.FINETUNE, Reliability.WEAK),
        ],
    )
    assert with_noise.decision.decision is base.decision.decision is Decision.ADD
    assert with_noise.decision.proposed_lineage.parents == [A]


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_support_score_always_bounded_and_reproducible(seed: int):
    rng = random.Random(seed)
    pool = _sample_pool()
    for _ in range(25):
        subset = [
            rng.choice(pool).model_copy(deep=True)
            for _ in range(rng.randint(0, 6))
        ]
        candidates = aggregate_candidates(subset)
        for hypothesis in candidates.hypotheses:
            if not hypothesis.clusters:
                continue
            first = compute_support(hypothesis, frozenset({A, B}))
            assert 0.0 <= first.support <= 1.0
            again = compute_support(hypothesis, frozenset({A, B}))
            assert first.support == pytest.approx(again.support)
            # declared agreement never changes the score, only the flag
            other = compute_support(hypothesis, frozenset())
            assert other.support == pytest.approx(first.support)


def test_thresholds_are_documented_policy_constants():
    policy = DEFAULT_POLICY
    # the replace bar IS the decisive bar, and it is above the add/keep bar
    assert policy.min_support_replace == policy.min_support_decisive
    assert policy.min_support_replace > policy.min_support_affirmative > 0
    assert policy.min_support_keep == policy.min_support_add
    assert policy.min_support_affirmative <= policy.min_support_keep
    # no single very_high artifact may reach the replace bar
    single = compute_support(
        aggregate_candidates([adapter_evidence(A)]).hypotheses[0]
    )
    assert single.support < policy.min_support_replace
