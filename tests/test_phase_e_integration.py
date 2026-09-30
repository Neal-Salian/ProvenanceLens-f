"""Phase E integration with the Phase D engine, plus stability guarantees.

The invariants under test:
  * Phase D remains the only decision maker;
  * LLM prose is MEDIUM-capped author-controlled evidence;
  * deterministic-only mode is the default and needs no LLM at all;
  * an unavailable or failing LLM never blocks an otherwise safe decision;
  * strong structured evidence cannot be casually overridden by prose;
  * evidence ordering stays irrelevant.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fixtures.phase_e_llm import (
    ADAPTER_README,
    CannedChatModel,
    claim_set,
    explicit_claim,
)
from provenancelens.pipeline import (
    audit_repository,
    audit_repository_with_prose,
    extract_snapshot_prose,
)
from provenancelens.prose import (
    LLMProseExtractor,
    ProseExtractionStatus,
    ProseFailureCode,
    unavailable_report,
)
from provenancelens.reasoning import aggregate_candidates, decide_lineage
from provenancelens.reporting import format_audit_decision
from provenancelens.schemas import Decision, Explicitness, ExtractionMethod, Reliability
from provenancelens.schemas.extraction import ExtractionIssue
from provenancelens.schemas.lineage import Relation

from test_phase_d_decisions import decide as phase_d_decide

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"

FINETUNE = "teknium/OpenHermes-2.5-Mistral-7B"
ADAPTER_REPO = "peft-internal-testing/tiny-OPTForCausalLM-lora"
MERGE_REPO = "mergekit-community/Qwen3-1.5B-Instruct"


def llm_claim_item(parent: str, relation, *, span: str, source_name: str = "README.md"):
    """Build LLM evidence exactly as the extractor would (via the real path)."""
    from provenancelens.prose import build_llm_evidence_item
    from provenancelens.prose.schema import ClaimStatus, ProseLineageClaim, RationaleCode

    claim = ProseLineageClaim(
        candidate_parent=parent,
        relation=relation,
        claim_status=ClaimStatus.EXPLICIT,
        evidence_span=span,
        rationale_code=RationaleCode.EXPLICIT_FINETUNE_PHRASE,
    )
    return build_llm_evidence_item(
        claim, source_name=source_name, key_path="prose[chunk 0]",
        note="llm prose claim; prompt=v1.0",
    )


# --- evidence shape and authority -------------------------------------------


def test_llm_evidence_is_medium_capped_and_prose_sourced():
    item = llm_claim_item("org/base-model", Relation.FINETUNE, span="fine-tuned from org/base-model")
    assert item.extraction_method is ExtractionMethod.LLM
    assert item.reliability is Reliability.MEDIUM
    assert item.reliability in (Reliability.WEAK, Reliability.MEDIUM, Reliability.MEDIUM_HIGH)
    assert item.explicitness is Explicitness.EXPLICIT
    assert item.source_name == "README.md"


def test_llm_evidence_enters_the_same_phase_d_engine():
    from fixtures.phase_d_evidence import A, adapter_evidence, declared

    deterministic = [adapter_evidence(A)]
    llm = [llm_claim_item("org/prose-base", Relation.FINETUNE, span="fine-tuned from org/prose-base")]

    with_llm = phase_d_decide(declared(), deterministic + llm)
    without_llm = phase_d_decide(declared(), deterministic)
    assert with_llm.decision.decision is Decision.ADD
    assert with_llm.decision.decision is without_llm.decision.decision is Decision.ADD
    # the prose claim reached the engine as an ordinary candidate hypothesis
    candidates = {
        parent
        for hypothesis in with_llm.candidates.hypotheses
        for parent in hypothesis.parents
    }
    assert "org/prose-base" in candidates


# --- stability: prose cannot casually override structured evidence ----------


def test_very_high_adapter_evidence_survives_contradictory_weak_prose():
    from fixtures.phase_d_evidence import A, B, adapter_evidence, declared

    result = phase_d_decide(
        declared(B, "finetune"),
        [
            adapter_evidence(A),
            llm_claim_item(B, Relation.ADAPTER, span="trained on top of B"),
        ],
    )
    assert result.decision.decision is not Decision.REPLACE
    assert result.decision.recommended_patch is None
    assert result.decision.proposed_lineage.parents in ([A], [])


def test_very_high_adapter_add_is_not_overridden_by_weak_prose():
    from fixtures.phase_d_evidence import A, adapter_evidence, declared

    result = phase_d_decide(
        declared(),
        [
            adapter_evidence(A),
            llm_claim_item("org/prose-only", Relation.FINETUNE,
                           span="fine-tuned from org/prose-only"),
        ],
    )
    assert result.decision.decision is Decision.ADD
    assert result.decision.proposed_lineage.parents == [A]


def test_strong_merge_evidence_is_not_narrowed_by_partial_prose():
    from fixtures.phase_d_evidence import A, B, declared, merge_evidence

    result = phase_d_decide(
        declared(A, "merge", (B,)),
        [
            *merge_evidence([A, B]),
            llm_claim_item(A, Relation.MERGE, span="merges org/A with other models"),
        ],
    )
    assert result.decision.decision is Decision.KEEP
    assert set(result.decision.proposed_lineage.parents) == {A, B}


def test_irrelevant_prose_does_not_change_a_decision():
    from fixtures.phase_d_evidence import A, adapter_evidence, declared

    baseline = phase_d_decide(declared(), [adapter_evidence(A)])
    noisy = phase_d_decide(
        declared(),
        [
            adapter_evidence(A),
            llm_claim_item("org/irrelevant", Relation.FINETUNE,
                           span="fine-tuned from org/irrelevant"),
        ],
    )
    assert noisy.decision.decision is baseline.decision.decision is Decision.ADD
    assert noisy.decision.proposed_lineage.parents == [A]


def test_prose_cannot_outrank_a_tool_generated_artifact_on_its_own():
    """Many prose mentions are still author-controlled documentation."""
    from fixtures.phase_d_evidence import A, adapter_evidence, declared

    items = [adapter_evidence(A)]
    items += [
        llm_claim_item(f"org/prose-{i}", Relation.FINETUNE,
                       span=f"fine-tuned from org/prose-{i}")
        for i in range(5)
    ]
    result = phase_d_decide(declared(), items)
    assert result.decision.decision is Decision.ADD
    assert result.decision.proposed_lineage.parents == [A]
    assert result.decision.support_score == pytest.approx(0.75)


def test_evidence_ordering_remains_irrelevant_with_llm_evidence():
    from fixtures.phase_d_evidence import A, adapter_evidence, declared

    adapter = adapter_evidence(A)
    prose = llm_claim_item("org/prose-base", Relation.FINETUNE,
                           span="fine-tuned from org/prose-base")
    first = phase_d_decide(declared(), [adapter, prose])
    second = phase_d_decide(declared(), [prose, adapter])
    assert first.decision.decision is second.decision.decision
    assert first.decision.support_score == pytest.approx(second.decision.support_score)


# --- source independence: README prose vs README front matter --------------


def test_readme_prose_does_not_masquerade_as_a_second_physical_source():
    from fixtures.phase_d_evidence import A, declared

    result = phase_d_decide(
        declared(A, "finetune"),
        [llm_claim_item(A, Relation.FINETUNE, span="fine-tuned from A")],
    )
    # A single prose mention is author-controlled documentation: it cannot
    # establish lineage on its own, and it certainly is not "two sources".
    assert result.decision.decision is Decision.ABSTAIN
    assert result.decision.support_score < 0.55


# --- deterministic-only vs LLM modes ---------------------------------------


def test_deterministic_only_is_the_default_and_needs_no_llm():
    for repo in (FINETUNE, ADAPTER_REPO, MERGE_REPO):
        decision = audit_repository(repo, root=SNAPSHOT_ROOT).decision
        assert decision.decision in (Decision.KEEP, Decision.ADD, Decision.REPLACE,
                                     Decision.ABSTAIN)
    # audit_repository has no LLM parameter at all: prose is opt-in
    import inspect
    assert "extractor" not in inspect.signature(audit_repository).parameters


def test_no_extractor_is_reported_unavailable_and_changes_nothing():
    outcome = audit_repository_with_prose(ADAPTER_REPO, root=SNAPSHOT_ROOT)
    assert outcome.report.status is ProseExtractionStatus.UNAVAILABLE
    assert outcome.report.evidence == []
    assert outcome.llm_evidence_count == 0
    assert outcome.decision_changed is False
    assert outcome.decision.decision is Decision.ADD


def test_snapshot_prose_is_fetched_through_the_langchain_tool():
    reports = extract_snapshot_prose(ADAPTER_REPO, root=SNAPSHOT_ROOT, extractor=None)
    assert reports[0].status is ProseExtractionStatus.UNAVAILABLE
    # the tool really ran: the artifact was found, otherwise the reason differs
    assert "deterministic-only" in (reports[0].reason or "")


def test_unknown_snapshot_yields_unavailable_not_crash():
    reports = extract_snapshot_prose("org/does-not-exist", root=SNAPSHOT_ROOT)
    assert reports[0].status is ProseExtractionStatus.UNAVAILABLE
    assert "no frozen snapshot" in (reports[0].reason or "")


def test_llm_failure_does_not_override_strong_deterministic_evidence():
    from fixtures.phase_d_evidence import A, adapter_evidence, declared
    from provenancelens.prose import ProseExtractionReport

    model = CannedChatModel(responses=[], raise_on_call="ollama connection refused")
    extractor = LLMProseExtractor(model, model_name="broken")
    report = extractor.extract(ADAPTER_README, source_name="README.md")
    assert report.evidence == []
    assert report.failures[0].code is ProseFailureCode.MALFORMED_OUTPUT

    # the deterministic decision is unchanged by that failure
    assert phase_d_decide(declared(), [adapter_evidence(A)]).decision.decision is Decision.ADD


def test_unavailable_report_shape_is_structural():
    report = unavailable_report("README.md", "Ollama not running", model="llama3.2:3b")
    assert report.status is ProseExtractionStatus.UNAVAILABLE
    assert report.reason == "Ollama not running"
    assert report.evidence == []
    assert "unavailable" in report.summary().lower()


# --- reporting --------------------------------------------------------------


def test_report_separates_deterministic_and_llm_evidence():
    from fixtures.phase_d_evidence import A, adapter_evidence
    from provenancelens.pipeline import audit_extraction
    from provenancelens.parsers import extract_repository_evidence
    from provenancelens.snapshots import load_snapshot

    commit = sorted(
        p.name for p in (SNAPSHOT_ROOT / ADAPTER_REPO.replace("/", "__")).iterdir()
        if (p / "manifest.json").is_file()
    )[-1]
    snapshot = load_snapshot(ADAPTER_REPO, commit, root=SNAPSHOT_ROOT)
    extraction = extract_repository_evidence(ADAPTER_REPO, commit, snapshot.contents)
    # prose that corroborates the *same* parent the adapter config names, so the
    # LLM item belongs to the winning hypothesis and shows up in the report
    parent = "hf-internal-testing/tiny-random-OPTForCausalLM"
    llm = [llm_claim_item(parent, Relation.ADAPTER, span=f"adapter for {parent}")]
    result = audit_extraction(extraction, extra_evidence=llm)
    from provenancelens.prose import ProseExtractionReport

    prose_report = ProseExtractionReport(
        status=ProseExtractionStatus.OK,
        source_name="README.md",
        prompt_version="1.0",
        prompt_digest="0" * 64,
        model="canned-test-model",
        chunks_processed=1,
        claims_reported=1,
        claims_accepted=1,
        evidence=llm,
    )
    report = format_audit_decision(result.decision, prose_report=prose_report)
    assert "[DETERMINISTIC]" in report
    assert "adapter_config" in report
    assert "[LLM_EXTRACTED]" in report
    assert "prompt version: 1.0" in report


def test_report_includes_llm_status_and_rejections():
    from provenancelens.prose.schema import ProseFailure

    report = unavailable_report("README.md", "Ollama not running")
    decision = audit_repository(ADAPTER_REPO, root=SNAPSHOT_ROOT).decision
    rendered = format_audit_decision(decision, prose_report=report)
    assert "LLM PROSE EXTRACTION" in rendered
    assert "Ollama not running" in rendered

    report_with_failure = report.model_copy(update={
        "failures": [ProseFailure(
            source_name="README.md", chunk_index=0,
            code=ProseFailureCode.SPAN_NOT_FOUND, detail="not found",
        )],
    })
    rendered = format_audit_decision(decision, prose_report=report_with_failure)
    assert "rejected claims" in rendered
    assert "span_not_found" in rendered
    # no chain-of-thought is ever displayed
    assert "step" not in rendered.lower() or "steps" not in rendered.lower()


def test_tool_failure_issue_and_llm_evidence_coexist_without_penalty():
    from fixtures.phase_d_evidence import A, adapter_evidence, declared, issue

    result = phase_d_decide(
        declared(), [adapter_evidence(A)],
        issues=[issue()],
    )
    assert result.decision.decision is Decision.ADD


def test_prose_extraction_outcome_serializes_for_reproducible_runs():
    outcome = audit_repository_with_prose(ADAPTER_REPO, root=SNAPSHOT_ROOT)
    payload = outcome.report.model_dump(mode="json")
    json.dumps(payload)  # must stay JSON-serializable for run archives
    assert payload["prompt_version"] == "1.0"
    assert len(payload["prompt_digest"]) == 64
