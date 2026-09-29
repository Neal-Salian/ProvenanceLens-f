"""Deterministic evidence extraction (no LLM involved)."""

from .adapter import extract_adapter_evidence
from .bundle import extract_declared, extract_independent_evidence, extract_repository_evidence
from .configs import LINEAGE_CONFIG_KEYS, extract_config_evidence
from .frontmatter import extract_declared_from_readme, split_front_matter
from .merge import extract_merge_evidence
from .metadata import extract_declared_metadata
from .prose import PROSE_PATTERNS, extract_prose_claims
from .training import TRAINING_LINEAGE_KEYS, extract_training_evidence

__all__ = [
    "LINEAGE_CONFIG_KEYS",
    "PROSE_PATTERNS",
    "TRAINING_LINEAGE_KEYS",
    "extract_adapter_evidence",
    "extract_config_evidence",
    "extract_declared",
    "extract_declared_metadata",
    "extract_declared_from_readme",
    "extract_independent_evidence",
    "extract_merge_evidence",
    "extract_prose_claims",
    "extract_repository_evidence",
    "extract_training_evidence",
    "split_front_matter",
]
