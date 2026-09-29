"""Safe JSON/YAML loading for untrusted repository artifacts.

Only ``json.loads`` and ``yaml.safe_load`` are used — downloaded content is
data, never code: nothing is executed, imported, or deserialized beyond
plain JSON/YAML structures.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import yaml

from ..schemas.extraction import ExtractionIssue


def load_json_text(text: object, *, source_name: str) -> tuple[Any, ExtractionIssue | None]:
    """Parse JSON text; returns (None, issue) instead of raising.

    An empty document is *absent content* (None, no issue) — malformed
    non-empty content is an error issue.
    """
    if not isinstance(text, str):
        return None, ExtractionIssue(
            source_name=source_name, message="input is not text", severity="error"
        )
    if not text.strip():
        return None, None
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, ExtractionIssue(
            source_name=source_name,
            message=f"invalid JSON: {exc}",
            severity="error",
        )


def load_yaml_text(text: object, *, source_name: str) -> tuple[Any, ExtractionIssue | None]:
    """Parse YAML text with ``safe_load``; returns (None, issue) on failure."""
    if not isinstance(text, str):
        return None, ExtractionIssue(
            source_name=source_name, message="input is not text", severity="error"
        )
    if not text.strip():
        return None, None
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as exc:
        return None, ExtractionIssue(
            source_name=source_name,
            message=f"invalid YAML: {exc}",
            severity="error",
        )


def is_structured_data(data: object) -> bool:
    """True for the mapping/list roots our structured parsers accept."""
    return isinstance(data, (Mapping, list))
