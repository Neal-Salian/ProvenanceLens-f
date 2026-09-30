"""Phase E: LLM-last prose lineage claim extraction.

Structured repository data is parsed deterministically (Phase C); only
genuinely unstructured prose reaches a local, open-weight chat model through
LangChain. The model extracts claims, never decisions: every claim is
validated against the source text and converted into ordinary Phase 3
:class:`EvidenceItem` objects that the existing Phase D reasoning engine
consumes.

Import policy: the schema, chunking, selection, validation, and outcome types
have no LangChain dependency, so "LLM unavailable" can always be *represented*
structurally. The LangChain-dependent pieces (prompt, extractor) are imported
defensively; if they are missing, the package still imports and
:data:`LLM_STACK_AVAILABLE` reports ``False``.
"""

from __future__ import annotations

from .chunking import (
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_MAX_CHUNKS,
    ProseChunk,
    chunk_prose,
    strip_front_matter,
    strip_non_prose,
)
from .outcome import ProseExtractionOutcome
from .schema import (
    LLM_PROSE_RELIABILITY,
    ClaimStatus,
    ProseClaimSet,
    ProseExtractionReport,
    ProseExtractionStatus,
    ProseFailure,
    ProseFailureCode,
    ProseLineageClaim,
    RationaleCode,
    build_llm_evidence_item,
    llm_evidence_reliability,
    unavailable_report,
)
from .selection import select_provenance_chunks
from .validation import (
    INJECTION_PATTERNS,
    LINEAGE_CUES,
    ClaimValidation,
    looks_like_injection,
    span_occurs_in,
    states_lineage,
    validate_claim,
)

#: Availability of the optional LangChain-based extraction stack.
LLM_STACK_AVAILABLE = True
LLM_STACK_ERROR: str | None = None

try:  # LangChain is optional: the deterministic core must never need it.
    from ..llm_runtime import (
        DEFAULT_LLM_MODEL,
        LLMAvailability,
        LLMUnavailable,
        build_default_chat_model,
        llm_availability,
    )
    from .extractor import LLMProseExtractor
    from .prompt import (
        EXTRACTION_INSTRUCTIONS,
        PROSE_BLOCK_CLOSE,
        PROSE_BLOCK_OPEN,
        PROSE_EXTRACTION_PROMPT,
        PROSE_EXTRACTION_PROMPT_VERSION,
        prompt_digest,
        render_prose_block,
    )
except ImportError as exc:  # pragma: no cover - depends on environment
    LLM_STACK_AVAILABLE = False
    LLM_STACK_ERROR = f"{type(exc).__name__}: {exc}"

_LANGCHAIN_ONLY = (
    "DEFAULT_LLM_MODEL", "EXTRACTION_INSTRUCTIONS", "LLMAvailability",
    "LLMProseExtractor", "LLMUnavailable", "PROSE_BLOCK_CLOSE",
    "PROSE_BLOCK_OPEN", "PROSE_EXTRACTION_PROMPT",
    "PROSE_EXTRACTION_PROMPT_VERSION", "build_default_chat_model",
    "llm_availability", "prompt_digest", "render_prose_block",
    "unavailable_report",
)


def __getattr__(name: str):
    """Give an explicit, actionable error for LangChain-only names."""
    if name in _LANGCHAIN_ONLY:
        raise ImportError(
            f"provenancelens.prose.{name} requires the optional LangChain extra "
            f"(pip install 'provenancelens[llm]'); import error was: {LLM_STACK_ERROR}"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DEFAULT_LLM_MODEL",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_MAX_CHUNK_CHARS",
    "EXTRACTION_INSTRUCTIONS",
    "INJECTION_PATTERNS",
    "LINEAGE_CUES",
    "LLM_PROSE_RELIABILITY",
    "LLM_STACK_AVAILABLE",
    "LLM_STACK_ERROR",
    "PROSE_BLOCK_CLOSE",
    "PROSE_BLOCK_OPEN",
    "PROSE_EXTRACTION_PROMPT",
    "PROSE_EXTRACTION_PROMPT_VERSION",
    "ClaimStatus",
    "ClaimValidation",
    "LLMAvailability",
    "LLMProseExtractor",
    "LLMUnavailable",
    "ProseChunk",
    "ProseClaimSet",
    "ProseExtractionOutcome",
    "ProseExtractionReport",
    "ProseExtractionStatus",
    "ProseFailure",
    "ProseFailureCode",
    "ProseLineageClaim",
    "RationaleCode",
    "build_default_chat_model",
    "build_llm_evidence_item",
    "chunk_prose",
    "llm_availability",
    "llm_evidence_reliability",
    "looks_like_injection",
    "prompt_digest",
    "render_prose_block",
    "select_provenance_chunks",
    "span_occurs_in",
    "states_lineage",
    "strip_front_matter",
    "strip_non_prose",
    "unavailable_report",
    "validate_claim",
]
