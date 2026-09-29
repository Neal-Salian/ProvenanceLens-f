"""LangChain-specific integration (optional dependency).

Everything here degrades gracefully: if ``langchain-core`` is not installed,
the builders return ``None`` and the deterministic core package keeps working.
No paid LLM API is required anywhere in the project.
"""

from ._availability import LANGCHAIN_AVAILABLE
from .chains import build_legacy_audit_chain
from .output_parsers import build_decision_parser
from .prompts import build_claim_prompt

__all__ = [
    "LANGCHAIN_AVAILABLE",
    "build_claim_prompt",
    "build_decision_parser",
    "build_legacy_audit_chain",
]
