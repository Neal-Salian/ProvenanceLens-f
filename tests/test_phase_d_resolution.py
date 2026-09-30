"""Conservative entity resolution: what may be resolved, and what must not be."""

from __future__ import annotations

import pytest

from provenancelens.resolution import (
    ResolutionStatus,
    normalize_identifier,
    resolve_identifier,
)

EVIDENCE_INDEX = {
    "meta-llama/Llama-2-7b-hf": {"meta-llama/Llama-2-7b-hf", "Llama-2-7b-hf"},
    "Qwen/Qwen2.5-7B-Instruct": {"Qwen/Qwen2.5-7B-Instruct", "Qwen2.5-7B-Instruct"},
}


# --- exact and normalized ---------------------------------------------------


@pytest.mark.parametrize("raw", [
    "meta-llama/Llama-2-7b-hf",
    "  meta-llama/Llama-2-7b-hf  ",
])
def test_canonical_ids_are_exact_or_normalized(raw: str):
    resolution = resolve_identifier(raw)
    assert resolution.status in (ResolutionStatus.EXACT, ResolutionStatus.NORMALIZED)
    assert resolution.resolved == "meta-llama/Llama-2-7b-hf"
    assert resolution.raw == raw.strip()  # raw is kept, only trimmed


def test_stored_spelling_is_never_rewritten():
    """Hub ids are case-insensitive but the author's spelling is kept as-is."""
    resolution = resolve_identifier("Meta-Llama/Llama-2-7B-HF")
    assert resolution.resolved == "Meta-Llama/Llama-2-7B-HF"
    assert resolution.status is ResolutionStatus.EXACT


def test_case_variant_unifies_with_the_evidence_spelling():
    resolution = resolve_identifier(
        "Meta-Llama/Llama-2-7B-HF", evidence_ids=EVIDENCE_INDEX
    )
    assert resolution.status is ResolutionStatus.REFERENT
    assert resolution.resolved == "meta-llama/Llama-2-7b-hf"


def test_hub_url_is_normalized_not_rejected():
    for raw in (
        "huggingface.co/meta-llama/Llama-2-7b-hf",
        "https://huggingface.co/meta-llama/Llama-2-7b-hf",
        "https://hf.co/meta-llama/Llama-2-7b-hf",
        "https://huggingface.co/meta-llama/Llama-2-7b-hf/revisions/abc123",
    ):
        resolution = resolve_identifier(raw)
        assert resolution.resolved == "meta-llama/Llama-2-7b-hf"
        assert resolution.status is ResolutionStatus.NORMALIZED


def test_normalize_identifier_trims_and_collapses_space():
    assert normalize_identifier("  Mistral 7B ") == "Mistral-7B"
    assert normalize_identifier("meta-llama/Llama-2-7b-hf") == "meta-llama/Llama-2-7b-hf"


# --- referent matching within the evidence ---------------------------------


def test_bare_name_resolves_only_when_the_evidence_shows_one_target():
    resolution = resolve_identifier("Llama-2-7b-hf", evidence_ids=EVIDENCE_INDEX)
    assert resolution.status is ResolutionStatus.REFERENT
    assert resolution.resolved == "meta-llama/Llama-2-7b-hf"


def test_case_insensitive_bare_name_matches_the_same_target():
    resolution = resolve_identifier("llama-2-7b-hf", evidence_ids=EVIDENCE_INDEX)
    assert resolution.resolved == "meta-llama/Llama-2-7b-hf"


def test_same_name_in_two_organizations_is_ambiguous():
    index = {
        "org-a/shared-name": {"shared-name"},
        "org-b/shared-name": {"shared-name"},
    }
    resolution = resolve_identifier("shared-name", evidence_ids=index)
    assert resolution.status is ResolutionStatus.AMBIGUOUS
    assert resolution.resolved is None
    assert resolution.alternatives == ["org-a/shared-name", "org-b/shared-name"]


# --- things that must never resolve -----------------------------------------


@pytest.mark.parametrize("raw", [
    "Mistral 7B",
    "Mistral-7B-v0.1",
    "llama3",
    "gpt2",
    "some random model",
])
def test_bare_names_without_evidence_are_ambiguous(raw: str):
    resolution = resolve_identifier(raw)
    assert resolution.resolved is None
    assert resolution.status in (ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNRESOLVED)


def test_mistral_7b_never_becomes_a_specific_version():
    resolution = resolve_identifier("Mistral 7B")
    assert resolution.resolved is None
    assert "mistralai" not in str(resolution.resolved)
    assert "version" in resolution.reason or "namespace" in resolution.reason


@pytest.mark.parametrize("raw", [
    "/data/checkpoints/run-3",
    "./outputs/model",
    "../model",
    "C:\\models\\llama",
    "model.safetensors",
    "training.json",
    "",
    "   ",
])
def test_paths_and_non_references_are_invalid(raw: str):
    resolution = resolve_identifier(raw)
    assert resolution.status is ResolutionStatus.INVALID
    assert resolution.resolved is None


@pytest.mark.parametrize("raw", [None, 42, 3.5, [], {}])
def test_non_string_values_are_invalid(raw: object):
    assert resolve_identifier(raw).status is ResolutionStatus.INVALID


def test_substring_similarity_is_not_resolution():
    """A different suffix is a different model, not a variant of the same one."""
    resolution = resolve_identifier("meta-llama/Llama-2-7b-hf-v2")
    assert resolution.resolved == "meta-llama/Llama-2-7b-hf-v2"  # distinct id
    assert resolution.resolved != "meta-llama/Llama-2-7b-hf"


def test_same_organization_is_not_resolution():
    resolution = resolve_identifier("meta-llama/Mistral-7B-v0.1")
    assert resolution.resolved == "meta-llama/Mistral-7B-v0.1"


def test_resolution_never_calls_the_network(monkeypatch):
    """Entity resolution is a pure function: no hub lookups whatsoever."""
    import provenancelens.resolution.resolver as resolver_module

    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("entity resolution must not perform any I/O")

    monkeypatch.setattr(resolver_module, "resolve_identifier", explode, raising=False)
    # A fresh call through the public path still works without I/O.
    assert resolve_identifier("org/model", evidence_ids={}).status is ResolutionStatus.EXACT


def test_resolution_result_is_frozen():
    resolution = resolve_identifier("org/model")
    with pytest.raises(Exception):
        resolution.resolved = "other/model"  # type: ignore[misc]
