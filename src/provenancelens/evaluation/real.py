"""LineageRepairBench REAL track: adjudicated frozen snapshots.

Ground truth lives in a human-reviewable file
(:mod:`provenancelens.evaluation.adjudication` -> ``adjudication/real_cases.yaml``)
and is **never** derived from ProvenanceLens predictions. Each record pins the
frozen commit, the artifacts it was adjudicated from, and the precedence rule
that produced the label.
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
    "ADJUDICATION_FILE",
    "ADJUDICATOR",
    "PRECEDENCE",
    "load_adjudication_file",
    "load_real_benchmark",
    "snapshot_root",
    "adjudication_summary",
    "real_case_index",
]

ADJUDICATOR = "Phase G manual adjudication (frozen artifacts)"
ADJUDICATION_FILE = Path(__file__).resolve().parent / "adjudication" / "real_cases.yaml"
DEFAULT_SNAPSHOT_ROOT = Path("data/snapshots")

#: Documented adjudication precedence (also recorded in the YAML header).
PRECEDENCE: tuple[str, ...] = (
    "P1 tool-generated lineage field (adapter_config.json, mergekit models list) "
    "determines parent and the relation it implies",
    "P2 model-card body statement with a canonical org/model id determines the parent, "
    "and the relation when the wording states one",
    "P3 declared front-matter field alone is the audit subject, never independent "
    "ground truth; it counts only when an artifact corroborates it",
    "P4 name, family, architecture, tokenizer or popularity resemblance is never truth",
)


def snapshot_root(root: Path | None = None) -> Path:
    """Snapshot root, defaulting to the repository's committed snapshots."""
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[3] / DEFAULT_SNAPSHOT_ROOT


def load_adjudication_file(path: Path | None = None) -> dict[str, Any]:
    """Parse the adjudication YAML (the reviewable source of REAL labels)."""
    import yaml

    data = yaml.safe_load((path or ADJUDICATION_FILE).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"malformed adjudication file: {path or ADJUDICATION_FILE}")
    return data


def _read_snapshot_files(root: Path, repository: str, commit: str) -> dict[str, str]:
    directory = Path(root) / repository.replace("/", "__") / commit
    manifest = directory / "manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(
            f"no frozen snapshot for {repository!r} at {commit}; run the acquisition "
            "command to freeze it (network required)"
        )
    files_root = directory / "files"
    return {
        path.relative_to(files_root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(files_root.rglob("*")) if path.is_file()
    }


_SELECTION_CACHE: dict[str, str] | None = None


def acquisition_strata() -> dict[str, str]:
    """Repository -> acquisition stratum, from the frozen selection record.

    The selection record is the audit trail of *how* the real track was
    sampled; stratification in the analysis uses it so the strata are the
    ones the plan declared, not ones derived from measured outcomes.
    """
    global _SELECTION_CACHE
    if _SELECTION_CACHE is None:
        path = snapshot_root(None).parent / "acquisition" / "real_selection.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        _SELECTION_CACHE = {
            record["repository"]: record["stratum"] for record in data["records"]
        }
    return dict(_SELECTION_CACHE)


def _acquisition_stratum(repository: str) -> str:
    return acquisition_strata().get(repository, "pre_phase_g")


def _case_from_record(record: dict[str, Any], files: dict[str, str]) -> BenchmarkCase:
    from ..parsers import extract_repository_evidence

    # Declared metadata is read from the frozen snapshot (mechanical, not a label):
    # it is the audit subject and the validator checks consistency against it.
    extraction = extract_repository_evidence(record["repository"], record["commit"], files)
    declared_lineage = extraction.declared_lineage
    parents_status = TruthStatus(record["parents_status"])
    relation_status = TruthStatus(record["relation_status"])
    truth = GroundTruth(
        parents=tuple(record["parents"]) or None,
        parents_status=parents_status,
        relation=Relation(record["relation"]) if record.get("relation") else None,
        relation_status=relation_status,
        metadata_state=MetadataState(record["metadata_state"]),
        parent_set_alternatives=tuple(
            tuple(alt) for alt in record.get("parent_set_alternatives", [])
        ),
        rationale=record["rationale"],
    )
    expected = Decision(record["expected_action"])
    acceptable = tuple(Decision(a) for a in record.get("acceptable_actions", [expected.value]))
    return BenchmarkCase(
        case_id=f"REAL-{record['repository']}",
        track=Track.REAL,
        title=record.get("title") or record["repository"],
        repository=record["repository"],
        snapshot_commit=record["commit"],
        snapshot_files=files,
        declared_base_model=declared_lineage.base_model,
        declared_relation_raw=declared_lineage.relation_raw,
        declared_additional_base_models=tuple(declared_lineage.additional_base_models),
        truth=truth,
        expected_action=expected,
        acceptable_actions=acceptable or (expected,),
        adjudication=Adjudication(
            provenance=LabelProvenance.MANUAL_ADJUDICATION,
            adjudicator=ADJUDICATOR,
            evidence_used=tuple(sorted(files)),
            evidence_excerpt=record.get("evidence_summary"),
            notes=record["rationale"],
        ),
        repairable=expected in (Decision.ADD, Decision.REPLACE),
        tags=(
            "real",
            "frozen-snapshot",
            f"stratum:{_acquisition_stratum(record['repository'])}",
            *record.get("tags", ()),
        ),
    )


def load_real_benchmark(
    root: Path | None = None,
    *,
    repositories: tuple[str, ...] | None = None,
    adjudication_file: Path | None = None,
) -> list[BenchmarkCase]:
    """Materialise the REAL track from adjudications + frozen snapshots (offline)."""
    resolved_root = snapshot_root(root)
    data = load_adjudication_file(adjudication_file)
    cases: list[BenchmarkCase] = []
    for record in data["cases"]:
        repository = record["repository"]
        if repositories is not None and repository not in repositories:
            continue
        files = _read_snapshot_files(resolved_root, repository, record["commit"])
        cases.append(_case_from_record(record, files))
    return cases


def adjudication_summary(
    root: Path | None = None, *, adjudication_file: Path | None = None
) -> list[dict[str, Any]]:
    """Reviewer-facing rows: declared vs adjudicated, per case."""
    from ..parsers import extract_repository_evidence

    resolved_root = snapshot_root(root)
    data = load_adjudication_file(adjudication_file)
    rows: list[dict[str, Any]] = []
    for record in data["cases"]:
        files = _read_snapshot_files(resolved_root, record["repository"], record["commit"])
        extraction = extract_repository_evidence(
            record["repository"], record["commit"], files
        )
        rows.append({
            "repository": record["repository"],
            "commit": record["commit"][:12],
            "declared_parents": list(extraction.declared_lineage.base_models),
            "declared_relation_raw": extraction.declared_lineage.relation_raw,
            "adjudicated_parents": list(record["parents"]),
            "parents_status": record["parents_status"],
            "adjudicated_relation": record["relation"],
            "relation_status": record["relation_status"],
            "metadata_state": record["metadata_state"],
            "expected_action": record["expected_action"],
            "acceptable_actions": list(record.get("acceptable_actions", [])),
            "evidence_files": sorted(files),
            "evidence_summary": record["evidence_summary"],
            "ambiguity": record["parents_status"] != "known",
            "rationale": record["rationale"],
        })
    return rows


def real_case_index(cases: list[BenchmarkCase]) -> dict[str, dict[str, Any]]:
    """Compact index used by documentation and reports."""
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
