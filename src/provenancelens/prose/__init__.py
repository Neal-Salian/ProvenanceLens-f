"""Phase E: LLM-last prose lineage claim extraction.

Structured repository data is parsed deterministically (Phase C); only
genuinely unstructured prose reaches a local, open-weight chat model through
LangChain. The model extracts claims, never decisions: every claim is
validated against the source text and converted into ordinary Phase 3
:class:`EvidenceItem` objects that the existing Phase D reasoning engine
consumes.
"""

from .chunking import (
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_MAX_CHUNKS,
    ProseChunk,
    chunk_prose,
    strip_front_matter,
    strip_non_prose,
)
from .extractor import LLMProseExtractor, LLMUnavailable, unavailable_report
from .prompt import (
    EXTRACTION_INSTRUCTIONS,
    PROSE_BLOCK_CLOSE,
    PROSE_BLOCK_OPEN,
    PROSE_EXTRACTION_PROMPT,
    PROSE_EXTRACTION_PROMPT_VERSION,
    prompt_digest,
    render_prose_block,
)
from .runtime import (
    DEFAULT_LLM_MODEL,
    LLMAvailability,
    build_default_chat_model,
    llm_availability,
)
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
)
from .selection import select_provenance_chunks
from .validation import (
    LINEAGE_CUES,
    INJECTION_PATTERNS,
    ClaimValidation,
    looks_like_injection,
    span_occurs_in,
    states_lineage,
    validate_claim,
)

__all__ = [
    "DEFAULT_LLM_MODEL",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_MAX_CHUNK_CHARS",
    "EXTRACTION_INSTRUCTIONS",
    "INJECTION_PATTERNS",
    "LINEAGE_CUES",
    "LLM_PROSE_RELIABILITY",
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
    "ProseExtractionReport",
    "ProseExtractionStatus",
    "ProseFailure",
    "ProseFailureCode",
    "ProseLineageClaim",
    "RationaleCode",
    "build_default_chat_model",
    "build_llm_evidence_item",
    "llm_evidence_reliability",
    "looks_like_injection",
    "states_lineage",
    "chunk_prose",
    "llm_availability",
    "prompt_digest",
    "render_prose_block",
    "select_provenance_chunks",
    "span_occurs_in",
    "strip_front_matter",
    "strip_non_prose",
    "unavailable_report",
    "validate_claim",
]
