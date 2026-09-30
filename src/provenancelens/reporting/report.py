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


LLM_EXTRACTED_LABEL = "[LLM_EXTRACTED]"
DETERMINISTIC_LABEL = "[DETERMINISTIC]"


def _evidence_line(item: Any) -> str:
    relation = item.relation.value if item.relation else "unspecified"
    line = (
        f"{item.source_type.value}:{item.source_name or '-'} "
        f"key_path={item.key_path or '-'} "
        f"raw={item.raw_value or item.candidate_parent or '-'} "
        f"relation={relation} reliability={item.reliability.value} "
        f"explicitness={item.explicitness.value}"
    )
    if item.evidence_span:
        line += f' span="{item.evidence_span}"'
    return "    - " + line


def _evidence_section(items: Sequence[Any], *, llm_report: Any = None) -> str:
    """Render evidence grouped by extraction method, as an audit reader needs."""
    if not items:
        return "    none"
    deterministic = [i for i in items if i.extraction_method.value == "deterministic"]
    llm = [i for i in items if i.extraction_method.value == "llm"]
    if not llm:
        return "\n".join(_evidence_line(i) for i in items)
    lines: list[str] = []
    if deterministic:
        lines.append(f"    {DETERMINISTIC_LABEL}")
        lines.extend(_evidence_line(i) for i in deterministic)
    report = getattr(llm_report, "report", llm_report)
    prompt_version = getattr(report, "prompt_version", None)
    lines.append(
        f"    {LLM_EXTRACTED_LABEL}"
        + (f" prompt version: {prompt_version}" if prompt_version else "")
    )
    lines.extend(_evidence_line(i) for i in llm)
    return "\n".join(lines)


def format_audit_decision(decision: BaseModel, *, prose_report: Any = None) -> str:
    """Render a Phase D AuditDecision, optionally annotated with LLM provenance.

    ``prose_report`` is a :class:`ProseExtractionReport` (or a
    :class:`ProseExtractionOutcome`). It never changes the decision, it only
    makes the evidence provenance visible: which items came from deterministic
    parsers, which were LLM-extracted from prose, and why an LLM run was
    unavailable. No chain-of-thought is ever displayed.
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
        return _evidence_section(items, llm_report=prose_report)

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
        *_prose_status_lines(prose_report),
    ])


def _prose_status_lines(prose_report: Any) -> list[str]:
    """Concise LLM status block (never chain-of-thought, never a crash)."""
    if prose_report is None:
        return []
    report = getattr(prose_report, "report", prose_report)
    summary = getattr(report, "summary", None)
    if not callable(summary):  # pragma: no cover - defensive
        return []
    detail = summary()
    lines = ["", f"LLM PROSE EXTRACTION: {detail}"]
    version = getattr(report, "prompt_version", None)
    digest = getattr(report, "prompt_digest", None)
    if version:
        provenance = f"prompt version: {version}"
        if digest:
            provenance += f" (digest {str(digest)[:12]})"
        if getattr(report, "model", None):
            provenance += f", model {report.model}"
        lines.append(f"    {provenance}")
    evidence = getattr(report, "evidence", []) or []
    if evidence:
        lines.append("    validated claims:")
        for item in evidence:
            span = f' "{item.evidence_span}"' if item.evidence_span else ""
            lines.append(
                f"    - {item.candidate_parent}"
                f"[{item.relation.value if item.relation else 'unspecified'}]"
                f" ({item.claim_status if hasattr(item, 'claim_status') else ''}){span}"
            )
    failures = getattr(report, "failures", []) or []
    if failures:
        lines.append("    rejected claims (not used as evidence):")
        for failure in failures:
            lines.append(
                f"    - {failure.code.value} (chunk {failure.chunk_index}): {failure.detail}"
            )
    return lines
