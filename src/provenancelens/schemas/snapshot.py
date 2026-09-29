"""Frozen snapshot manifest schema (versionable, machine-readable)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .collection import CollectionStatus, RetrievedFile

SNAPSHOT_SCHEMA_VERSION = 1


class SnapshotManifest(BaseModel):
    """Identity and provenance of one frozen snapshot.

    Identity of a snapshot is (repository, resolved_commit_sha); file lists
    are split by outcome so the manifest records what was retrieved, what
    failed, and what was deliberately skipped (and why).
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SNAPSHOT_SCHEMA_VERSION
    repository: str
    requested_revision: str | None = None
    resolved_commit_sha: str
    collected_at: str
    status: CollectionStatus
    max_file_bytes: int
    retrieved: list[RetrievedFile] = Field(default_factory=list)
    failed: list[RetrievedFile] = Field(default_factory=list)
    skipped: list[RetrievedFile] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
