"""Corrected extraction primitives: configs, prose, declared, bundle."""

from __future__ import annotations

from provenancelens.parsers import (
    extract_config_evidence,
    extract_declared,
    extract_declared_metadata,
    extract_independent_evidence,
    extract_prose_claims,
)
from provenancelens.schemas import (
    AuditDecision,
    DeclaredLineage,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Relation,
    Reliability,
    SourceType,
    split_by_role,
)


# --- config extraction ------------------------------------------------------


def test_config_evidence_retains_source_information():
    items = extract_config_evidence({"_name_or_path": "org/base-model"})
    assert len(items) == 1
    item = items[0]
    assert item.source_type is SourceType.CONFIG
    assert item.source_name == "config.json"
    assert item.role is EvidenceRole.INDEPENDENT
    assert item.extraction_method is ExtractionMethod.DETERMINISTIC
    assert item.candidate_parent == "org/base-model"
    assert item.reliability is Reliability.MEDIUM


def test_config_evidence_does_not_inherit_declared_relation():
    """CRITICAL: config evidence must never copy the declared relation."""
    declared_lineage, declared_item = extract_declared_metadata(
        {"base_model": "org/wrong", "base_model_relation": "fine-tune"}
    )
    assert declared_lineage.relation is Relation.FINETUNE
    assert declared_item is not None and declared_item.role is EvidenceRole.DECLARED

    items = extract_config_evidence({"_name_or_path": "org/candidate"})
    assert len(items) == 1
    assert items[0].relation is None
    assert items[0].role is EvidenceRole.INDEPENDENT


def test_config_extracts_multiple_lineage_keys():
    items = extract_config_evidence(
        {
            "_name_or_path": "org/base-a",
            "model_name_or_path": "org/base-a",
            "pretrained_model_name_or_path": "org/base-b",
        }
    )
    parents = [item.candidate_parent for item in items]
    assert parents == ["org/base-a", "org/base-b"]  # deduplicated per source


def test_config_skips_non_model_values():
    items = extract_config_evidence(
        {
            "_name_or_path": "/local/path/llama",
            "model_name_or_path": "checkpoints/epoch3.pt",
            "base_model": "bare-name-no-slash",
        }
    )
    assert items == []


# --- prose extraction -------------------------------------------------------


def test_prose_extracts_explicit_claims_with_spans():
    text = "This model was fine-tuned from org/base-model for instruction following."
    items = extract_prose_claims(text)
    assert len(items) == 1
    item = items[0]
    assert item.candidate_parent == "org/base-model"
    assert item.relation is Relation.FINETUNE
    assert item.role is EvidenceRole.INDEPENDENT
    assert item.extraction_method is ExtractionMethod.RULE_BASED
    assert item.explicitness is Explicitness.EXPLICIT
    assert item.reliability is Reliability.MEDIUM
    assert item.source_name == "README.md"
    assert item.evidence_span is not None
    assert "fine-tuned from" in item.evidence_span


def test_prose_extracts_multiple_relations():
    text = (
        "The model was fine-tuned from org/base-model and later "
        "quantized from org/base-quantized."
    )
    items = extract_prose_claims(text)
    pairs = {(item.candidate_parent, item.relation) for item in items}
    assert ("org/base-model", Relation.FINETUNE) in pairs
    assert ("org/base-quantized", Relation.QUANTIZED) in pairs


def test_prose_mere_mention_yields_no_claim():
    """Discussing another model without establishing ancestry -> NO_CLAIM."""
    text = "We compare against org/other-model and thank the org/acknowledgements team."
    assert extract_prose_claims(text) == []


def test_prose_rejects_non_model_paths():
    text = "The model was trained on top of checkpoints/epoch1.pt."
    assert extract_prose_claims(text) == []
    text2 = "The model was trained on top of configs/train.json."
    assert extract_prose_claims(text2) == []


def test_prose_missing_or_malformed_input_is_safe():
    assert extract_prose_claims("") == []
    assert extract_prose_claims(None) == []
    assert extract_prose_claims(123) == []


def test_prose_relation_normalizes_canonically():
    """New extraction emits canonical `finetune`, not legacy `fine-tune`."""
    items = extract_prose_claims("Fine-tuned from org/base-model.")
    assert items[0].relation is Relation.FINETUNE
    assert items[0].relation.value == "finetune"


# --- declared metadata ------------------------------------------------------


def test_declared_metadata_is_marked_as_subject():
    lineage, item = extract_declared_metadata(
        {"base_model": "org/base", "base_model_relation": "fine-tune"}
    )
    assert lineage.relation is Relation.FINETUNE
    assert item is not None
    assert item.role is EvidenceRole.DECLARED
    assert item.reliability is Reliability.NOT_APPLICABLE
    assert item.relation_raw == "fine-tune"


def test_declared_metadata_without_base_model_returns_no_evidence():
    lineage, item = extract_declared_metadata({"base_model": None})
    assert lineage.base_model is None
    assert item is None


# --- bundle extraction ------------------------------------------------------


def test_bundle_independent_evidence_excludes_declared_metadata():
    """CRITICAL: declared metadata never leaks into independent evidence."""
    bundle = {
        "model_id": "org/audited-model",
        "metadata": {"base_model": "org/wrong-declared", "base_model_relation": "fine-tune"},
        "config": {"_name_or_path": "org/config-parent"},
        "readme": "This model was fine-tuned from org/readme-parent.",
        "tool_errors": [],
    }
    declared_lineage, declared_item = extract_declared(bundle)
    independent = extract_independent_evidence(bundle)

    assert declared_lineage.base_model == "org/wrong-declared"
    assert declared_item is not None

    assert len(independent) == 2
    assert all(item.role is EvidenceRole.INDEPENDENT for item in independent)
    assert {item.candidate_parent for item in independent} == {
        "org/config-parent",
        "org/readme-parent",
    }
    assert "org/wrong-declared" not in {item.candidate_parent for item in independent}

    declared_list, independent_again = split_by_role([declared_item, *independent])
    assert declared_list == [declared_item]
    assert independent_again == independent


def test_bundle_repository_id_propagates_to_evidence():
    bundle = {
        "model_id": "org/audited-model",
        "metadata": {},
        "config": {"_name_or_path": "org/base"},
        "readme": "",
        "tool_errors": [],
    }
    items = extract_independent_evidence(bundle)
    assert all(item.repository == "org/audited-model" for item in items)


def test_malformed_bundle_is_safe():
    assert extract_independent_evidence(None) == []
    assert extract_independent_evidence("not a mapping") == []
    assert extract_declared(None) == (DeclaredLineage(), None)
    assert extract_independent_evidence({"config": None, "readme": None}) == []


def test_no_evidence_supports_safe_abstention_result():
    """NO EVIDENCE -> ABSTAIN is representable with structured output."""
    lineage, _ = extract_declared({"metadata": {}})
    decision = AuditDecision.abstain(
        model_id="org/model",
        current_lineage=lineage,
        reasoning_summary="No independent evidence found.",
    )
    assert decision.supporting_evidence == []
    assert decision.conflicts == []
    assert decision.recommended_patch is None
