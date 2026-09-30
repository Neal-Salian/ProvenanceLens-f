"""Real-repository smoke tests + frozen-snapshot reproducibility.

Network tests are OFF by default so the suite stays offline and
deterministic. Enable them with:

    PROVENANCELENS_NETWORK_TESTS=1 python3 -m pytest -q tests/test_smoke_network.py

The offline test always runs against the frozen snapshots committed in
``data/snapshots/`` and re-derives their extraction output byte-for-byte.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from provenancelens.collectors import HuggingFaceCollector
from provenancelens.parsers import extract_repository_evidence
from provenancelens.schemas import (
    CollectionStatus,
    EvidenceRole,
    Relation,
    Reliability,
    SourceType,
    split_by_role,
)
from provenancelens.snapshots import load_snapshot, save_extracted_evidence, save_snapshot

_NETWORK_ENABLED = os.environ.get("PROVENANCELENS_NETWORK_TESTS") == "1"
needs_network = pytest.mark.skipif(
    not _NETWORK_ENABLED,
    reason="set PROVENANCELENS_NETWORK_TESTS=1 to run live Hugging Face tests",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"

FINETUNE_REPO = "teknium/OpenHermes-2.5-Mistral-7B"
ADAPTER_REPO = "peft-internal-testing/tiny-OPTForCausalLM-lora"
MERGE_REPO = "mergekit-community/Qwen3-1.5B-Instruct"


def _run_pipeline(repo: str, root: Path):
    """Collect -> freeze -> load offline -> extract (the full Phase C path)."""
    result = HuggingFaceCollector().collect(repo)
    assert result.status in {
        CollectionStatus.SUCCESS,
        CollectionStatus.PARTIAL,
        CollectionStatus.NO_RELEVANT_FILES,
    }, f"{repo}: unexpected status {result.status}"
    save_snapshot(result, root=root)
    loaded = load_snapshot(repo, result.resolved_commit_sha, root=root)
    extraction = extract_repository_evidence(
        repo, result.resolved_commit_sha, loaded.contents
    )
    save_extracted_evidence(
        repo, result.resolved_commit_sha,
        extraction.model_dump(mode="json"), root=root,
    )
    return result, loaded, extraction


# --- live network tests (opt-in) --------------------------------------------


@needs_network
def test_real_finetune_repository(tmp_path: Path):
    result, loaded, extraction = _run_pipeline(FINETUNE_REPO, tmp_path)
    # declared subject from the model-card front matter
    assert extraction.declared_lineage.base_model == "mistralai/Mistral-7B-v0.1"
    declared, independent = split_by_role(
        [*extraction.declared_evidence, *extraction.independent_evidence]
    )
    assert declared == extraction.declared_evidence
    assert independent == extraction.independent_evidence
    # independent corroboration exists but claims no relation of its own
    assert any(
        i.candidate_parent == "mistralai/Mistral-7B-v0.1" and i.relation is None
        for i in extraction.independent_evidence
    )
    # weights are never present in the snapshot
    assert not any(n.endswith((".safetensors", ".bin")) for n in loaded.contents)
    # second pass from the frozen snapshot is identical
    again = extract_repository_evidence(
        FINETUNE_REPO, result.resolved_commit_sha, loaded.contents
    )
    assert extraction.model_dump() == again.model_dump()


@needs_network
def test_real_adapter_repository(tmp_path: Path):
    _, loaded, extraction = _run_pipeline(ADAPTER_REPO, tmp_path)
    assert "adapter_config.json" in loaded.contents
    assert "adapter_model.bin" not in loaded.contents  # weights never fetched
    adapter_items = [
        i for i in extraction.independent_evidence
        if i.source_type is SourceType.ADAPTER_CONFIG
    ]
    assert adapter_items, "expected adapter evidence"
    item = adapter_items[0]
    assert item.relation is Relation.ADAPTER
    assert item.reliability is Reliability.VERY_HIGH
    assert item.candidate_parent == "hf-internal-testing/tiny-random-OPTForCausalLM"
    assert item.role is EvidenceRole.INDEPENDENT
    assert item.key_path == "base_model_name_or_path"


@needs_network
def test_real_merge_repository(tmp_path: Path):
    _, loaded, extraction = _run_pipeline(MERGE_REPO, tmp_path)
    assert "mergekit_config.yml" in loaded.contents
    # declared: multiple base models from the front matter
    assert extraction.declared_lineage.base_models[0] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert len(extraction.declared_lineage.base_models) >= 3
    # independent: merge sources carry the MERGE relation
    merge_parents = {
        i.candidate_parent for i in extraction.independent_evidence
        if i.relation is Relation.MERGE
    }
    assert {
        "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "Qwen/Qwen2.5-Math-1.5B-Instruct",
    } <= merge_parents
    # top-level base_model in the merge config: extracted, relation untouched
    top = [
        i for i in extraction.independent_evidence
        if i.key_path == "base_model" and i.source_type is SourceType.MERGE_CONFIG
    ]
    assert top and top[0].relation is None
    # declared subject never contributes independent proof
    assert all(i.role is EvidenceRole.INDEPENDENT for i in extraction.independent_evidence)


# --- offline: committed snapshots stay reproducible --------------------------


def _committed_snapshots() -> list[tuple[str, str, Path]]:
    found = []
    for manifest_path in sorted(SNAPSHOT_ROOT.glob("*/*/manifest.json")):
        snap_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        found.append((manifest["repository"], snap_dir.name, snap_dir))
    return found


def test_committed_snapshots_exist():
    snapshots = _committed_snapshots()
    assert len(snapshots) == 3, f"expected 3 frozen snapshots, found {len(snapshots)}"


def test_committed_snapshots_extract_deterministically():
    for repo, commit, snap_dir in _committed_snapshots():
        loaded = load_snapshot(repo, commit, root=SNAPSHOT_ROOT)
        extraction = extract_repository_evidence(repo, commit, loaded.contents)
        expected = json.loads(
            (snap_dir / "extracted_evidence.json").read_text(encoding="utf-8")
        )
        assert extraction.model_dump(mode="json") == expected, (
            f"{repo}: offline re-extraction differs from frozen output"
        )
        # architectural invariant holds on real data
        assert all(i.role is EvidenceRole.INDEPENDENT for i in extraction.independent_evidence)
        assert all(i.role is EvidenceRole.DECLARED for i in extraction.declared_evidence)
        # no weights, ever
        assert not any(
            n.endswith((".safetensors", ".bin", ".pt", ".gguf")) for n in loaded.contents
        )


def test_committed_snapshot_manifests_are_sourced():
    for repo, _, snap_dir in _committed_snapshots():
        manifest = json.loads((snap_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["schema_version"] == 1
        assert manifest["repository"] == repo
        retrieved = manifest["retrieved"]
        assert retrieved and all(f["sha256"] for f in retrieved)
        assert all(
            f["source_url"].startswith("https://huggingface.co/") for f in retrieved
        )
