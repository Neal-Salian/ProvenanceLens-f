"""Offline orchestration: frozen snapshot -> structured evidence -> AuditDecision.

The pipeline adds no collection and no network access: it consumes either a
frozen Phase C snapshot or an already-extracted :class:`EvidenceExtraction`,
which is what makes the Phase D reasoning engine reproducible on stored
evidence.

    snapshot ─► parse evidence ─► resolve identifiers ─► aggregate candidates
              ─► detect conflicts ─► fuse evidence ─► decide ─► AuditDecision
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .reasoning import DEFAULT_POLICY, DecisionPolicy, DecisionResult, decide_lineage
from .schemas.audit import AuditDecision
from .schemas.extraction import EvidenceExtraction
from .snapshots import DEFAULT_SNAPSHOT_ROOT, LoadedSnapshot, load_snapshot

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    from .prose import LLMProseExtractor, ProseExtractionOutcome, ProseExtractionReport

__all__ = [
    "audit_snapshot",
    "to_audit_decision",
    "audit_extraction",
    "audit_repository",
    "audit_repository_with_prose",
    "extract_snapshot_prose",
    "DecisionResult",
]


def audit_extraction(
    extraction: EvidenceExtraction,
    *,
    policy: DecisionPolicy = DEFAULT_POLICY,
    extra_evidence: list | None = None,
) -> DecisionResult:
    """Run the Phase D engine on already-extracted structured evidence.

    ``extra_evidence`` lets Phase E add validated LLM prose claims to the very
    same engine; the engine itself is unchanged and remains the only decider.
    """
    evidence = [
        *extraction.declared_evidence,
        *extraction.independent_evidence,
        *(extra_evidence or []),
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
    extra_evidence: list | None = None,
) -> DecisionResult:
    """Audit a frozen snapshot entirely offline (parse -> decide)."""
    from .parsers import extract_repository_evidence  # local: keeps import cost low

    loaded = snapshot if snapshot is not None else load_snapshot(
        repository, commit, root=root
    )
    extraction = extract_repository_evidence(repository, commit, loaded.contents)
    return audit_extraction(
        extraction, policy=policy, extra_evidence=extra_evidence
    )


def audit_repository(
    repository: str,
    commit: str | None = None,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    policy: DecisionPolicy = DEFAULT_POLICY,
    extra_evidence: list | None = None,
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
    return audit_snapshot(
        repository, commit, root=root, policy=policy, extra_evidence=extra_evidence
    )


def to_audit_decision(result: DecisionResult) -> AuditDecision:
    """The public Phase D output object."""
    return result.decision


def extract_snapshot_prose(
    repository: str,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    extractor: LLMProseExtractor | None = None,
    tool: Any = None,
    sources: tuple[str, ...] = ("README.md",),
) -> list[ProseExtractionReport]:
    """Run Phase E prose extraction over a frozen snapshot.

    The model card text is fetched through the read-only LangChain snapshot
    tool, so the tool participates in the workflow instead of decorating it.
    When no extractor is configured (or the runtime is unavailable) an
    ``UNAVAILABLE`` report is returned and no evidence is fabricated.
    """
    from .prose import unavailable_report

    reports: list[ProseExtractionReport] = []  # noqa: F821 - TYPE_CHECKING alias
    try:
        from .tools import build_readme_prose_tool

        resolved_tool = tool or build_readme_prose_tool(root=root)
    except ImportError as exc:  # LangChain missing: degrade, never crash
        return [
            unavailable_report(
                source_name,
                f"LLM prose extraction unavailable: {exc}",
            )
            for source_name in sources
        ]

    for source_name in sources:
        raw = resolved_tool.invoke({"repository": repository, "source_name": source_name})
        payload = json.loads(raw if isinstance(raw, str) else raw)
        if not payload.get("found"):
            reports.append(unavailable_report(
                source_name,
                str(payload.get("reason", "artifact not found in the frozen snapshot")),
            ))
            continue
        if extractor is None:
            # Deterministic-only mode: report the state, invent nothing.
            reports.append(unavailable_report(
                source_name, "no LLM extractor configured (deterministic-only mode)"
            ))
            continue
        reports.append(extractor.extract(
            payload["text"],
            source_name=source_name,
            repository=repository,
            revision=payload.get("commit"),
        ))
    return reports


def audit_repository_with_prose(
    repository: str,
    commit: str | None = None,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    policy: DecisionPolicy = DEFAULT_POLICY,
    extractor: LLMProseExtractor | None = None,
    sources: tuple[str, ...] = ("README.md",),
    tool: Any = None,
) -> ProseExtractionOutcome:
    """Audit a frozen snapshot deterministically, then add validated LLM prose.

    Mode selection is explicit and safe: without ``extractor`` this is plain
    deterministic auditing. Phase D remains the only decision maker, so the
    outcome reports both decisions and whether the added prose changed them.
    """
    from .prose.outcome import ProseExtractionOutcome

    deterministic = audit_repository(repository, commit, root=root, policy=policy)
    commit_sha = commit or _latest_commit(root, repository)
    reports = extract_snapshot_prose(
        repository, root=root, extractor=extractor, sources=sources, tool=tool
    )
    llm_evidence = [item for report in reports for item in report.evidence]
    combined = audit_repository(
        repository, commit_sha, root=root, policy=policy, extra_evidence=llm_evidence
    )
    return ProseExtractionOutcome(
        report=_merge_reports(reports),
        decision=combined.decision,
        deterministic_decision=deterministic.decision.decision.value,
        decision_changed=(
            combined.decision.decision is not deterministic.decision.decision
        ),
    )


def _latest_commit(root: Path, repository: str) -> str:
    directory = Path(root) / repository.replace("/", "__")
    commits = sorted(
        path.name for path in directory.iterdir()
        if (path / "manifest.json").is_file()
    )
    if not commits:
        raise FileNotFoundError(f"no frozen snapshot for {repository!r} under {root}")
    return commits[-1]


def _merge_reports(reports: list[ProseExtractionReport]) -> ProseExtractionReport:  # noqa: F821
    """Combine per-source reports into one (deterministic, order-stable)."""
    from .prose import ProseExtractionReport, unavailable_report

    if len(reports) == 1:
        return reports[0]
    if not reports:  # pragma: no cover - defensive
        return unavailable_report("none", "no prose sources configured")
    first = reports[0]
    return ProseExtractionReport(
        status=min((r.status for r in reports), key=lambda s: s.value),
        source_name=", ".join(r.source_name for r in reports),
        prompt_version=first.prompt_version,
        prompt_digest=first.prompt_digest,
        model=first.model,
        reason=first.reason,
        chunks_available=sum(r.chunks_available for r in reports),
        chunks_processed=sum(r.chunks_processed for r in reports),
        claims_reported=sum(r.claims_reported for r in reports),
        claims_accepted=sum(r.claims_accepted for r in reports),
        no_claim_chunks=sum(r.no_claim_chunks for r in reports),
        failures=[f for r in reports for f in r.failures],
        evidence=[i for r in reports for i in r.evidence],
        elapsed_seconds=(
            round(sum(r.elapsed_seconds or 0.0 for r in reports), 4)
        ),
    )
