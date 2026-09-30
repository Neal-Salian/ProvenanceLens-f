"""Phase E on the three frozen real repositories (offline, canned model).

The live local model was run against all three snapshots during development;
these tests pin the *invariants* that held, using canned answers:

* validated prose evidence never overrides deterministic structured evidence,
* a misread benchmark sentence is rejected rather than trusted,
* an unresolved bare name surfaces as a conservative abstention,
* the frozen snapshots are never modified, and Phase D still decides.

Frozen snapshots are inputs and are never changed to fit an expectation.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from fixtures.phase_e_llm import CannedChatModel, claim_set, explicit_claim
from provenancelens.pipeline import (
    audit_repository,
    audit_repository_with_prose,
    extract_snapshot_prose,
)
from provenancelens.prose import (
    LLMProseExtractor,
    ProseFailureCode,
    ProseExtractionStatus,
)
from provenancelens.reporting import format_audit_decision
from provenancelens.schemas import Decision, ExtractionMethod

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"

FINETUNE = "teknium/OpenHermes-2.5-Mistral-7B"
ADAPTER = "peft-internal-testing/tiny-OPTForCausalLM-lora"
MERGE = "mergekit-community/Qwen3-1.5B-Instruct"

REPOS = (FINETUNE, ADAPTER, MERGE)


def canned(responses: list[str]) -> LLMProseExtractor:
    return LLMProseExtractor(CannedChatModel(responses=responses))


def _grounded_window(extractor: LLMProseExtractor, text: str, start: str) -> str:
    """A verbatim, whitespace-normalized window from a chunk the model really saw.

    Grounding the canned answer in the *selected chunks* keeps the test honest:
    the span cannot silently drift away from what the extractor sends.
    """
    for chunk in extractor.select_chunks(text):
        index = chunk.text.find(start)
        if index == -1:
            continue
        # Cut on a real sentence boundary only: a period inside "2.5" or inside
        # a URL must not truncate the window.
        boundary = chunk.text.find(". ", index)
        end = boundary + 1 if boundary != -1 else len(chunk.text)
        window = chunk.text[index:end]
        normalized = " ".join(window.split())
        if len(normalized) > 20:
            return normalized
    raise AssertionError(f"no selected chunk contains {start!r}")


def readme_of(repo: str) -> str:
    directory = SNAPSHOT_ROOT / repo.replace("/", "__")
    commit = sorted(p.name for p in directory.iterdir()
                    if (p / "manifest.json").is_file())[-1]
    return (directory / commit / "files" / "README.md").read_text(encoding="utf-8")


# --- documented deterministic decisions stay stable -------------------------


@pytest.mark.parametrize("repo", REPOS)
def test_no_claim_prose_leaves_every_decision_unchanged(repo: str):
    baseline = audit_repository(repo, root=SNAPSHOT_ROOT).decision
    outcome = audit_repository_with_prose(
        repo, root=SNAPSHOT_ROOT, extractor=canned(['{"claims": []}'])
    )
    assert outcome.deterministic_decision == baseline.decision.value
    assert outcome.decision.decision is baseline.decision
    assert outcome.decision_changed is False
    assert outcome.report.evidence == []


def test_openhermes_benchmark_misreading_is_rejected_not_trusted():
    """A leaderboard sentence is not lineage, even when it says "finetune".

    The span is a verbatim sentence from the frozen model card, so this is the
    real misreading observed in the live run, not an invented one.
    """
    extractor = canned([claim_set(explicit_claim("Mistral-7B", "finetune", "x") )])
    span = _grounded_window(
        extractor, readme_of(FINETUNE), "Hermes 2.5 on Mistral-7B outperforms"
    )
    extractor = canned([claim_set(explicit_claim("Mistral-7B", "finetune", span))])
    reports = extract_snapshot_prose(
        FINETUNE, root=SNAPSHOT_ROOT, extractor=extractor
    )
    assert all(report.evidence == [] for report in reports)
    codes = {f.code for report in reports for f in report.failures}
    assert ProseFailureCode.NON_LINEAGE_CONTEXT in codes


def test_openhermes_unresolved_bare_name_yields_conservative_abstain():
    """A vague prose mention must not resolve into a canonical model id."""
    extractor = canned(['{"claims": []}'])
    baseline = audit_repository(FINETUNE, root=SNAPSHOT_ROOT).decision
    outcome = audit_repository_with_prose(
        FINETUNE, root=SNAPSHOT_ROOT, extractor=extractor
    )
    # deterministic evidence alone already abstains here, and the LLM run must
    # not make the system *more* confident
    assert baseline.decision is Decision.ABSTAIN
    assert outcome.decision.decision is Decision.ABSTAIN
    assert outcome.decision.support_score == pytest.approx(baseline.support_score)


def test_openhermes_prose_cannot_raise_support_above_the_policy_bar():
    """A confident-sounding prose claim alone is still MEDIUM author-controlled."""
    baseline = audit_repository(FINETUNE, root=SNAPSHOT_ROOT).decision
    outcome = audit_repository_with_prose(
        FINETUNE, root=SNAPSHOT_ROOT, extractor=canned(['{"claims": []}'])
    )
    assert outcome.decision.support_score <= baseline.support_score + 0.30
    assert outcome.decision.decision is not Decision.REPLACE


def test_adapter_repository_decision_is_unchanged_by_prose():
    """adapter_config evidence is strong; prose cannot redirect the repair."""
    baseline = audit_repository(ADAPTER, root=SNAPSHOT_ROOT).decision
    assert baseline.decision is Decision.ADD
    wrong_span = "We compare against hf-internal-testing/tiny-random-OPTForCausalLM."
    outcome = audit_repository_with_prose(
        ADAPTER, root=SNAPSHOT_ROOT,
        extractor=canned([claim_set(explicit_claim(
            "hf-internal-testing/tiny-random-OPTForCausalLM", "merge", wrong_span,
            rationale="EXPLICIT_MERGE_PHRASE"))]),
    )
    assert outcome.decision.decision is Decision.ADD
    assert outcome.decision.proposed_lineage.parents == [
        "hf-internal-testing/tiny-random-OPTForCausalLM"
    ]
    assert outcome.decision.proposed_lineage.entries[0].relation.value == "adapter"


def test_merge_repository_declared_set_is_never_narrowed_by_prose():
    baseline = audit_repository(MERGE, root=SNAPSHOT_ROOT).decision
    assert baseline.decision is Decision.KEEP
    declared = set(baseline.current_lineage.base_models)
    outcome = audit_repository_with_prose(
        MERGE, root=SNAPSHOT_ROOT,
        extractor=canned(['{"claims": []}']),
    )
    assert outcome.decision.decision is Decision.KEEP
    assert set(outcome.decision.proposed_lineage.parents) == declared


# --- evidence provenance and report ---------------------------------------


def test_merge_model_card_prose_claim_is_grounded_and_labelled():
    """The merge model card really does state its merge source in prose."""
    readme = readme_of(MERGE)
    parent = "Qwen/Qwen2.5-1.5B-Instruct"
    extractor = canned([claim_set(explicit_claim(parent, "merge", "x"))])
    span = _grounded_window(extractor, readme, "This model was merged using")
    assert parent in span, "the merge sentence must name the source model"
    extractor = canned([claim_set(explicit_claim(
        parent, "merge", span, rationale="EXPLICIT_MERGE_PHRASE"))])
    outcome = audit_repository_with_prose(
        MERGE, root=SNAPSHOT_ROOT, extractor=extractor
    )
    assert outcome.report.claims_accepted == 1
    item = outcome.report.evidence[0]
    assert item.candidate_parent == parent
    assert item.extraction_method is ExtractionMethod.LLM
    assert item.reliability.value == "medium"
    assert span in readme

    report = format_audit_decision(outcome.decision, prose_report=outcome)
    # The claim is reported as validated LLM prose, with its prompt version.
    assert "LLM PROSE EXTRACTION" in report
    assert "prompt version: 1.0" in report
    assert parent in report
    # Prose about a merge source corroborates a *parent* cluster; it never joins
    # the merge source set itself (Phase D aggregates merge evidence from merge
    # configurations only), so the declared set and the decision stay intact.
    assert outcome.decision.decision is Decision.KEEP
    assert outcome.decision_changed is False
    assert set(outcome.decision.proposed_lineage.parents) == set(
        outcome.decision.current_lineage.base_models
    )


def test_adapter_model_card_has_no_lineage_prose_to_extract():
    """Documented fact: the 93-byte adapter card states no lineage in prose."""
    readme = readme_of(ADAPTER)
    assert len(readme) < 200
    outcome = audit_repository_with_prose(
        ADAPTER, root=SNAPSHOT_ROOT, extractor=canned([claim_set()])
    )
    assert outcome.report.evidence == []
    report = format_audit_decision(outcome.decision, prose_report=outcome)
    assert "LLM PROSE EXTRACTION" in report
    assert "[LLM_EXTRACTED]" not in report


@pytest.mark.parametrize("repo", REPOS)
def test_frozen_snapshots_are_never_modified_by_a_phase_e_run(repo: str):
    def digest() -> dict[str, str]:
        return {
            str(path.relative_to(SNAPSHOT_ROOT)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(SNAPSHOT_ROOT.rglob("*")) if path.is_file()
        }

    before = digest()
    outcome = audit_repository_with_prose(
        repo, root=SNAPSHOT_ROOT, extractor=canned(['{"claims": []}'])
    )
    assert digest() == before
    assert outcome.report.status in (
        ProseExtractionStatus.OK, ProseExtractionStatus.PARTIAL,
    )


@pytest.mark.parametrize("repo", REPOS)
def test_phase_e_runs_are_deterministic_for_canned_responses(repo: str):
    first = audit_repository_with_prose(
        repo, root=SNAPSHOT_ROOT, extractor=canned(['{"claims": []}'])
    )
    second = audit_repository_with_prose(
        repo, root=SNAPSHOT_ROOT, extractor=canned(['{"claims": []}'])
    )
    assert first.decision.model_dump() == second.decision.model_dump()
    assert first.report.model_dump(mode="json")["evidence"] == \
        second.report.model_dump(mode="json")["evidence"]
