"""Phase 3 deterministic extraction: front matter, adapter, training, merge,
bundle routing, and the declared-vs-independent architectural invariant."""

from __future__ import annotations

import pytest

from provenancelens.parsers import (
    extract_adapter_evidence,
    extract_declared_from_readme,
    extract_merge_evidence,
    extract_repository_evidence,
    extract_training_evidence,
    split_front_matter,
)
from provenancelens.schemas import (
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Relation,
    Reliability,
    SourceType,
    is_plausible_model_id,
)
from provenancelens.schemas.extraction import EvidenceExtraction

SHA = "e" * 40
REPO = "org/model"


# --- README front matter (DECLARED) ----------------------------------------


def test_front_matter_single_base_model():
    text = "---\nbase_model: org/base\nbase_model_relation: fine-tuned\n---\n# Card"
    lineage, items, issues = extract_declared_from_readme(text, repository=REPO, revision=SHA)
    assert lineage.base_model == "org/base"
    assert lineage.relation is Relation.FINETUNE
    assert lineage.relation_raw == "fine-tuned"
    assert issues == []
    assert len(items) == 1
    item = items[0]
    assert item.role is EvidenceRole.DECLARED
    assert item.reliability is Reliability.NOT_APPLICABLE
    assert item.extraction_method is ExtractionMethod.DETERMINISTIC
    assert item.explicitness is Explicitness.EXPLICIT
    assert item.source_type is SourceType.DECLARED_METADATA
    assert item.key_path == "base_model"
    assert item.repository == REPO and item.revision == SHA


def test_front_matter_multiple_base_models():
    text = (
        "---\nbase_model:\n  - org/model-a\n  - org/model-b\n"
        "base_model_relation: merge\n---\nbody"
    )
    lineage, items, issues = extract_declared_from_readme(text)
    assert lineage.base_models == ["org/model-a", "org/model-b"]
    assert lineage.base_model == "org/model-a"  # stable first field
    assert lineage.relation is Relation.MERGE
    assert [i.candidate_parent for i in items] == ["org/model-a", "org/model-b"]
    assert issues == []


def test_front_matter_dict_form_entries():
    text = "---\nbase_model:\n  - name: org/model-a\n---\nbody"
    lineage, items, _ = extract_declared_from_readme(text)
    assert lineage.base_models == ["org/model-a"]
    assert len(items) == 1


def test_front_matter_missing_returns_empty():
    lineage, items, issues = extract_declared_from_readme("# just a card\n")
    assert lineage.base_model is None and items == [] and issues == []


def test_front_matter_empty_text_returns_empty():
    assert extract_declared_from_readme("") == (lineage_empty(), [], [])


def lineage_empty():
    from provenancelens.schemas import DeclaredLineage
    return DeclaredLineage()


def test_front_matter_malformed_yaml_is_error_not_crash():
    text = "---\nbase_model: [unclosed\n  bad: : : \n---\nbody"
    lineage, items, issues = extract_declared_from_readme(text)
    assert lineage.base_model is None and items == []
    assert issues and issues[0].severity == "error"
    assert "YAML" in issues[0].message


def test_front_matter_unterminated_warns():
    lineage, items, issues = extract_declared_from_readme("---\nbase_model: org/x\n# no close")
    assert lineage.base_model is None and items == []
    assert issues and issues[0].severity == "warning"
    assert "unterminated" in issues[0].message


def test_front_matter_non_mapping_is_error():
    text = "---\n- just\n- a list\n---\nbody"
    lineage, items, issues = extract_declared_from_readme(text)
    assert items == []
    assert issues and issues[0].severity == "error"
    assert "not a mapping" in issues[0].message


def test_front_matter_unsupported_shape_warns_without_item():
    text = "---\nbase_model:\n  nested: {weird: true}\n---\nbody"
    lineage, items, issues = extract_declared_from_readme(text)
    assert lineage.base_model is None and items == []
    assert any("unsupported base_model shape" in i.message for i in issues)


def test_unknown_relation_raw_preserved_relation_none():
    text = "---\nbase_model: org/base\nbase_model_relation: teleported\n---\n"
    lineage, items, issues = extract_declared_from_readme(text)
    assert lineage.relation_raw == "teleported"
    assert lineage.relation is None
    assert issues == []  # preserved, not an error
    assert items[0].relation_raw == "teleported"
    assert items[0].relation is None


def test_split_front_matter_variants():
    body, raw = split_front_matter("---\na: 1\n---\nrest")
    assert raw == "a: 1" and body == "rest"
    body, raw = split_front_matter("---\na: 1\n...\nrest")
    assert raw == "a: 1" and body == "rest"
    body, raw = split_front_matter("no front matter")
    assert raw is None and body == "no front matter"


def test_front_matter_never_lands_in_independent_list():
    text = "---\nbase_model: org/base\nbase_model_relation: finetune\n---\n"
    _, declared_items, _ = extract_declared_from_readme(
        text, repository=REPO, revision=SHA
    )
    result = extract_repository_evidence(REPO, SHA, {"README.md": text})
    assert [i.model_dump() for i in result.declared_evidence] == [
        i.model_dump() for i in declared_items
    ]
    for item in result.independent_evidence:
        assert item.role is EvidenceRole.INDEPENDENT
    for item in result.declared_evidence:
        assert item.role is EvidenceRole.DECLARED


# --- adapter_config.json -----------------------------------------------------


def test_adapter_valid_parent():
    items, issues = extract_adapter_evidence(
        '{"base_model_name_or_path": "org/base", "peft_type": "LORA"}',
        repository=REPO, revision=SHA,
    )
    assert issues == []
    item = items[0]
    assert item.candidate_parent == "org/base"
    assert item.relation is Relation.ADAPTER
    assert item.role is EvidenceRole.INDEPENDENT
    assert item.reliability is Reliability.VERY_HIGH
    assert item.source_type is SourceType.ADAPTER_CONFIG
    assert item.key_path == "base_model_name_or_path"
    assert item.raw_value == "org/base"
    assert item.repository == REPO and item.revision == SHA


def test_adapter_local_path_rejected_but_preserved():
    items, issues = extract_adapter_evidence(
        '{"base_model_name_or_path": "/data/checkpoints/llama"}'
    )
    assert issues == []
    item = items[0]
    assert item.candidate_parent is None  # never a public parent
    assert item.raw_value == "/data/checkpoints/llama"
    assert "rejected" in (item.note or "")
    assert item.reliability is Reliability.VERY_HIGH  # evidence of a claim either way


def test_adapter_bare_name_rejected():
    items, _ = extract_adapter_evidence('{"base_model_name_or_path": "llama-7b"}')
    assert items[0].candidate_parent is None
    assert items[0].raw_value == "llama-7b"


def test_adapter_missing_parent_field_is_silent():
    items, issues = extract_adapter_evidence('{"peft_type": "LORA", "r": 8}')
    assert items == [] and issues == []


def test_adapter_malformed_json_is_structural_issue():
    items, issues = extract_adapter_evidence('{"base_model_name_or_path": ')
    assert items == []
    assert issues and issues[0].severity == "error"
    assert "invalid JSON" in issues[0].message


def test_adapter_non_string_parent_warns():
    items, issues = extract_adapter_evidence('{"base_model_name_or_path": 42}')
    assert items == []
    assert issues and issues[0].severity == "warning"


def test_adapter_non_object_root_is_error():
    items, issues = extract_adapter_evidence('[1, 2, 3]')
    assert items == []
    assert issues and issues[0].severity == "error"


def test_adapter_never_claims_relation_from_filename():
    items, _ = extract_adapter_evidence(
        '{"base_model_name_or_path": "org/base", "quantization_config": {"load_in_4bit": true}}'
    )
    assert len(items) == 1
    assert items[0].relation is Relation.ADAPTER  # from the parent field, not quant config
    assert items[0].relation is not Relation.QUANTIZED


# --- training configs --------------------------------------------------------


def test_training_json_allowlist_keys_with_key_paths():
    text = (
        '{"model_name_or_path": "org/base", '
        '"training_args": {"model_name_or_path": "org/nested-base"}}'
    )
    items, issues = extract_training_evidence(text, source_name="train.json", fmt="json")
    assert issues == []
    assert [i.candidate_parent for i in items] == ["org/base", "org/nested-base"]
    assert items[0].key_path == "model_name_or_path"
    assert items[1].key_path == "training_args.model_name_or_path"
    assert all(i.relation is None for i in items)
    assert all(i.reliability is Reliability.MEDIUM for i in items)
    assert all(i.source_type is SourceType.TRAINING_CONFIG for i in items)


def test_training_yaml_variant():
    text = "base_model: org/base\nlr: 0.1\n"
    items, issues = extract_training_evidence(
        text, source_name="train.yaml", fmt="yaml"
    )
    assert issues == []
    assert items[0].candidate_parent == "org/base"
    assert items[0].relation is None


def test_training_rejects_local_paths_with_warning():
    text = '{"model_name_or_path": "/data/checkpoints/run-3"}'
    items, issues = extract_training_evidence(text, source_name="train.json")
    assert items == []
    assert issues and issues[0].severity == "warning"
    assert "/data/checkpoints/run-3" in issues[0].message
    assert "model_name_or_path" in issues[0].message


def test_training_unsupported_value_type_warns():
    text = '{"base_model": {"unexpected": "shape"}}'
    items, issues = extract_training_evidence(text, source_name="cfg.json")
    assert items == []
    assert issues and issues[0].severity == "warning"


def test_training_malformed_and_empty_inputs():
    items, issues = extract_training_evidence("{oops", source_name="cfg.json")
    assert items == [] and issues[0].severity == "error"
    items, issues = extract_training_evidence("", source_name="cfg.json")
    assert items == [] and issues[0].severity == "warning"
    items, issues = extract_training_evidence("just: [fine]", source_name="cfg.yaml", fmt="yaml")
    assert items == [] and issues == []


def test_training_ignores_non_allowlisted_keys():
    text = '{"quantization_config": {"quant_method": "bitsandbytes"}, "architectures": ["X"]}'
    items, issues = extract_training_evidence(text, source_name="cfg.json")
    assert items == [] and issues == []
    assert all(i.relation is not Relation.QUANTIZED for i in items)


def test_training_array_values_expand_with_paths():
    text = '{"base_model": ["org/a", "org/b"]}'
    items, _ = extract_training_evidence(text, source_name="cfg.json")
    assert [i.candidate_parent for i in items] == ["org/a", "org/b"]
    assert items[1].key_path == "base_model[1]"


def test_training_deep_structure_truncation_warns():
    deep = '{"a": ' * 20 + "1" + "}" * 20
    items, issues = extract_training_evidence(deep, source_name="deep.json")
    assert items == []
    assert any("deeper than" in i.message for i in issues)


def test_training_exact_source_traceability():
    text = '{"training": {"pretrained_model_name_or_path": "org/base"}}'
    items, _ = extract_training_evidence(text, source_name="configs/train.yaml", fmt="json")
    item = items[0]
    assert item.source_name == "configs/train.yaml"
    assert item.key_path == "training.pretrained_model_name_or_path"
    assert item.raw_value == "org/base"
    assert item.evidence_span is not None
    assert item.extraction_method is ExtractionMethod.DETERMINISTIC


# --- merge configs -----------------------------------------------------------


def test_merge_models_list_str_and_dict_entries():
    text = (
        "models:\n"
        "  - model: org/model-a\n"
        "  - path: org/model-b\n"
        "merge_method: linear\n"
    )
    items, issues = extract_merge_evidence(text, source_name="mergekit.yaml")
    assert issues == []
    assert [i.candidate_parent for i in items] == ["org/model-a", "org/model-b"]
    assert all(i.relation is Relation.MERGE for i in items)
    assert all(i.source_type is SourceType.MERGE_CONFIG for i in items)
    assert items[0].key_path == "models[0].model"
    assert items[1].key_path == "models[1].path"
    assert all(i.reliability is Reliability.HIGH for i in items)


def test_merge_slices_sources():
    text = "slices:\n  - sources: [org/model-a, org/model-b]\n"
    items, issues = extract_merge_evidence(text, source_name="merge.yaml")
    assert issues == []
    assert [i.candidate_parent for i in items] == ["org/model-a", "org/model-b"]
    assert items[0].key_path == "slices[0].sources[0]"


def test_merge_top_level_base_model_has_no_relation():
    text = "base_model: org/arch-base\nmodels:\n  - model: org/model-a\n"
    items, _ = extract_merge_evidence(text, source_name="mergekit.yaml")
    by_parent = {i.candidate_parent: i for i in items}
    arch = by_parent["org/arch-base"]
    assert arch.relation is None  # algorithm-specific, NOT merge by assumption
    assert "algorithm-specific" in (arch.note or "")
    assert by_parent["org/model-a"].relation is Relation.MERGE


def test_merge_duplicate_sources_deduped_with_extra_location():
    text = (
        "models:\n"
        "  - model: org/model-a\n"
        "  - model: org/model-a\n"
        "base_model: org/model-a\n"
    )
    items, _ = extract_merge_evidence(text, source_name="mergekit.yaml")
    assert [i.candidate_parent for i in items] == ["org/model-a"]
    note = items[0].note or ""
    assert "also at models[1].model" in note
    assert "also at base_model" in note


def test_merge_rejects_local_paths_with_warning():
    text = "models:\n  - model: /data/llama-checkpoint\n"
    items, issues = extract_merge_evidence(text, source_name="mergekit.yaml")
    assert items == []
    assert issues and issues[0].severity == "warning"
    assert "/data/llama-checkpoint" in issues[0].message


def test_merge_entry_without_model_field_warns():
    text = "models:\n  - weight: 0.5\n"
    items, issues = extract_merge_evidence(text, source_name="mergekit.yaml")
    assert items == []
    assert issues and "no model/path field" in issues[0].message


def test_merge_non_mapping_root_is_error():
    items, issues = extract_merge_evidence("- just\n- a list\n", source_name="m.yaml")
    assert items == [] and issues[0].severity == "error"


def test_merge_entry_missing_sources_is_not_crash():
    items, issues = extract_merge_evidence("models: not-a-list\n", source_name="m.yaml")
    assert items == [] and issues and "not a list" in issues[0].message


# --- bundle routing ----------------------------------------------------------


def _sample_contents() -> dict[str, str]:
    return {
        "README.md": (
            "---\nbase_model: org/declared-base\nbase_model_relation: finetune\n---\n\n"
            "This model is fine-tuned from org/declared-base.\n"
        ),
        "adapter_config.json": '{"base_model_name_or_path": "org/adapter-base"}',
        "config.json": '{"_name_or_path": "org/config-base"}',
        "mergekit.yaml": "models:\n  - model: org/merge-a\n  - model: org/merge-b\n",
        "train_lora.yaml": "model_name_or_path: org/train-base\n",
        "provenance_notes.md": "Merged from org/prose-merge-base for the audit.\n",
    }


def test_bundle_routes_each_file_to_its_parser():
    result = extract_repository_evidence(REPO, SHA, _sample_contents())
    assert isinstance(result, EvidenceExtraction)
    assert result.repository == REPO
    assert result.resolved_commit_sha == SHA
    assert result.schema_version == 1

    parents = {i.candidate_parent: i for i in result.independent_evidence}
    assert parents["org/adapter-base"].relation is Relation.ADAPTER
    assert parents["org/adapter-base"].reliability is Reliability.VERY_HIGH
    assert parents["org/config-base"].relation is None
    assert parents["org/train-base"].relation is None
    assert parents["org/merge-a"].relation is Relation.MERGE
    assert parents["org/merge-b"].relation is Relation.MERGE
    assert parents["org/prose-merge-base"].relation is Relation.MERGE
    # declared subject extracted but never mixed into independent evidence
    assert result.declared_lineage.base_model == "org/declared-base"
    assert result.declared_lineage.relation is Relation.FINETUNE
    assert all(i.role is EvidenceRole.INDEPENDENT for i in result.independent_evidence)


def test_bundle_declared_relation_never_inherited_by_independent_items():
    contents = {
        "README.md": "---\nbase_model: org/x\nbase_model_relation: merge\n---\n",
        "config.json": '{"base_model": "org/x"}',
    }
    result = extract_repository_evidence(REPO, SHA, contents)
    assert result.declared_lineage.relation is Relation.MERGE
    config_items = [i for i in result.independent_evidence if i.source_name == "config.json"]
    assert config_items and config_items[0].relation is None


def test_bundle_malformed_priority_config_reports_issue_keeps_others():
    contents = {
        "README.md": "---\nbase_model: org/x\n---\n",
        "config.json": "{broken json",
        "train.yaml": "base_model: org/y\n",
    }
    result = extract_repository_evidence(REPO, SHA, contents)
    assert any(i.source_name == "config.json" and i.severity == "error"
               for i in result.issues)
    assert any(i.candidate_parent == "org/x" for i in result.declared_evidence)
    assert any(i.candidate_parent == "org/y" for i in result.independent_evidence)


def test_bundle_quantization_config_never_yields_quantized_relation():
    contents = {"quantization_config.json": '{"quantization_config": {"load_in_4bit": true}}'}
    result = extract_repository_evidence(REPO, SHA, contents)
    assert all(i.relation is not Relation.QUANTIZED for i in result.independent_evidence)


def test_bundle_text_and_unsupported_files():
    result = extract_repository_evidence(REPO, SHA, {"notes.txt": "just notes\n"})
    assert result.independent_evidence == [] and result.issues == []
    result = extract_repository_evidence(REPO, SHA, {"weights.safetensors": "\x00\x01"})
    assert any(i.severity == "warning" for i in result.issues)


def test_bundle_non_text_content_warns():
    result = extract_repository_evidence(REPO, SHA, {"README.md": 12345})
    assert any("not text" in i.message for i in result.issues)


def test_bundle_is_deterministic_and_ordered():
    contents = _sample_contents()
    first = extract_repository_evidence(REPO, SHA, contents)
    second = extract_repository_evidence(REPO, SHA, dict(reversed(list(contents.items()))))
    assert first.model_dump() == second.model_dump()
    source_names = [i.source_name for i in first.independent_evidence]
    assert source_names == sorted(source_names)


def test_bundle_uses_requested_revision_when_sha_missing():
    result = extract_repository_evidence(REPO, None, {"README.md": "# x"}, requested_revision="main")
    assert result.resolved_commit_sha is None
    # revision fallback reaches evidence items
    assert all(i.revision in (None, "main") for i in result.declared_evidence)
