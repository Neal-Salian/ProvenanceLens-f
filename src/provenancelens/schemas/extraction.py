"""Deterministic extraction result for one (repository, commit) evidence set.

The extraction layer only EXTRACTS. It never decides KEEP/ADD/REPLACE/
ABSTAIN — that is Phase D reasoning over this output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .evidence import EvidenceItem
from .lineage import DeclaredLineage

EXTRACTION_SCHEMA_VERSION = 1


class ExtractionIssue(BaseModel):
    """A structural parser problem (malformed YAML, unsupported shape, ...).

    Issues are data, not exceptions: one broken artifact never discards the
    evidence extracted from the others.
    """

    model_config = ConfigDict(extra="forbid")

    source_name: str
    message: str
    severity: Literal["warning", "error"] = "warning"


class EvidenceExtraction(BaseModel):
    """Declared subject vs independent evidence + structural issues.

    Deterministic and timestamp-free so identical snapshot inputs always
    produce byte-identical ``extracted_evidence.json`` payloads.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = EXTRACTION_SCHEMA_VERSION
    repository: str
    resolved_commit_sha: str | None = None
    declared_lineage: DeclaredLineage
    declared_evidence: list[EvidenceItem] = Field(default_factory=list)
    independent_evidence: list[EvidenceItem] = Field(default_factory=list)
    issues: list[ExtractionIssue] = Field(default_factory=list)
