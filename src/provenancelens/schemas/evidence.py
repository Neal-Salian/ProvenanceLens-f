"""Core evidence representation.

Every decision in ProvenanceLens must remain traceable back to structured
evidence items. Declared repository metadata (the *subject* of the audit) and
independent evidence (configs, documentation, ...) are distinguished by
:class:`EvidenceRole` so the subject can never silently count as proof of
itself.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .lineage import Relation


class SourceType(str, Enum):
    """Where an evidence item comes from."""

    DECLARED_METADATA = "declared_metadata"
    README = "readme"
    CONFIG = "config"
    ADAPTER_CONFIG = "adapter_config"
    MERGE_CONFIG = "merge_config"
    TRAINING_CONFIG = "training_config"
    OTHER = "other"


class EvidenceRole(str, Enum):
    """DECLARED = subject of the audit; INDEPENDENT = external corroboration.

    Only INDEPENDENT items may contribute support to a decision.
    """

    DECLARED = "declared"
    INDEPENDENT = "independent"


class ExtractionMethod(str, Enum):
    DETERMINISTIC = "deterministic"
    RULE_BASED = "rule_based"
    LLM = "llm"


class Explicitness(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    UNKNOWN = "unknown"


class Reliability(str, Enum):
    """Heuristic evidence reliability hierarchy (NOT calibrated probabilities)."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    WEAK = "weak"
    NOT_APPLICABLE = "not_applicable"


class EvidenceItem(BaseModel):
    """A single traceable piece of lineage evidence.

    Optional fields stay ``None`` rather than being filled with meaningless
    placeholders.
    """

    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    role: EvidenceRole
    extraction_method: ExtractionMethod
    reliability: Reliability
    source_name: str | None = None
    repository: str | None = None
    revision: str | None = None
    candidate_parent: str | None = None
    relation: Relation | None = None
    relation_raw: str | None = None
    raw_value: str | None = None
    evidence_span: str | None = None
    explicitness: Explicitness = Explicitness.UNKNOWN
    source_url: str | None = None
    note: str | None = None


def split_by_role(items: Iterable[EvidenceItem]) -> tuple[list[EvidenceItem], list[EvidenceItem]]:
    """Split evidence into (declared, independent).

    This enforces the core architectural rule: declared metadata is the
    subject of the audit and is never independent proof of itself.
    """
    declared: list[EvidenceItem] = []
    independent: list[EvidenceItem] = []
    for item in items:
        if item.role is EvidenceRole.DECLARED:
            declared.append(item)
        else:
            independent.append(item)
    return declared, independent


_MODEL_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

# File-looking suffixes are never valid Hugging Face model-name components.
_FILE_LIKE_SUFFIXES = (
    ".json", ".yaml", ".yml", ".txt", ".md", ".csv", ".py", ".bin",
    ".safetensors", ".pt", ".pth", ".ckpt", ".pkl", ".npy", ".npz",
    ".gguf", ".ggml", ".onnx", ".tar", ".gz", ".zip", ".log", ".cfg",
    ".ini", ".toml", ".sh",
)


def is_plausible_model_id(value: object) -> bool:
    """Conservative syntactic check for an ``org/name`` Hugging Face model ID.

    This only rejects clearly invalid values (local paths, file names, bare
    names without a namespace, ...). It does NOT resolve or disambiguate
    names — that is the job of the entity-resolution layer.
    """
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    parts = candidate.split("/")
    if len(parts) != 2:
        return False
    namespace, name = parts
    if not _MODEL_ID_RE.fullmatch(namespace) or not _MODEL_ID_RE.fullmatch(name):
        return False
    if name.lower().endswith(_FILE_LIKE_SUFFIXES) or namespace.lower().endswith(_FILE_LIKE_SUFFIXES):
        return False
    return True
