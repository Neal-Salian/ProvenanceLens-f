"""Reproducible acquisition of REAL-track repository snapshots.

Acquisition is **network-bound and explicit**: it is never part of the test
suite and never runs during evaluation. Evaluation only ever reads the frozen
snapshots this module produces, offline.

Selection methodology (fixed, documented, and deliberately not curated)
----------------------------------------------------------------------
The goal is an *observational* sample stratified by **evidence shape**, not a
hand-picked list of favourable repositories. Each stratum is a deterministic
Hub query; candidates are ordered by ``(downloads desc, id asc)`` and the
first ``take`` that pass the inclusion criteria are frozen. No candidate is
ever swapped out because its adjudication would be inconvenient - a stratum
that yields ambiguous or unknowable cases keeps them.

Inclusion criteria
    1. the repository resolves publicly and freezes at a pinned commit;
    2. collection yields at least one provenance-relevant artifact
       (model card, config, adapter/merge/training configuration);
    3. the frozen snapshot stays under :data:`SNAPSHOT_MAX_BYTES`;
    4. the repository is not already part of the benchmark.

Exclusion criteria (recorded, never silent)
    * gated, private, missing, or unreachable repositories;
    * no provenance-relevant artifact (e.g. weights-only mirrors);
    * snapshots above the size budget (safety is never weakened to grow N);
    * repositories already in the benchmark.

Safety
    Reuses the Phase C collector unchanged: weights and binary artifacts are
    excluded by type, the 1 MiB per-file cap and the metadata size check
    apply, and only text artifacts are stored. No model weights are ever
    fetched, and no model is ever downloaded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ConfigDict

from ..schemas.collection import CollectionStatus
from ..snapshots import DEFAULT_SNAPSHOT_ROOT, SnapshotError, save_snapshot

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..collectors import HuggingFaceCollector

__all__ = [
    "SNAPSHOT_MAX_BYTES",
    "Stratum",
    "STRATA",
    "CandidateRecord",
    "AcquisitionReport",
    "enumerate_candidates",
    "acquire_real_snapshots",
]

#: Total frozen bytes allowed per repository (text artifacts only).
SNAPSHOT_MAX_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Stratum:
    """One documented selection stratum."""

    name: str
    description: str
    query: Callable[[], list]
    take: int
    #: Requests per stratum before ordering (keeps ordering stable).
    pool: int = 60


def _list_models(**kwargs):
    """Return a *lazy* Hub query.

    The client is imported inside the closure, never at module import time:
    importing the evaluation package must not touch the network stack, and
    ``STRATA`` is built at import time to document the frozen selection plan.
    """

    def _query() -> list:
        from huggingface_hub import HfApi

        return list(HfApi().list_models(**kwargs))

    return _query


#: The frozen selection plan. Changing it changes the benchmark, so the plan is
#: part of the code and its results are recorded in the acquisition report.
STRATA: tuple[Stratum, ...] = (
    Stratum(
        name="peft_adapters",
        description="models tagged with the PEFT library (adapter repositories)",
        query=_list_models(filter="peft", sort="downloads", limit=60),
        take=8,
    ),
    Stratum(
        name="mergekit_merges",
        description="model cards mentioning mergekit (merge configurations)",
        query=_list_models(search="mergekit", sort="downloads", limit=80),
        take=8,
    ),
    Stratum(
        name="lora_adapters",
        description="models tagged LoRA (adapter or fine-tune repositories)",
        query=_list_models(filter="lora", sort="downloads", limit=60),
        take=6,
    ),
    Stratum(
        name="quantized_gguf",
        description="GGUF distributions (quantized derivatives of base models)",
        query=_list_models(search="gguf", sort="downloads", limit=60),
        take=6,
    ),
    Stratum(
        name="quantized_awq",
        description="AWQ distributions (quantized derivatives of base models)",
        query=_list_models(search="awq", sort="downloads", limit=40),
        take=5,
    ),
    Stratum(
        name="instruction_finetunes",
        description="popular instruct/chat derivatives (typical fine-tunes)",
        query=_list_models(search="instruct", sort="downloads", limit=60),
        take=8,
    ),
)


class CandidateRecord(BaseModel):
    """Why a candidate was frozen or skipped (kept for reproducibility)."""

    model_config = ConfigDict(extra="forbid")

    repository: str
    stratum: str
    downloads: int | None = None
    included: bool
    reason: str
    commit: str | None = None
    status: str | None = None
    files: tuple[str, ...] = ()
    snapshot_bytes: int | None = None


class AcquisitionReport(BaseModel):
    """Full, reproducible record of one acquisition run."""

    model_config = ConfigDict(extra="forbid")

    snapshot_root: str
    collector_statuses: tuple[str, ...] = ()
    records: tuple[CandidateRecord, ...] = ()
    n_included: int = 0
    n_excluded: int = 0
    notes: tuple[str, ...] = ()

    def excluded(self) -> list[CandidateRecord]:
        return [record for record in self.records if not record.included]

    def included(self) -> list[CandidateRecord]:
        return [record for record in self.records if record.included]


def _order(models: list) -> list:
    """Deterministic ordering: popularity desc, then id asc."""
    return sorted(models, key=lambda m: (-(getattr(m, "downloads", 0) or 0),
                                        str(getattr(m, "id", ""))))


def enumerate_candidates(
    strata: tuple[Stratum, ...] = STRATA,
    *,
    already: frozenset[str] = frozenset(),
) -> list[tuple[str, object]]:
    """Apply the documented plan and return (stratum, candidate) pairs."""
    selected: list[tuple[str, object]] = []
    seen: set[str] = set(already)
    for stratum in strata:
        try:
            models = _order(stratum.query())
        except Exception as exc:  # network/query failure is recorded by the caller
            selected.append((stratum.name, exc))  # type: ignore[arg-type]
            continue
        taken = 0
        for model in models:
            if taken >= stratum.take:
                break
            repository = str(getattr(model, "id", ""))
            if not repository or repository in seen:
                continue
            seen.add(repository)
            selected.append((stratum.name, model))
            taken += 1
    return selected


def _snapshot_size(snapshot_dir: Path) -> int:
    return sum(
        path.stat().st_size
        for path in snapshot_dir.rglob("*") if path.is_file()
    )


def acquire_real_snapshots(
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    strata: tuple[Stratum, ...] = STRATA,
    already: frozenset[str] = frozenset(),
    collector: HuggingFaceCollector | None = None,
    dry_run: bool = False,
) -> AcquisitionReport:
    """Freeze the documented candidate set (network required).

    With ``dry_run=True`` the selection is reported without any download.
    """
    if collector is None:
        # imported lazily so that importing the evaluation package never pulls in
        # an HTTP client: evaluation and acquisition must stay separable offline
        from ..collectors import HuggingFaceCollector

        collector = HuggingFaceCollector()
    records: list[CandidateRecord] = []

    for stratum_name, candidate in enumerate_candidates(strata, already=already):
        if isinstance(candidate, Exception):
            records.append(CandidateRecord(
                repository="", stratum=stratum_name, included=False,
                reason=f"query failed: {type(candidate).__name__}",
            ))
            continue
        repository = str(getattr(candidate, "id", ""))
        downloads = getattr(candidate, "downloads", None)

        if dry_run:
            records.append(CandidateRecord(
                repository=repository, stratum=stratum_name, downloads=downloads,
                included=False, reason="dry run: not collected",
            ))
            continue

        result = collector.collect(repository)
        if result.status not in (
            CollectionStatus.SUCCESS, CollectionStatus.PARTIAL
        ):
            records.append(CandidateRecord(
                repository=repository, stratum=stratum_name, downloads=downloads,
                included=False, reason=f"collection status {result.status.value}",
                status=result.status.value,
            ))
            continue
        if not result.contents:
            records.append(CandidateRecord(
                repository=repository, stratum=stratum_name, downloads=downloads,
                included=False, reason="no provenance-relevant artifact",
                status=result.status.value,
            ))
            continue

        commit = str(result.resolved_commit_sha)
        snapshot_dir = root / repository.replace("/", "__") / commit
        if snapshot_dir.exists() and (snapshot_dir / "manifest.json").is_file():
            records.append(CandidateRecord(
                repository=repository, stratum=stratum_name, downloads=downloads,
                included=True, reason="already frozen", commit=commit,
                status=result.status.value, files=tuple(sorted(result.contents)),
                snapshot_bytes=_snapshot_size(snapshot_dir),
            ))
            continue

        try:
            save_snapshot(result, root=root)
        except SnapshotError as exc:
            records.append(CandidateRecord(
                repository=repository, stratum=stratum_name, downloads=downloads,
                included=False, reason=f"snapshot refused: {exc}",
                commit=commit, status=result.status.value,
            ))
            continue

        size = _snapshot_size(snapshot_dir)
        if size > SNAPSHOT_MAX_BYTES:
            records.append(CandidateRecord(
                repository=repository, stratum=stratum_name, downloads=downloads,
                included=False,
                reason=f"snapshot {size} B exceeds budget {SNAPSHOT_MAX_BYTES} B",
                commit=commit, status=result.status.value,
                files=tuple(sorted(result.contents)), snapshot_bytes=size,
            ))
            continue

        records.append(CandidateRecord(
            repository=repository, stratum=stratum_name, downloads=downloads,
            included=True, reason="frozen from documented stratum",
            commit=commit, status=result.status.value,
            files=tuple(sorted(result.contents)), snapshot_bytes=size,
        ))

    included = [r for r in records if r.included]
    excluded = [r for r in records if not r.included]
    return AcquisitionReport(
        snapshot_root=str(root),
        records=tuple(records),
        n_included=len(included),
        n_excluded=len(excluded),
        notes=(
            "selection is stratified by evidence shape with fixed per-stratum quotas",
            "candidates ordered by (downloads desc, id asc)",
            "exclusions are recorded, never silently dropped",
        ),
    )
