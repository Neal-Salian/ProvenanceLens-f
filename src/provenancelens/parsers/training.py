"""Training configuration files -> INDEPENDENT candidate-parent evidence.

Only an explicit allowlist of lineage-indicating keys is read, at any JSON/
YAML depth, and each claim retains its exact key path and raw value. Fields
are never inferred from arbitrary strings, and no transformation *relation*
is claimed: a training config names a model but does not state the
relationship (relation stays ``None``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

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
from .structured import is_structured_data, load_json_text, load_yaml_text

# Explicit lineage-indicating keys (lower-cased comparison).
TRAINING_LINEAGE_KEYS: frozenset[str] = frozenset({
    "model_name_or_path",
    "base_model",
    "base_model_name_or_path",
    "pretrained_model_name_or_path",
})

_MAX_DEPTH = 12


def extract_training_evidence(
    text: object,
    *,
    source_name: str,
    source_type: SourceType = SourceType.TRAINING_CONFIG,
    fmt: Literal["json", "yaml"] = "json",
    repository: str | None = None,
    revision: str | None = None,
) -> tuple[list[EvidenceItem], list[ExtractionIssue]]:
    """Extract allow-listed model fields from a training config's text."""
    if fmt == "yaml":
        data, issue = load_yaml_text(text, source_name=source_name)
    else:
        data, issue = load_json_text(text, source_name=source_name)
    if issue:
        return [], [issue]
    if data is None:
        return [], [ExtractionIssue(
            source_name=source_name, message="no structured content",
            severity="warning",
        )]
    if not is_structured_data(data):
        return [], [ExtractionIssue(
            source_name=source_name,
            message=f"unexpected root type {type(data).__name__}",
            severity="error",
        )]

    items: list[EvidenceItem] = []
    issues: list[ExtractionIssue] = []
    truncated = [False]
    _walk(
        data,
        path="",
        depth=0,
        source_name=source_name,
        source_type=source_type,
        repository=repository,
        revision=revision,
        items=items,
        issues=issues,
        truncated=truncated,
    )
    if truncated[0]:
        issues.append(ExtractionIssue(
            source_name=source_name,
            message=f"structure deeper than {_MAX_DEPTH} levels was not scanned",
            severity="warning",
        ))
    return items, issues


def _walk(
    node: object,
    *,
    path: str,
    depth: int,
    source_name: str,
    source_type: SourceType,
    repository: str | None,
    revision: str | None,
    items: list[EvidenceItem],
    issues: list[ExtractionIssue],
    truncated: list[bool],
) -> None:
    if depth > _MAX_DEPTH:
        truncated[0] = True
        return
    if isinstance(node, Mapping):
        for key, value in node.items():
            if not isinstance(key, str):
                continue
            key_path = f"{path}{key}"
            if key.lower() in TRAINING_LINEAGE_KEYS:
                _handle_value(
                    value,
                    key_path=key_path,
                    source_name=source_name,
                    source_type=source_type,
                    repository=repository,
                    revision=revision,
                    items=items,
                    issues=issues,
                )
            _walk(
                value,
                path=f"{key_path}.",
                depth=depth + 1,
                source_name=source_name,
                source_type=source_type,
                repository=repository,
                revision=revision,
                items=items,
                issues=issues,
                truncated=truncated,
            )
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(
                value,
                path=f"{path}[{index}].",
                depth=depth + 1,
                source_name=source_name,
                source_type=source_type,
                repository=repository,
                revision=revision,
                items=items,
                issues=issues,
                truncated=truncated,
            )


def _handle_value(
    value: object,
    *,
    key_path: str,
    source_name: str,
    source_type: SourceType,
    repository: str | None,
    revision: str | None,
    items: list[EvidenceItem],
    issues: list[ExtractionIssue],
) -> None:
    if isinstance(value, str):
        candidate = value.strip()
        if is_plausible_model_id(candidate):
            items.append(EvidenceItem(
                source_type=source_type,
                source_name=source_name,
                repository=repository,
                revision=revision,
                role=EvidenceRole.INDEPENDENT,
                candidate_parent=candidate,
                relation=None,
                raw_value=value,
                key_path=key_path,
                evidence_span=f"{key_path} = {value!r}",
                extraction_method=ExtractionMethod.DETERMINISTIC,
                explicitness=Explicitness.EXPLICIT,
                reliability=Reliability.MEDIUM,
                note="training config names a candidate parent; relation not established by this source",
            ))
        else:
            kind = (
                "local/checkpoint path" if ("/" in candidate or candidate.startswith("."))
                else "value without a namespace"
            )
            issues.append(ExtractionIssue(
                source_name=source_name,
                message=f"rejected {kind} at '{key_path}': {value!r}",
                severity="warning",
            ))
    elif isinstance(value, list):
        for index, entry in enumerate(value):
            _handle_value(
                entry,
                key_path=f"{key_path}[{index}]",
                source_name=source_name,
                source_type=source_type,
                repository=repository,
                revision=revision,
                items=items,
                issues=issues,
            )
    else:
        issues.append(ExtractionIssue(
            source_name=source_name,
            message=f"unsupported value type for '{key_path}' ({type(value).__name__})",
            severity="warning",
        ))
