"""Declared repository metadata extraction (the SUBJECT of the audit)."""

from __future__ import annotations

from collections.abc import Mapping

from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from ..schemas.lineage import DeclaredLineage


def extract_declared_metadata(
    metadata: object,
    *,
    repository: str | None = None,
    revision: str | None = None,
) -> tuple[DeclaredLineage, EvidenceItem | None]:
    """Build the declared lineage (subject) from ``base_model`` metadata.

    The returned evidence item has role ``declared`` and reliability
    ``not_applicable``: it records *what is being audited*, never what
    supports the audit.
    """
    lineage = DeclaredLineage.from_metadata(metadata if isinstance(metadata, Mapping) else None)
    if lineage.base_model is None:
        return lineage, None
    evidence = EvidenceItem(
        source_type=SourceType.DECLARED_METADATA,
        source_name="model card metadata",
        repository=repository,
        revision=revision,
        role=EvidenceRole.DECLARED,
        candidate_parent=lineage.base_model,
        relation=lineage.relation,
        relation_raw=lineage.relation_raw,
        raw_value=lineage.base_model,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        explicitness=Explicitness.EXPLICIT,
        reliability=Reliability.NOT_APPLICABLE,
        note="declared metadata: subject of the audit, not independent evidence",
    )
    return lineage, evidence
