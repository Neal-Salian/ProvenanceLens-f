"""Offline orchestration: frozen snapshot -> structured evidence -> AuditDecision.

The pipeline adds no collection and no network access: it consumes either a
frozen Phase C snapshot or an already-extracted :class:`EvidenceExtraction`,
which is what makes the Phase D reasoning engine reproducible on stored
evidence.

    snapshot ─► parse evidence ─► resolve identifiers ─► aggregate candidates
              ─► detect conflicts ─► fuse evidence ─► decide ─► AuditDecision
"""

from __future__ import annotations

from pathlib import Path

from .reasoning import DEFAULT_POLICY, DecisionPolicy, DecisionResult, decide_lineage
from .schemas.audit import AuditDecision
from .schemas.extraction import EvidenceExtraction
from .snapshots import DEFAULT_SNAPSHOT_ROOT, LoadedSnapshot, load_snapshot

__all__ = [
    "audit_snapshot",
    "to_audit_decision",
    "audit_extraction",
    "audit_repository",
    "DecisionResult",
]


def audit_extraction(
    extraction: EvidenceExtraction,
    *,
    policy: DecisionPolicy = DEFAULT_POLICY,
) -> DecisionResult:
    """Run the Phase D engine on already-extracted structured evidence."""
    evidence = [
        *extraction.declared_evidence,
        *extraction.independent_evidence,
    ]
    return decide_lineage(
        extraction.repository,
        extraction.declared_lineage,
        evidence,
        policy=policy,
    )


def audit_snapshot(
    repository: str,
    commit: str,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    policy: DecisionPolicy = DEFAULT_POLICY,
    snapshot: LoadedSnapshot | None = None,
) -> DecisionResult:
    """Audit a frozen snapshot entirely offline (parse -> decide)."""
    from .parsers import extract_repository_evidence  # local: keeps import cost low

    loaded = snapshot if snapshot is not None else load_snapshot(
        repository, commit, root=root
    )
    extraction = extract_repository_evidence(repository, commit, loaded.contents)
    return audit_extraction(extraction, policy=policy)


def audit_repository(
    repository: str,
    commit: str | None = None,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    policy: DecisionPolicy = DEFAULT_POLICY,
) -> DecisionResult:
    """Audit a repository from its newest frozen snapshot under ``root``.

    The commit is resolved from the snapshot directories, so callers do not
    have to know the sha; passing ``commit`` audits that exact snapshot.
    """
    if commit is None:
        encoded = repository.replace("/", "__")
        candidates = sorted(
            path.name
            for path in (Path(root) / encoded).iterdir()
            if (path / "manifest.json").is_file()
        ) if (Path(root) / encoded).is_dir() else []
        if not candidates:
            raise FileNotFoundError(
                f"no frozen snapshot for {repository!r} under {root}"
            )
        commit = candidates[-1]
    return audit_snapshot(repository, commit, root=root, policy=policy)


def to_audit_decision(result: DecisionResult) -> AuditDecision:
    """The public Phase D output object."""
    return result.decision
