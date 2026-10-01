"""Corrected Phase 3 primitives: schemas, vocabulary, evidence roles."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from provenancelens.schemas import (
    AuditDecision,
    Conflict,
    ConflictKind,
    Decision,
    DeclaredLineage,
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Lineage,
    LineageEntry,
    Relation,
    Reliability,
    SuggestedPatch,
    SourceType,
    is_plausible_model_id,
    split_by_role,
)


def _declared_item() -> EvidenceItem:
    return EvidenceItem(
        source_type=SourceType.DECLARED_METADATA,
        role=EvidenceRole.DECLARED,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        reliability=Reliability.NOT_APPLICABLE,
        candidate_parent="org/wrong-parent",
        relation=Relation.FINETUNE,
    )


def _independent_item(parent: str = "org/right-parent") -> EvidenceItem:
    return EvidenceItem(
        source_type=SourceType.CONFIG,
        role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        reliability=Reliability.MEDIUM,
        candidate_parent=parent,
    )


# --- relation vocabulary ----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("fine-tune", Relation.FINETUNE),
        ("finetune", Relation.FINETUNE),
        ("fine_tune", Relation.FINETUNE),
        ("Fine Tuned", Relation.FINETUNE),
        ("FINETUNED", Relation.FINETUNE),
        ("adapter", Relation.ADAPTER),
        ("merged", Relation.MERGE),
        ("quantization", Relation.QUANTIZED),
        ("quantised", Relation.QUANTIZED),
    ],
)
def test_relation_normalizes_known_variants(raw, expected):
    assert Relation.normalize(raw) is expected


@pytest.mark.parametrize("raw", [None, "", "teleport", "supervised", 42, ["finetune"]])
def test_relation_rejects_unknown_values(raw):
    assert Relation.normalize(raw) is None


def test_legacy_fine_tune_label_normalizes_to_canonical():
    """Phase 2's `fine-tune` maps to canonical `finetune` at the boundary."""
    assert Relation.normalize("fine-tune") is Relation.FINETUNE
    assert Relation.FINETUNE.value == "finetune"


def test_unknown_declared_relation_is_kept_raw_but_not_valid():
    declared = DeclaredLineage.from_metadata(
        {"base_model": "org/model", "base_model_relation": "twirls-into"}
    )
    assert declared.relation_raw == "twirls-into"
    assert declared.relation is None


def test_evidence_relation_field_rejects_raw_strings():
    with pytest.raises(ValidationError):
        EvidenceItem(
            source_type=SourceType.README,
            role=EvidenceRole.INDEPENDENT,
            extraction_method=ExtractionMethod.RULE_BASED,
            reliability=Reliability.MEDIUM,
            relation="bogus-relation",  # type: ignore[arg-type]
        )


# --- declared vs independent roles ----------------------------------------


def test_declared_metadata_is_never_independent():
    declared, item = _declared_item(), None
    independent = _independent_item()
    declared_list, independent_list = split_by_role([declared, independent])
    assert declared_list == [declared]
    assert independent_list == [independent]
    assert declared.role is EvidenceRole.DECLARED
    assert independent.role is EvidenceRole.INDEPENDENT


def test_evidence_item_requires_role_and_reliability():
    """Support-relevant fields cannot be silently defaulted."""
    with pytest.raises(ValidationError):
        EvidenceItem(
            source_type=SourceType.CONFIG,
            extraction_method=ExtractionMethod.DETERMINISTIC,
            reliability=Reliability.MEDIUM,
        )
    with pytest.raises(ValidationError):
        EvidenceItem(
            source_type=SourceType.CONFIG,
            role=EvidenceRole.INDEPENDENT,
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )


def test_evidence_item_retains_source_information():
    item = EvidenceItem(
        source_type=SourceType.ADAPTER_CONFIG,
        source_name="adapter_config.json",
        repository="org/model",
        revision="abc123",
        role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        reliability=Reliability.VERY_HIGH,
        candidate_parent="org/base-model",
        relation=Relation.ADAPTER,
        raw_value="org/base-model",
        evidence_span='"base_model_name_or_path": "org/base-model"',
        explicitness=Explicitness.EXPLICIT,
        source_url="https://huggingface.co/org/model/resolve/abc123/adapter_config.json",
    )
    assert item.source_type is SourceType.ADAPTER_CONFIG
    assert item.source_name == "adapter_config.json"
    assert item.repository == "org/model"
    assert item.revision == "abc123"
    assert item.candidate_parent == "org/base-model"
    assert item.relation is Relation.ADAPTER
    assert item.extraction_method is ExtractionMethod.DETERMINISTIC
    assert item.explicitness is Explicitness.EXPLICIT
    assert item.reliability is Reliability.VERY_HIGH
    assert item.source_url.startswith("https://")


def test_evidence_item_does_not_force_meaningless_values():
    item = _independent_item()
    assert item.repository is None
    assert item.revision is None
    assert item.source_url is None
    assert item.evidence_span is None


# --- model id plausibility --------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["org/model", "Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.2-1B"],
)
def test_plausible_model_ids_accepted(value):
    assert is_plausible_model_id(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "bare-model-name",
        "/absolute/path/model",
        "a/b/c",
        "checkpoints/epoch1.pt",
        "configs/train.json",
        "my org/model",
        "",
        None,
        42,
    ],
)
def test_non_model_ids_rejected(value):
    assert is_plausible_model_id(value) is False


# --- lineage ---------------------------------------------------------------


def test_lineage_represents_multiple_merge_sources():
    lineage = Lineage(
        entries=[
            LineageEntry(parent="org/model-a", relation=Relation.MERGE),
            LineageEntry(parent="org/model-b", relation=Relation.MERGE),
            LineageEntry(parent="org/model-c", relation=Relation.MERGE),
        ]
    )
    assert lineage.parents == ["org/model-a", "org/model-b", "org/model-c"]
    assert not lineage.is_empty
    assert len(lineage.entries) == 3


def test_lineage_single_and_empty():
    assert Lineage.single("org/base", Relation.FINETUNE).parents == ["org/base"]
    assert Lineage().is_empty


def test_declared_lineage_normalizes_at_boundary():
    declared = DeclaredLineage.from_metadata(
        {"base_model": "org/model", "base_model_relation": "fine-tune"}
    )
    assert declared.base_model == "org/model"
    assert declared.relation_raw == "fine-tune"
    assert declared.relation is Relation.FINETUNE


def test_declared_lineage_handles_missing_and_malformed_metadata():
    assert DeclaredLineage.from_metadata(None).base_model is None
    assert DeclaredLineage.from_metadata({}).base_model is None
    weird = DeclaredLineage.from_metadata({"base_model": {"nested": True}, "base_model_relation": 7})
    assert weird.base_model is None
    assert weird.relation is None
    assert weird.relation_raw is None


# --- audit decision ---------------------------------------------------------


def test_abstain_with_no_evidence_is_representable():
    decision = AuditDecision.abstain(
        model_id="org/model",
        current_lineage=DeclaredLineage(),
        reasoning_summary="No evidence available.",
        conflicts=[
            Conflict(kind=ConflictKind.TOOL_FAILURE, description="README retrieval failed"),
        ],
    )
    assert decision.decision is Decision.ABSTAIN
    assert decision.supporting_evidence == []
    assert decision.proposed_lineage.is_empty
    assert decision.recommended_patch is None
    assert decision.conflicts[0].kind is ConflictKind.TOOL_FAILURE


def test_abstain_may_not_propose_or_patch():
    with pytest.raises(ValidationError):
        AuditDecision(
            model_id="org/model",
            current_lineage=DeclaredLineage(),
            decision=Decision.ABSTAIN,
            proposed_lineage=Lineage.single("org/parent", Relation.FINETUNE),
            support_score=0.4,
            reasoning_summary="inconsistent",
        )
    with pytest.raises(ValidationError):
        AuditDecision(
            model_id="org/model",
            current_lineage=DeclaredLineage(),
            decision=Decision.ABSTAIN,
            support_score=0.4,
            reasoning_summary="inconsistent",
            recommended_patch=SuggestedPatch(new_base_model="org/parent"),
        )


def test_non_abstain_requires_a_proposal():
    with pytest.raises(ValidationError):
        AuditDecision(
            model_id="org/model",
            current_lineage=DeclaredLineage(),
            decision=Decision.ADD,
            support_score=0.7,
            reasoning_summary="missing proposal",
        )


def test_support_score_bounds():
    with pytest.raises(ValidationError):
        AuditDecision(
            model_id="org/model",
            current_lineage=DeclaredLineage(),
            decision=Decision.ADD,
            proposed_lineage=Lineage.single("org/parent", Relation.FINETUNE),
            support_score=1.5,
            reasoning_summary="out of range",
        )


def test_suggested_patch_requires_a_new_value():
    with pytest.raises(ValidationError):
        SuggestedPatch(old_base_model="org/old")
    patch = SuggestedPatch(old_base_model="org/old", new_base_model="org/new")
    assert patch.new_base_model == "org/new"
