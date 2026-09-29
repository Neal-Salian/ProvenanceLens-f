"""Human-readable and machine-readable rendering of results."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel


def format_results_table(results: Sequence[Mapping[str, Any]]) -> str:
    """Render legacy Phase 2 result dicts as the notebook's summary table."""
    lines = [
        f"{'MODEL':38} {'ACTION':9} {'PARENT':32} CONFIDENCE",
        "-" * 94,
    ]
    for result in results:
        parent = result.get("proposed_parent") or "-"
        lines.append(
            f"{result['model_id']:38} {result['action']:9} {parent:32} {result['confidence']:.2f}"
        )
    return "\n".join(lines)


def to_json(data: Any, *, indent: int = 2) -> str:
    """Serialize a dict/list or Pydantic model as JSON text."""
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    return json.dumps(data, indent=indent, ensure_ascii=False)
