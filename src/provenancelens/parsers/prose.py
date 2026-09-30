"""Rule-based prose claim extraction (deterministic fallback, no LLM).

Patterns only fire on explicit lineage phrasing ("fine-tuned from X", ...).
Text that merely *mentions* another model produces no claim (NO_CLAIM).
Candidate parents must pass the conservative model-ID check — arbitrary
``foo/bar`` strings (file paths, local paths) are rejected.
"""

from __future__ import annotations

import re

from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
    is_plausible_model_id,
)
from ..schemas.lineage import Relation

# Canonical relation -> pattern. Order matters for deterministic output and is
# relied upon by the legacy Phase 2 compatibility layer.
PROSE_PATTERNS: dict[Relation, str] = {
    Relation.FINETUNE: r"(?:fine[- ]?tuned|trained)\s+(?:from|on top of)\s+([\w.-]+/[\w.-]+)",
    Relation.ADAPTER: r"adapter\s+(?:for|based on)\s+([\w.-]+/[\w.-]+)",
    Relation.MERGE: r"merg(?:e|ed)\s+(?:from|of)\s+([\w.-]+/[\w.-]+)",
    Relation.QUANTIZED: r"quantiz(?:ed|ation)\s+(?:from|of)\s+([\w.-]+/[\w.-]+)",
}


def extract_prose_claims(
    text: object,
    *,
    source_type: SourceType = SourceType.README,
    source_name: str = "README.md",
    repository: str | None = None,
    revision: str | None = None,
) -> list[EvidenceItem]:
    """Extract explicit direct-parent claims from prose.

    Returns an empty list when no explicit claim exists (NO_CLAIM) or when
    the input is missing/malformed — never raises on bad input.
    """
    if not isinstance(text, str) or not text:
        return []

    items: list[EvidenceItem] = []
    seen: set[tuple[str, Relation]] = set()
    for relation, pattern in PROSE_PATTERNS.items():
        for match in re.finditer(pattern, text, flags=re.I):
            raw_parent = match.group(1)
            parent = raw_parent.rstrip(".")
            if not is_plausible_model_id(parent):
                continue
            key = (parent, relation)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                EvidenceItem(
                    source_type=source_type,
                    source_name=source_name,
                    repository=repository,
                    revision=revision,
                    role=EvidenceRole.INDEPENDENT,
                    candidate_parent=parent,
                    relation=relation,
                    raw_value=raw_parent,
                    evidence_span=match.group(0),
                    extraction_method=ExtractionMethod.RULE_BASED,
                    explicitness=Explicitness.EXPLICIT,
                    reliability=Reliability.MEDIUM,
                    note="rule-based prose pattern match",
                )
            )
    return items
