"""LCEL chains (LangChain, optional)."""

from __future__ import annotations

from typing import Any

from ._availability import LANGCHAIN_AVAILABLE


def build_legacy_audit_chain() -> Any | None:
    """Phase 2 LCEL composition: extract evidence -> decide lineage.

    Returns None when ``langchain-core`` is unavailable; callers should fall
    back to :func:`provenancelens.reasoning.legacy.audit`, which is equivalent.
    """
    if not LANGCHAIN_AVAILABLE:
        return None
    from langchain_core.runnables import RunnableLambda

    from ..reasoning.legacy import decide_lineage, extract_evidence

    return RunnableLambda(extract_evidence) | RunnableLambda(decide_lineage)
