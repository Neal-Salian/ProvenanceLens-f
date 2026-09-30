"""LineageRepairBench REAL track: frozen snapshots with manual adjudication.

Ground truth is **adjudicated from the frozen repository evidence and the
published provenance of the model**, never copied from ProvenanceLens output.
Where the frozen evidence cannot settle a question, the case is labelled
ambiguous/undetermined instead of being given an invented label.

Adjudication notes per case record what the label rests on, which files were
read, and why the alternative readings were rejected or left open.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas.audit import Decision
from ..schemas.lineage import Relation
from .schema import (
    Adjudication,
    BenchmarkCase,
    GroundTruth,
    LabelProvenance,
    MetadataState,
    Track,
    TruthStatus,
)

__all__ = [
    "REAL_CASE_SPECS",
    "ADJUDICATOR",
    "load_real_benchmark",
    "snapshot_root",
    "default_snapshot_root",
]

ADJUDICATOR = "Phase F real-track adjudication (manual, from frozen evidence)"

DEFAULT_SNAPSHOT_ROOT = Path("data/snapshots")


def snapshot_root(root: Path | None = None) -> Path:
    """Snapshot root, defaulting to the repository's committed snapshots."""
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[3] / DEFAULT_SNAPSHOT_ROOT


class _RealSpec:
    """Adjudication specification for one real repository (no evidence blobs)."""

    def __init__(
        self,
        repository: str,
        title: str,
        truth: GroundTruth,
        expected_action: Decision,
        acceptable: tuple[Decision, ...],
        evidence_used: tuple[str, ...],
        excerpt: str | None,
        notes: str,
    ) -> None:
        self.repository = repository
        self.title = title
        self.truth = truth
        self.expected_action = expected_action
        self.acceptable = acceptable
        self.evidence_used = evidence_used
        self.excerpt = excerpt
        self.notes = notes


def _adapter_truth(parent: str) -> GroundTruth:
    return GroundTruth(
        parents=(parent,),
        parents_status=TruthStatus.KNOWN,
        relation=Relation.ADAPTER,
        relation_status=TruthStatus.KNOWN,
        metadata_state=MetadataState.MISSING,
        rationale=(
            "adapter_config.json is written by the PEFT library when the adapter is "
            "saved: base_model_name_or_path records the base checkpoint the adapter was "
            "trained on, and peft_type=LORA identifies the transformation as an adapter. "
            "The repository's model card declares no base_model at all, so the lineage "
            "metadata is missing rather than wrong."
        ),
    )


REAL_CASE_SPECS: tuple[_RealSpec, ...] = (
    _RealSpec(
        repository="peft-internal-testing/tiny-OPTForCausalLM-lora",
        title="PEFT LoRA adapter whose model card declares no lineage",
        truth=_adapter_truth("hf-internal-testing/tiny-random-OPTForCausalLM"),
        expected_action=Decision.ADD,
        acceptable=(Decision.ADD,),
        evidence_used=("adapter_config.json",),
        excerpt=(
            '"peft_type": "LORA", "task_type": "CAUSAL_LM", '
            '"base_model_name_or_path": "hf-internal-testing/tiny-random-OPTForCausalLM"'
        ),
        notes=(
            "Adjudicated from a tool-generated artifact, so the label does not depend on "
            "the card's own claims. A LoRA adapter is not a finetune of the base model "
            "in the direct-parent sense: the adapter config states the base, and the "
            "repository itself states nothing else."
        ),
    ),
    _RealSpec(
        repository="teknium/OpenHermes-2.5-Mistral-7B",
        title="Finetune whose declared parent is corroborated but never related",
        truth=GroundTruth(
            parents=("mistralai/Mistral-7B-v0.1",),
            parents_status=TruthStatus.KNOWN,
            relation=None,
            relation_status=TruthStatus.UNKNOWN,
            metadata_state=MetadataState.UNDETERMINED,
            rationale=(
                "Two artifacts name mistralai/Mistral-7B-v0.1: the model-card front "
                "matter (declared) and config.json _name_or_path (framework written), "
                "so the parent identity is corroborated and is not demonstrably wrong. "
                "No artifact in the snapshot states the transformation relation: the "
                "card says only 'OpenHermes 2.5 Mistral 7B is a state of the art Mistral "
                "Fine-tune, a continuation of OpenHermes 2 model' - a bare family name "
                "and a different intermediate model, neither carrying a canonical id. "
                "The declaration is therefore neither verifiably complete nor verifiably "
                "incorrect, so no automated change is safe."
            ),
        ),
        expected_action=Decision.ABSTAIN,
        acceptable=(Decision.KEEP, Decision.ABSTAIN),
        evidence_used=("README.md", "config.json"),
        excerpt=(
            "front matter: base_model: mistralai/Mistral-7B-v0.1 (no "
            "base_model_relation); config.json: \"_name_or_path\": "
            "\"mistralai/Mistral-7B-v0.1\""
        ),
        notes=(
            "Deliberately NOT labelled 'incorrect': the missing relation is a completeness "
            "gap, not a demonstrated error, and adding a relation would require evidence "
            "the snapshot does not contain. External knowledge that the model is a "
            "Mistral-7B-v0.1 finetune is deliberately not used as a label: the benchmark "
            "scores what the stored evidence supports."
        ),
    ),
    _RealSpec(
        repository="mergekit-community/Qwen3-1.5B-Instruct",
        title="MergeKit output whose declared source set has two defensible readings",
        truth=GroundTruth(
            parents=("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-Coder-1.5B-Instruct",
                     "Qwen/Qwen2.5-Math-1.5B-Instruct"),
            parents_status=TruthStatus.AMBIGUOUS,
            relation=Relation.MERGE,
            relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.UNDETERMINED,
            parent_set_alternatives=(
                ("Qwen/Qwen2.5-Coder-1.5B-Instruct", "Qwen/Qwen2.5-Math-1.5B-Instruct"),
                ("Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen2.5-Coder-1.5B-Instruct",
                 "Qwen/Qwen2.5-Math-1.5B-Instruct"),
            ),
            rationale=(
                "mergekit_config.yml lists two models under 'models:' (Coder and Math) "
                "with merge_method 'ties' and additionally sets 'base_model: "
                "Qwen/Qwen2.5-1.5B-Instruct'; the card's 'Models Merged' section lists "
                "only Math and Coder, while its merge sentence names 1.5B-Instruct too. "
                "Whether MergeKit's top-level base_model is an additional merged source "
                "or the base the merge is residual-ised onto is an algorithm-semantics "
                "question the stored evidence does not settle, so the source set is "
                "labelled ambiguous. Under either reading the declared set is not "
                "demonstrably wrong."
            ),
        ),
        expected_action=Decision.ABSTAIN,
        acceptable=(Decision.KEEP, Decision.ABSTAIN),
        evidence_used=("mergekit_config.yml", "README.md", "config.json"),
        excerpt=(
            "models: [Qwen/Qwen2.5-Coder-1.5B-Instruct, Qwen/Qwen2.5-Math-1.5B-Instruct]; "
            "merge_method: ties; base_model: Qwen/Qwen2.5-1.5B-Instruct"
        ),
        notes=(
            "This is the interesting natural conflict: three declared parents against "
            "two merge slots. Labelling either set as truth would encode a MergeKit "
            "interpretation rather than an adjudicated fact, so the case is ambiguous and "
            "only 'do not change the metadata silently' is expected."
        ),
    ),
)


def _read_snapshot_files(root: Path, repository: str) -> tuple[str, dict[str, str]]:
    directory = root / repository.replace("/", "__")
    if not directory.is_dir():
        raise FileNotFoundError(
            f"no frozen snapshot for {repository!r} under {root}; run the Phase C "
            "snapshot tests to materialise it"
        )
    commits = sorted(path.name for path in directory.iterdir()
                     if (path / "manifest.json").is_file())
    if not commits:
        raise FileNotFoundError(f"no manifest found for {repository!r} under {directory}")
    commit = commits[-1]
    manifest = json.loads(
        (directory / commit / "manifest.json").read_text(encoding="utf-8")
    )
    files_root = directory / commit / "files"
    files = {
        path.relative_to(files_root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(files_root.rglob("*")) if path.is_file()
    }
    return str(manifest.get("resolved_commit_sha") or commit), files


def load_real_benchmark(
    root: Path | None = None, *, repositories: tuple[str, ...] | None = None
) -> list[BenchmarkCase]:
    """Materialise the REAL track from frozen snapshots (offline, read-only)."""
    resolved_root = snapshot_root(root)
    specs = REAL_CASE_SPECS
    if repositories is not None:
        specs = tuple(spec for spec in specs if spec.repository in repositories)

    cases: list[BenchmarkCase] = []
    for spec in specs:
        commit, files = _read_snapshot_files(resolved_root, spec.repository)
        cases.append(BenchmarkCase(
            case_id=f"REAL-{spec.repository}",
            track=Track.REAL,
            title=spec.title,
            repository=spec.repository,
            snapshot_commit=commit,
            snapshot_files=files,
            truth=spec.truth,
            expected_action=spec.expected_action,
            acceptable_actions=spec.acceptable,
            adjudication=Adjudication(
                provenance=LabelProvenance.MANUAL_ADJUDICATION,
                adjudicator=ADJUDICATOR,
                evidence_used=spec.evidence_used,
                evidence_excerpt=spec.excerpt,
                notes=spec.notes,
            ),
            repairable=spec.expected_action in (Decision.ADD, Decision.REPLACE),
            tags=("real", "frozen-snapshot"),
        ))
    return cases


def real_case_index(cases: list[BenchmarkCase]) -> dict[str, dict[str, Any]]:
    """Convenience mapping used by documentation and reports."""
    return {
        case.case_id: {
            "repository": case.repository,
            "commit": case.snapshot_commit,
            "expected_action": case.expected_action.value,
            "metadata_state": case.truth.metadata_state.value,
            "parents_status": case.truth.parents_status.value,
            "files": sorted(case.snapshot_files or {}),
        }
        for case in cases
    }
