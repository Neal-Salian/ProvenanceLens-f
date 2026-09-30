"""Conservative model-identifier resolution (no search, no guessing)."""

from .resolver import (
    ModelResolution,
    ResolutionStatus,
    merge_sources_to_one,
    normalize_identifier,
    resolve_identifier,
    resolve_identifiers,
)

__all__ = [
    "ModelResolution",
    "ResolutionStatus",
    "merge_sources_to_one",
    "normalize_identifier",
    "resolve_identifier",
    "resolve_identifiers",
]
