"""Deterministic structured-config lineage extraction.

Config fields can identify a *candidate parent* but generally do not
establish the relationship type — so extracted evidence carries
``relation=None`` and never inherits the relation declared elsewhere in the
repository metadata.
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

# Fields that reasonably indicate lineage in config/training JSON files.
LINEAGE_CONFIG_KEYS: tuple[str, ...] = (
    "_name_or_path",
    "model_name_or_path",
    "base_model",
    "pretrained_model_name_or_path",
)


def extract_config_evidence(
    config: object,
    *,
    source_name: str = "config.json",
    source_type: SourceType = SourceType.CONFIG,
    repository: str | None = None,
    revision: str | None = None,
    reliability: Reliability = Reliability.MEDIUM,
) -> list[EvidenceItem]:
    """Extract candidate-parent evidence from a parsed config mapping.

    Returns an empty list for missing/malformed/non-model values — never
    raises on bad input. The relationship type is intentionally left unset:
    a config field names a model, it does not state the relationship.
    """
    if not isinstance(config, Mapping):
        return []

    items: list[EvidenceItem] = []
    seen: set[str] = set()
    for key in LINEAGE_CONFIG_KEYS:
        if key not in config:
            continue
        value = config[key]
        if not is_plausible_model_id(value):
            continue
        if value in seen:
            continue
        seen.add(value)
        items.append(
            EvidenceItem(
                source_type=source_type,
                source_name=source_name,
                repository=repository,
                revision=revision,
                role=EvidenceRole.INDEPENDENT,
                candidate_parent=value,
                relation=None,
                raw_value=str(value),
                extraction_method=ExtractionMethod.DETERMINISTIC,
                explicitness=Explicitness.EXPLICIT,
                reliability=reliability,
                note=f"config field '{key}' names a candidate parent; relation not established by this source",
            )
        )
    return items
