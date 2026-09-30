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


def format_audit_decision(decision: BaseModel) -> str:
    """Render a Phase D :class:`AuditDecision` as a human-readable audit record.

    Structured and deterministic (no chain-of-thought): every section states a
    fact about the evidence or the action taken.
    """
    lineage = decision.proposed_lineage
    proposed = (
        "\n".join(
            f"    - {entry.parent} [{entry.relation.value if entry.relation else 'relation unspecified'}]"
            for entry in lineage.entries
        )
        or "none"
    )
    current = decision.current_lineage
    declared_parts = list(current.base_models) or ["none"]
    if current.relation_raw:
        declared_parts.append(f"(declared relation: {current.relation_raw!r})")
    elif current.relation:
        declared_parts.append(f"(declared relation: {current.relation.value})")
    else:
        declared_parts.append("(no declared relation)")

    def _items(items) -> str:
        if not items:
            return "    none"
        return "\n".join(
            "    - "
            f"{item.source_type.value}:{item.source_name or '-'}"
            f" key_path={item.key_path or '-'}"
            f" raw={item.raw_value or item.candidate_parent or '-'}"
            f" relation={item.relation.value if item.relation else 'unspecified'}"
            f" reliability={item.reliability.value}"
            f" explicitness={item.explicitness.value}"
            for item in items
        )

    if decision.conflicts:
        conflicts = "\n".join(
            f"    - [{c.kind.value}] {c.description}" for c in decision.conflicts
        )
    else:
        conflicts = "    none"

    patch = decision.recommended_patch
    if patch is None:
        patch_text = "none"
    else:
        patch_parts = []
        if patch.new_base_model:
            patch_parts.append(f"base_model: {patch.old_base_model!r} -> {patch.new_base_model!r}")
        if patch.new_relation:
            patch_parts.append(
                f"base_model_relation: {patch.old_relation_raw!r} -> {patch.new_relation.value!r}"
            )
        patch_text = "\n    ".join(patch_parts)

    return "\n".join([
        "PROVENANCELENS AUDIT (Phase D)",
        "=" * 72,
        f"TARGET              : {decision.model_id}",
        f"CURRENT LINEAGE     : {' '.join(declared_parts)}",
        f"DECISION            : {decision.decision.value}",
        f"PROPOSED LINEAGE    :\n{proposed}",
        f"SUPPORT SCORE       : {decision.support_score:.2f} "
        "(heuristic evidence strength, NOT a probability)",
        f"SUPPORTING EVIDENCE :\n{_items(decision.supporting_evidence)}",
        f"CONTRADICTORY EVID. :\n{_items(decision.contradictory_evidence)}",
        f"CONFLICTS           :\n{conflicts}",
        f"REASONING SUMMARY   : {decision.reasoning_summary}",
        f"SUGGESTED PATCH     :\n    {patch_text}",
    ])
