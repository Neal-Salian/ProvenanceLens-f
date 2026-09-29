"""Structured output parsers (LangChain, optional)."""

from __future__ import annotations

from typing import Any

from ._availability import LANGCHAIN_AVAILABLE
from ..reasoning.legacy import LegacyLineageDecision


def build_decision_parser() -> Any | None:
    """Return a JsonOutputParser over the Phase 2 decision schema, or None."""
    if not LANGCHAIN_AVAILABLE:
        return None
    from langchain_core.output_parsers import JsonOutputParser

    return JsonOutputParser(pydantic_object=LegacyLineageDecision)
