"""LEGACY Phase 2 decision engine — preserved verbatim for regression tests.

This module intentionally reproduces the original notebook behavior,
including its known methodological flaws (documented in CURRENT_STATE.md):

- ``config._name_or_path`` inherits the *declared* relation (circular),
- any string containing ``/`` is accepted as a model ID,
- at least 2 distinct sources are required regardless of reliability,
- ``confidence`` is an ad-hoc heuristic presented like a probability,
- evidence is untraceable strings, not structured objects,
- tool errors do not affect the decision when other claims exist.

Do NOT extend this module. New reasoning logic belongs in the Phase 3
reasoning layer; new extraction belongs in :mod:`provenancelens.parsers`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..parsers.prose import PROSE_PATTERNS
from ..schemas.lineage import Relation

# Legacy Phase 2 relation labels, kept exactly as the notebook produced them.
LEGACY_RELATION_LABELS: dict[Relation, str] = {
    Relation.FINETUNE: "fine-tune",
    Relation.ADAPTER: "adapter",
    Relation.MERGE: "merge",
    Relation.QUANTIZED: "quantized",
}

# Legacy-labeled patterns (same regexes and iteration order as Phase 2).
RELATION_PATTERNS: dict[str, str] = {
    LEGACY_RELATION_LABELS[relation]: pattern
    for relation, pattern in PROSE_PATTERNS.items()
}


class LegacyLineageDecision(BaseModel):
    """Phase 2 output shape (notebook ``LineageDecision``)."""

    model_id: str
    action: Literal["KEEP", "ADD", "REPLACE", "ABSTAIN"]
    proposed_parent: str | None = None
    relationship: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    rationale: str


def extract_evidence(bundle: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 extraction: declared + config + README regex claims."""
    claims: list[dict[str, Any]] = []
    declared = bundle.get("metadata", {}).get("base_model")
    relation = bundle.get("metadata", {}).get("base_model_relation")
    if declared:
        claims.append({"parent": declared, "relation": relation, "source": "metadata", "weight": 0})
    config_parent = bundle.get("config", {}).get("_name_or_path")
    if config_parent and "/" in config_parent:
        claims.append({"parent": config_parent, "relation": relation or "fine-tune", "source": "config.json", "weight": 3})
    text = bundle.get("readme", "")
    for legacy_label, pattern in RELATION_PATTERNS.items():
        match = re.search(pattern, text, flags=re.I)
        if match:
            claims.append({"parent": match.group(1).rstrip("."), "relation": legacy_label, "source": "README", "weight": 2})
    return {**bundle, "claims": claims}


def decide_lineage(item: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 weighted scoring + KEEP/ADD/REPLACE/ABSTAIN decision."""
    declared = item.get("metadata", {}).get("base_model")
    errors = item.get("tool_errors", [])
    independent = [c for c in item["claims"] if c["source"] != "metadata"]
    scores: dict[str, int] = defaultdict(int)
    sources: dict[str, list[str]] = defaultdict(list)
    relations: dict[str, list[Any]] = defaultdict(list)
    for claim in independent:
        scores[claim["parent"]] += claim["weight"]
        sources[claim["parent"]].append(claim["source"])
        relations[claim["parent"]].append(claim["relation"])

    if not scores:
        return {
            "model_id": item["model_id"], "action": "ABSTAIN", "proposed_parent": None,
            "relationship": None, "confidence": 0.10, "supporting_evidence": [],
            "conflicting_evidence": errors or ["No independent parent evidence found"],
            "rationale": "Evidence is unavailable or insufficient for a safe repair."
        }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    winner, top_score = ranked[0]
    runner_score = ranked[1][1] if len(ranked) > 1 else 0
    conflict = len(ranked) > 1
    evidence_count = len(set(sources[winner]))

    if conflict and top_score - runner_score < 2:
        action = "ABSTAIN"
        confidence = 0.45
        parent = None
    elif evidence_count < 2:
        action = "ABSTAIN"
        confidence = 0.55
        parent = None
    else:
        parent = winner
        action = "KEEP" if declared == winner else ("ADD" if not declared else "REPLACE")
        confidence = min(0.95, 0.65 + 0.05 * top_score)

    supporting = [f"{c['source']}: {c['parent']} ({c['relation']})" for c in independent if c["parent"] == winner]
    conflicting = [f"{c['source']}: {c['parent']}" for c in independent if c["parent"] != winner]
    if declared and declared != winner:
        conflicting.append(f"declared metadata: {declared}")

    return {
        "model_id": item["model_id"], "action": action, "proposed_parent": parent,
        "relationship": relations[winner][0] if parent else None,
        "confidence": round(confidence, 2), "supporting_evidence": supporting,
        "conflicting_evidence": conflicting + errors,
        "rationale": (
            "The strongest parent is independently supported by configuration and documentation."
            if action != "ABSTAIN" else
            "The evidence is conflicting or does not meet the minimum support threshold."
        ),
    }


def audit(bundle: dict[str, Any]) -> dict[str, Any]:
    """Run the full Phase 2 pipeline on one evidence bundle."""
    return decide_lineage(extract_evidence(bundle))
