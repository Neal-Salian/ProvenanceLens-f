"""Phase D reasoning over the three frozen Phase C snapshots (offline).

These tests document what the evidence policy actually produces. They are NOT
ground-truth labels: a KEEP means "no safe repair is indicated by the current
evidence", not "the repository metadata was independently verified as correct".
No snapshot, parser, or expectation is modified to fit a preferred outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provenancelens.parsers import extract_repository_evidence
from provenancelens.pipeline import audit_extraction, audit_repository, audit_snapshot
from provenancelens.reporting import format_audit_decision
from provenancelens.schemas import Decision, EvidenceRole, Reliability, SourceType
from provenancelens.schemas.lineage import Relation

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"

FINETUNE = "teknium/OpenHermes-2.5-Mistral-7B"
ADAPTER = "peft-internal-testing/tiny-OPTForCausalLM-lora"
MERGE = "mergekit-community/Qwen3-1.5B-Instruct"


def _commit_of(repo: str) -> str:
    encoded = repo.replace("/", "__")
    commits = sorted(
        path.name for path in (SNAPSHOT_ROOT / encoded).iterdir()
        if (path / "manifest.json").is_file()
    )
    assert commits, f"no frozen snapshot for {repo}"
    return commits[-1]


# --- facts that hold regardless of any decision policy ----------------------


@pytest.mark.parametrize("repo", [FINETUNE, ADAPTER, MERGE])
def test_snapshot_loads_offline_and_reproduces_extraction(repo: str):
    """The Phase C evidence is reproduced exactly, with no network access."""
    commit = _commit_of(repo)
    snap_dir = SNAPSHOT_ROOT / repo.replace("/", "__") / commit
    expected = json.loads(
        (snap_dir / "extracted_evidence.json").read_text(encoding="utf-8")
    )
    result = audit_snapshot(repo, commit, root=SNAPSHOT_ROOT)
    assert result is not None
    frozen = extract_repository_evidence(
        repo, commit,
        {
            path.relative_to(snap_dir / "files").as_posix(): path.read_text(encoding="utf-8")
            for path in (snap_dir / "files").rglob("*") if path.is_file()
        },
    )
    assert frozen.model_dump(mode="json") == expected


@pytest.mark.parametrize("repo", [FINETUNE, ADAPTER, MERGE])
def test_declared_and_independent_stay_separated_on_real_data(repo: str):
    commit = _commit_of(repo)
    extraction = extract_repository_evidence(
        repo, commit, _contents(repo, commit)
    )
    assert all(item.role is EvidenceRole.DECLARED for item in extraction.declared_evidence)
    assert all(item.role is EvidenceRole.INDEPENDENT for item in extraction.independent_evidence)
    assert all(
        item.reliability is not Reliability.NOT_APPLICABLE
        for item in extraction.independent_evidence
    )


@pytest.mark.parametrize("repo", [FINETUNE, ADAPTER, MERGE])
def test_no_weights_are_ever_present(repo: str):
    commit = _commit_of(repo)
    assert not any(
        name.endswith((".safetensors", ".bin", ".pt", ".gguf", ".ggml"))
        for name in _contents(repo, commit)
    )


def _contents(repo: str, commit: str) -> dict[str, str]:
    files_root = SNAPSHOT_ROOT / repo.replace("/", "__") / commit / "files"
    return {
        path.relative_to(files_root).as_posix(): path.read_text(encoding="utf-8")
        for path in files_root.rglob("*") if path.is_file()
    }


# --- documented outcomes ----------------------------------------------------


def test_finetune_repository_abstains_on_weak_evidence():
    """OpenHermes declares a parent; only a config bookkeeping hint exists.

    The declared parent is correct-looking, but nothing that *identifies* a
    parent independently (no adapter/training/merge artifact) supports it, and
    no relation is stated anywhere. ABSTAIN is the honest result.
    """
    result = audit_repository(FINETUNE, root=SNAPSHOT_ROOT)
    decision = result.decision
    assert decision.current_lineage.base_model == "mistralai/Mistral-7B-v0.1"
    assert decision.decision is Decision.ABSTAIN
    assert decision.proposed_lineage.is_empty
    assert decision.recommended_patch is None
    assert decision.support_score == pytest.approx(0.30)
    assert {item.source_type for item in decision.supporting_evidence} == {SourceType.CONFIG}
    assert all(item.relation is None for item in decision.supporting_evidence)


def test_adapter_repository_adds_from_one_very_high_source():
    """The adapter declares nothing; adapter_config explicitly names its base."""
    result = audit_repository(ADAPTER, root=SNAPSHOT_ROOT)
    decision = result.decision
    assert decision.current_lineage.base_model is None
    assert decision.decision is Decision.ADD
    assert decision.proposed_lineage.parents == [
        "hf-internal-testing/tiny-random-OPTForCausalLM"
    ]
    assert decision.proposed_lineage.entries[0].relation is Relation.ADAPTER
    assert decision.support_score == pytest.approx(0.75)
    assert decision.recommended_patch is not None
    assert decision.recommended_patch.new_base_model == (
        "hf-internal-testing/tiny-random-OPTForCausalLM"
    )
    assert decision.recommended_patch.new_relation is Relation.ADAPTER


def test_merge_repository_keeps_the_declared_source_set():
    """The interesting case: 3 declared parents vs merge evidence.

    Facts from the frozen evidence:
      * ``mergekit_config.yml`` lists two models under ``models:``
        (Qwen2.5-Coder-1.5B-Instruct, Qwen2.5-Math-1.5B-Instruct) and a
        top-level ``base_model: Qwen/Qwen2.5-1.5B-Instruct``;
      * the declared front matter lists all three.

    ProvenanceLens extracts the top-level ``base_model`` as a third merge
    source (relation left unspecified, because MergeKit's semantics for that
    key are algorithm-specific), so the observed set equals the declared set
    and KEEP is indicated. Under the alternative reading of that key ("repair
    base" rather than a source) the observed set would be a strict subset of
    the declared set, which the policy also treats as KEEP (missing
    corroboration, not a contradiction). Neither reading yields a REPLACE.
    """
    result = audit_repository(MERGE, root=SNAPSHOT_ROOT)
    decision = result.decision
    declared = set(decision.current_lineage.base_models)
    assert declared == {
        "Qwen/Qwen2.5-1.5B-Instruct",
        "Qwen/Qwen2.5-Math-1.5B-Instruct",
        "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    }
    assert decision.decision is Decision.KEEP
    assert set(decision.proposed_lineage.parents) == declared
    assert decision.recommended_patch is None
    assert all(
        entry.relation is Relation.MERGE
        for entry in decision.proposed_lineage.entries
    ) or decision.current_lineage.relation is None


def test_merge_subset_reading_also_keeps_rather_than_narrowing():
    """Reading the top-level base_model as a repair base must not REPLACE."""
    from fixtures.phase_d_evidence import declared as declared_helper

    from provenancelens.reasoning import decide_lineage

    commit = _commit_of(MERGE)
    extraction = extract_repository_evidence(MERGE, commit, _contents(MERGE, commit))
    merge_items = [
        item for item in extraction.independent_evidence
        if item.source_type is SourceType.MERGE_CONFIG and item.relation is Relation.MERGE
    ]
    assert len(merge_items) == 2  # only models[] entries carry the merge relation
    result = decide_lineage(
        MERGE,
        declared_helper("Qwen/Qwen2.5-1.5B-Instruct", "merge", (
            "Qwen/Qwen2.5-Math-1.5B-Instruct",
            "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        )),
        merge_items,
    )
    assert result.decision.decision is not Decision.REPLACE
    assert result.decision.recommended_patch is None


def test_audit_repository_resolves_the_commit_automatically():
    for repo in (FINETUNE, ADAPTER, MERGE):
        by_commit = audit_snapshot(repo, _commit_of(repo), root=SNAPSHOT_ROOT)
        auto = audit_repository(repo, root=SNAPSHOT_ROOT)
        assert auto.decision.decision is by_commit.decision.decision
        assert auto.decision.support_score == by_commit.decision.support_score


def test_audit_output_is_deterministic_for_every_snapshot():
    for repo in (FINETUNE, ADAPTER, MERGE):
        first = audit_repository(repo, root=SNAPSHOT_ROOT)
        second = audit_repository(repo, root=SNAPSHOT_ROOT)
        assert first.decision.model_dump() == second.decision.model_dump()
        assert format_audit_decision(first.decision) == format_audit_decision(second.decision)


# --- reporting --------------------------------------------------------------


def test_report_contains_every_required_section():
    result = audit_repository(ADAPTER, root=SNAPSHOT_ROOT)
    report = format_audit_decision(result.decision)
    for section in (
        "TARGET", "CURRENT LINEAGE", "DECISION", "PROPOSED LINEAGE", "SUPPORT SCORE",
        "SUPPORTING EVIDENCE", "CONTRADICTORY EVID", "CONFLICTS", "REASONING SUMMARY",
        "SUGGESTED PATCH",
    ):
        assert section in report
    assert "NOT a probability" in report


def test_abstain_report_has_no_patch():
    result = audit_repository(FINETUNE, root=SNAPSHOT_ROOT)
    report = format_audit_decision(result.decision)
    assert "SUGGESTED PATCH     :\n    none" in report
    assert "PROPOSED LINEAGE    :\nnone" in report


def test_patch_is_only_a_recommendation_and_never_written():
    """The engine returns a patch object; nothing touches the repository."""
    result = audit_repository(ADAPTER, root=SNAPSHOT_ROOT)
    patch = result.decision.recommended_patch
    assert patch is not None
    assert not hasattr(patch, "commit")
    assert not hasattr(patch, "push")
    # the frozen snapshot on disk is untouched by the audit
    before = {
        path: path.read_bytes()
        for path in (SNAPSHOT_ROOT / ADAPTER.replace("/", "__")).rglob("*")
        if path.is_file()
    }
    audit_repository(ADAPTER, root=SNAPSHOT_ROOT)
    after = {path: path.read_bytes() for path in before}
    assert before == after


def test_audit_extraction_accepts_parsed_evidence_directly():
    commit = _commit_of(ADAPTER)
    extraction = extract_repository_evidence(ADAPTER, commit, _contents(ADAPTER, commit))
    result = audit_extraction(extraction)
    assert result.decision.decision is Decision.ADD
    assert result.candidates.has_usable_candidate is True
