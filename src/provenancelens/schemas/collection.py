"""Structured results of a lightweight Hugging Face repository collection.

Repository-level status (can the repository be inspected at all?) is kept
separate from per-file status (did an individual artifact download?), so a
single failed file never discards the evidence that was successfully
retrieved (PARTIAL, not failure).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CollectionStatus(str, Enum):
    """Repository-level outcome of a collection attempt."""

    SUCCESS = "SUCCESS"                  # all selected files retrieved
    PARTIAL = "PARTIAL"                  # some files retrieved, some failed
    NOT_FOUND = "NOT_FOUND"              # repository does not exist (or is invisible)
    PRIVATE_OR_GATED = "PRIVATE_OR_GATED"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"      # transport failure (or all files failed)
    INVALID_REPOSITORY = "INVALID_REPOSITORY"
    NO_RELEVANT_FILES = "NO_RELEVANT_FILES"  # repository resolved, nothing provenance-relevant


class FileStatus(str, Enum):
    """Per-file outcome (distinct from the repository-level status)."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FileCategory(str, Enum):
    """Why a file was selected (drives parser routing)."""

    MODEL_CARD = "model_card"
    CORE_CONFIG = "core_config"
    ADAPTER = "adapter"
    TOKENIZER_CONFIG = "tokenizer_config"
    GENERATION_CONFIG = "generation_config"
    TRAINING = "training"
    MERGE = "merge"
    QUANTIZATION = "quantization"
    PROVENANCE = "provenance"
    OTHER = "other"


class RetrievedFile(BaseModel):
    """One file's collection record with full source traceability."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    status: FileStatus
    category: FileCategory = FileCategory.OTHER
    selection_reason: str | None = None
    source_url: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    retrieved_at: str | None = None
    error: str | None = None


class CollectionResult(BaseModel):
    """Everything one collection run produced.

    ``contents`` maps filename -> decoded UTF-8 text for successfully
    retrieved files only; it is never written into the snapshot manifest
    (manifests hold metadata, file bodies are stored separately).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    repository: str
    requested_revision: str | None = None
    resolved_commit_sha: str | None = None
    collected_at: str
    status: CollectionStatus
    max_file_bytes: int
    files: list[RetrievedFile] = Field(default_factory=list)
    contents: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    @property
    def retrieved(self) -> list[RetrievedFile]:
        return [f for f in self.files if f.status is FileStatus.SUCCESS]

    @property
    def failed(self) -> list[RetrievedFile]:
        return [f for f in self.files if f.status is FileStatus.FAILED]

    @property
    def skipped(self) -> list[RetrievedFile]:
        return [f for f in self.files if f.status is FileStatus.SKIPPED]
