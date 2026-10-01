"""PromptTemplates for lineage claim extraction (LangChain, optional)."""

from __future__ import annotations

from typing import Any

from ._availability import LANGCHAIN_AVAILABLE

# Phase 2 prompt, preserved verbatim.
CLAIM_EXTRACTION_TEMPLATE = (
    "Extract only explicit direct-parent model claims from the text below. "
    "Return JSON with parent_model, relationship, quote and source. "
    "Do not guess.\n\nSOURCE: {source}\nTEXT: {text}"
)


def build_claim_prompt() -> Any | None:
    """Return the claim-extraction PromptTemplate, or None without LangChain."""
    if not LANGCHAIN_AVAILABLE:
        return None
    from langchain_core.prompts import PromptTemplate

    return PromptTemplate.from_template(CLAIM_EXTRACTION_TEMPLATE)
