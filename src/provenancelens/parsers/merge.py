"""Merge configuration files -> INDEPENDENT merge-source evidence.

Reads only source-model fields (``models``, ``sources``, ``slices`` sources)
and top-level ``base_model``. No quantization relation is ever claimed from
config presence, filenames, or format similarity.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
from .structured import load_yaml_text


def extract_merge_evidence(
    text: object,
    *,
    source_name: str,
    repository: str | None = None,
    revision: str | None = None,
) -> tuple[list[EvidenceItem], list[ExtractionIssue]]:
    """Extract merge sources from a merge config's text (YAML or JSON)."""
    data, issue = load_yaml_text(text, source_name=source_name)
    if issue:
        return [], [issue]
    if data is None:
        return [], [ExtractionIssue(
            source_name=source_name, message="no structured content",
            severity="warning",
        )]
    if not isinstance(data, Mapping):
        return [], [ExtractionIssue(
            source_name=source_name,
            message=f"merge config root is not a mapping (got {type(data).__name__})",
            severity="error",
        )]

    issues: list[ExtractionIssue] = []
    # (raw_value, key_path, relation, note)
    candidates: list[tuple[str, str, Relation | None, str | None]] = []

    def _add(entry: object, key_path: str, relation: Relation | None, note: str | None) -> None:
        if isinstance(entry, str) and entry.strip():
            candidates.append((entry.strip(), key_path, relation, note))
        elif isinstance(entry, Mapping):
            for field in ("model", "path", "model_id"):
                value = entry.get(field)
                if isinstance(value, str) and value.strip():
                    candidates.append(
                        (value.strip(), f"{key_path}.{field}", relation, note)
                    )
                    return
            issues.append(ExtractionIssue(
                source_name=source_name,
                message=f"source entry at '{key_path}' has no model/path field",
                severity="warning",
            ))

    for list_key in ("models", "sources"):
        entries = data.get(list_key)
        if entries is None:
            continue
        if isinstance(entries, list):
            for index, entry in enumerate(entries):
                _add(entry, f"{list_key}[{index}]", Relation.MERGE, None)
        else:
            issues.append(ExtractionIssue(
                source_name=source_name,
                message=f"'{list_key}' is not a list",
                severity="warning",
            ))

    slices = data.get("slices")
    if isinstance(slices, list):
        for s_index, slice_entry in enumerate(slices):
            if isinstance(slice_entry, Mapping):
                sources = slice_entry.get("sources")
                if isinstance(sources, list):
                    for src_index, source in enumerate(sources):
                        _add(
                            source,
                            f"slices[{s_index}].sources[{src_index}]",
                            Relation.MERGE,
                            None,
                        )

    if "base_model" in data:
        _add(
            data.get("base_model"),
            "base_model",
            None,
            "MergeKit top-level base_model: algorithm-specific semantics, "
            "may reference an architecture/repair base rather than a merge source",
        )

    return _build_items(candidates, source_name=source_name,
                        repository=repository, revision=revision, issues=issues), issues


def _build_items(
    candidates: list[tuple[str, str, Relation | None, str | None]],
    *,
    source_name: str,
    repository: str | None,
    revision: str | None,
    issues: list[ExtractionIssue],
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    seen: dict[str, EvidenceItem] = {}  # parent -> item (dedupe, preserve extra locations)
    for raw_value, key_path, relation, note in candidates:
        if not is_plausible_model_id(raw_value):
            issues.append(ExtractionIssue(
                source_name=source_name,
                message=f"rejected non-public value at '{key_path}': {raw_value!r}",
                severity="warning",
            ))
            continue
        existing = seen.get(raw_value)
        if existing is not None:
            prior = existing.note or ""
            existing.note = f"{prior}; also at {key_path}".lstrip("; ").strip()
            continue
        item = EvidenceItem(
            source_type=SourceType.MERGE_CONFIG,
            source_name=source_name,
            repository=repository,
            revision=revision,
            role=EvidenceRole.INDEPENDENT,
            candidate_parent=raw_value,
            relation=relation,
            raw_value=raw_value,
            key_path=key_path,
            evidence_span=f"{key_path}: {raw_value}",
            extraction_method=ExtractionMethod.DETERMINISTIC,
            explicitness=Explicitness.EXPLICIT,
            reliability=Reliability.HIGH,
            note=note or "merge source model",
        )
        seen[raw_value] = item
        items.append(item)
    return items
