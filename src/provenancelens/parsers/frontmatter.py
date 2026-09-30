"""README / model-card YAML front matter -> DECLARED evidence.

Front matter ``base_model`` (and friends) is the *subject of the audit*. It
is extracted with role DECLARED and reliability NOT_APPLICABLE so it can
never count as independent proof of itself.
"""

from __future__ import annotations

import yaml
from collections.abc import Mapping

from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from ..schemas.extraction import ExtractionIssue
from ..schemas.lineage import DeclaredLineage

_FRONT_MATTER_OPEN = "---"


def split_front_matter(text: str) -> tuple[str, str | None]:
    """Split ``--- yaml ---`` front matter from the body.

    Returns ``(body, raw_yaml_text_or_None)``. Malformed/absent front matter
    degrades to ``(full_text, None)`` rather than raising.
    """
    if not isinstance(text, str) or not text.startswith(_FRONT_MATTER_OPEN):
        return (text if isinstance(text, str) else ""), None
    lines = text.split("\n")
    if lines[0].strip() != _FRONT_MATTER_OPEN:
        return text, None
    for index in range(1, len(lines)):
        stripped = lines[index].strip()
        if stripped in (_FRONT_MATTER_OPEN, "..."):
            raw_yaml = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return body, raw_yaml
    return text, None  # unterminated front matter


def parse_front_matter(
    raw_yaml: str, *, source_name: str
) -> tuple[dict[str, object], list[ExtractionIssue]]:
    """``safe_load`` front matter YAML into a dict; issues instead of raising."""
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        return {}, [
            ExtractionIssue(
                source_name=source_name,
                message=f"invalid front matter YAML: {exc}",
                severity="error",
            )
        ]
    if data is None:
        return {}, []
    if not isinstance(data, Mapping):
        return {}, [
            ExtractionIssue(
                source_name=source_name,
                message=f"front matter is not a mapping (got {type(data).__name__})",
                severity="error",
            )
        ]
    return dict(data), []


def extract_declared_from_readme(
    text: object,
    *,
    source_name: str = "README.md",
    repository: str | None = None,
    revision: str | None = None,
) -> tuple[DeclaredLineage, list[EvidenceItem], list[ExtractionIssue]]:
    """Extract DECLARED lineage from a model card's YAML front matter."""
    if not isinstance(text, str) or not text:
        return DeclaredLineage(), [], []
    issues: list[ExtractionIssue] = []
    body, raw_yaml = split_front_matter(text)
    if raw_yaml is None:
        if text.lstrip().startswith(_FRONT_MATTER_OPEN):
            issues.append(ExtractionIssue(
                source_name=source_name,
                message="unterminated YAML front matter",
                severity="warning",
            ))
        return DeclaredLineage(), [], issues

    metadata, parse_issues = parse_front_matter(raw_yaml, source_name=source_name)
    issues.extend(parse_issues)
    if parse_issues:
        return DeclaredLineage(), [], issues

    lineage = DeclaredLineage.from_metadata(metadata)
    if "base_model" in metadata and not lineage.base_models:
        issues.append(ExtractionIssue(
            source_name=source_name,
            message="unsupported base_model shape in front matter",
            severity="warning",
        ))
    if "base_model_relation" in metadata and lineage.relation_raw is None:
        issues.append(ExtractionIssue(
            source_name=source_name,
            message="unsupported base_model_relation shape in front matter",
            severity="warning",
        ))

    items = [
        EvidenceItem(
            source_type=SourceType.DECLARED_METADATA,
            source_name=source_name,
            repository=repository,
            revision=revision,
            role=EvidenceRole.DECLARED,
            candidate_parent=parent,
            relation=lineage.relation,
            relation_raw=lineage.relation_raw,
            raw_value=parent,
            key_path="base_model",
            extraction_method=ExtractionMethod.DETERMINISTIC,
            explicitness=Explicitness.EXPLICIT,
            reliability=Reliability.NOT_APPLICABLE,
            note="model-card front matter: subject of the audit, not independent evidence",
        )
        for parent in lineage.base_models
    ]
    _ = body  # body is prose-parsed separately by the bundle layer
    return lineage, items, issues
