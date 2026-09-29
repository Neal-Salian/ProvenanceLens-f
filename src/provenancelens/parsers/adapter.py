"""PEFT ``adapter_config.json`` -> very high reliability INDEPENDENT evidence.

``base_model_name_or_path`` names the adapter's direct base model, making it
one of the strongest structured signals available. Local paths and other
non-public values are rejected as parent IDs, but the raw value is
preserved for traceability.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
    is_plausible_model_id,
)
from ..schemas.extraction import ExtractionIssue
from ..schemas.lineage import Relation
from .structured import load_json_text

ADAPTER_PARENT_KEY = "base_model_name_or_path"


def extract_adapter_evidence(
    text: object,
    *,
    source_name: str = "adapter_config.json",
    repository: str | None = None,
    revision: str | None = None,
) -> tuple[list[EvidenceItem], list[ExtractionIssue]]:
    """Extract the adapter's base model from ``adapter_config.json`` text."""
    data, issue = load_json_text(text, source_name=source_name)
    if issue:
        return [], [issue]
    if not isinstance(data, Mapping):
        if data is None:
            return [], [ExtractionIssue(
                source_name=source_name, message="empty adapter config",
                severity="warning",
            )]
        return [], [ExtractionIssue(
            source_name=source_name,
            message=f"adapter config root is not an object (got {type(data).__name__})",
            severity="error",
        )]

    raw = data.get(ADAPTER_PARENT_KEY)
    if raw is None:
        return [], []  # no parent field: nothing to extract, not an error
    if not isinstance(raw, str) or not raw.strip():
        return [], [ExtractionIssue(
            source_name=source_name,
            message=f"'{ADAPTER_PARENT_KEY}' is not a string value",
            severity="warning",
        )]

    value = raw.strip()
    common = dict(
        source_type=SourceType.ADAPTER_CONFIG,
        source_name=source_name,
        repository=repository,
        revision=revision,
        role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        explicitness=Explicitness.EXPLICIT,
        reliability=Reliability.VERY_HIGH,
        key_path=ADAPTER_PARENT_KEY,
    )
    if is_plausible_model_id(value):
        item = EvidenceItem(
            **common,
            candidate_parent=value,
            relation=Relation.ADAPTER,
            raw_value=raw,
            evidence_span=f'"{ADAPTER_PARENT_KEY}": "{raw}"',
            note="adapter_config base model",
        )
    else:
        # Rejected as a public parent ID, but the raw value is preserved.
        item = EvidenceItem(
            **common,
            candidate_parent=None,
            relation=Relation.ADAPTER,
            raw_value=raw,
            evidence_span=f'"{ADAPTER_PARENT_KEY}": "{raw}"',
            note=(
                "rejected: not a plausible public Hugging Face model id "
                "(local path or non-public value); raw value preserved"
            ),
        )
    return [item], []
