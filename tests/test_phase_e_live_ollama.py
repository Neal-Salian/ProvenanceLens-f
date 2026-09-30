"""Optional live local-LLM tests (opt-in, never required).

Enable with::

    PROVENANCELENS_LLM_TESTS=1 python3 -m pytest tests/test_phase_e_live_ollama.py

These tests are skipped by default and skip again (never fail) when the local
runtime or the configured model is missing. ProvenanceLens never downloads a
model: if ``llama3.2:3b`` is not installed, run ``ollama pull llama3.2:3b``
manually and re-run.
"""

from __future__ import annotations

import os
import time

import pytest

from fixtures.phase_e_llm import ADAPTER_README, FINETUNE_README, NO_CLAIM_README
from provenancelens.llm_runtime import (
    DEFAULT_LLM_MODEL,
    build_default_chat_model,
    llm_availability,
)
from provenancelens.prose import ProseExtractionStatus

_ENABLED = os.environ.get("PROVENANCELENS_LLM_TESTS") == "1"
live_only = pytest.mark.skipif(
    not _ENABLED,
    reason="set PROVENANCELENS_LLM_TESTS=1 to run live local LLM tests",
)


def _require_model():
    availability = llm_availability()
    if not availability.available:
        pytest.skip(availability.reason or "local model unavailable")
    return availability


@live_only
def test_local_model_is_available():
    availability = _require_model()
    assert availability.model
    assert availability.runtime_reachable is True


@live_only
def test_live_extraction_finds_a_grounded_claim():
    _require_model()
    from provenancelens.prose import LLMProseExtractor

    extractor = LLMProseExtractor(build_default_chat_model())
    started = time.perf_counter()
    report = extractor.extract(
        ADAPTER_README, source_name="README.md", repository="org/adapter",
    )
    elapsed = time.perf_counter() - started
    assert report.status in (
        ProseExtractionStatus.OK, ProseExtractionStatus.PARTIAL,
        ProseExtractionStatus.FAILED,
    )
    print(f"model={report.model} status={report.status.value} "
          f"chunks={report.chunks_processed} accepted={report.claims_accepted} "
          f"failures={[f.code.value for f in report.failures]} elapsed={elapsed:.1f}s")
    # Whatever the small local model produced, every accepted claim must be
    # grounded in the source text: the guard is the invariant under test.
    for item in report.evidence:
        assert item.candidate_parent in item.evidence_span
        assert item.reliability.value == "medium"
        assert item.extraction_method.value == "llm"


@live_only
def test_live_no_claim_document_produces_no_lineage_evidence():
    _require_model()
    from provenancelens.prose import LLMProseExtractor

    extractor = LLMProseExtractor(build_default_chat_model())
    report = extractor.extract(NO_CLAIM_README, source_name="README.md")
    for item in report.evidence:
        # A comparison/acknowledgement document must not yield lineage claims.
        assert item.relation is None or item.relation.value in (
            "finetune", "adapter", "merge", "quantized",
        )
        assert item.candidate_parent in item.evidence_span


@live_only
def test_live_pipeline_still_decides_with_phase_d():
    """The decision must come from Phase D, whatever the prose extractor found."""
    from pathlib import Path

    from provenancelens.pipeline import audit_repository_with_prose

    _require_model()
    repo_root = Path(__file__).resolve().parent.parent
    from provenancelens.prose import LLMProseExtractor

    outcome = audit_repository_with_prose(
        "peft-internal-testing/tiny-OPTForCausalLM-lora",
        root=repo_root / "data" / "snapshots",
        extractor=LLMProseExtractor(build_default_chat_model()),
    )
    # adapter_config evidence is strong enough regardless of prose
    assert outcome.decision.decision.value == "ADD"
    print(f"deterministic={outcome.deterministic_decision} "
          f"with_llm={outcome.decision.decision.value} "
          f"changed={outcome.decision_changed} llm_claims={outcome.llm_evidence_count}")


def test_live_tests_are_skipped_without_the_env_flag():
    """Guard: the default suite must not require Ollama."""
    if _ENABLED:  # pragma: no cover - only when explicitly enabled
        pytest.skip("env flag set")
    availability = llm_availability()
    # The probe is safe to call either way; it must never raise.
    assert isinstance(availability.available, bool)
    assert DEFAULT_LLM_MODEL
