"""Deterministic evidence extraction (no LLM involved)."""

from .bundle import extract_declared, extract_independent_evidence
from .configs import LINEAGE_CONFIG_KEYS, extract_config_evidence
from .metadata import extract_declared_metadata
from .prose import PROSE_PATTERNS, extract_prose_claims

__all__ = [
    "LINEAGE_CONFIG_KEYS",
    "PROSE_PATTERNS",
    "extract_config_evidence",
    "extract_declared",
    "extract_declared_metadata",
    "extract_independent_evidence",
    "extract_prose_claims",
]
