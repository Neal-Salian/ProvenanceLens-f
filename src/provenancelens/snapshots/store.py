"""Frozen evidence snapshot storage: save, validate, and load offline.

A snapshot is identified by ``(repository, resolved_commit_sha)``. Once
written, it is treated as immutable:

- re-saving an identical snapshot validates and reuses it,
- re-saving a *different* snapshot into the same identity raises
  :class:`SnapshotConflictError` (no silent overwrite or mutation),
- every filename coming from a manifest or repository is path-validated so
  hostile names like ``../../etc/passwd`` can never escape the snapshot
  directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..schemas.collection import CollectionResult, CollectionStatus, FileStatus
from ..schemas.snapshot import SNAPSHOT_SCHEMA_VERSION, SnapshotManifest

DEFAULT_SNAPSHOT_ROOT = Path("data/snapshots")

_REPO_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Statuses that represent evidence worth freezing. Repository-level failures
# (NOT_FOUND, ...) carry no artifacts and are audit state, not snapshots.
_FREEZABLE_STATUSES = frozenset({
    CollectionStatus.SUCCESS,
    CollectionStatus.PARTIAL,
    CollectionStatus.NO_RELEVANT_FILES,
})


class SnapshotError(Exception):
    """Base class for snapshot storage problems."""


class SnapshotConflictError(SnapshotError):
    """Existing snapshot disagrees with what we tried to write."""


class SnapshotNotFoundError(SnapshotError):
    """Requested snapshot does not exist locally."""


class SnapshotIntegrityError(SnapshotError):
    """Snapshot exists but is corrupt/incomplete/hostile."""


def encode_repo_id(repo_id: str) -> str:
    """Encode ``org/model`` as a safe single directory name (``org__model``)."""
    if not isinstance(repo_id, str) or not _REPO_ID_RE.match(repo_id):
        raise SnapshotError(f"invalid repository id for snapshot path: {repo_id!r}")
    return repo_id.replace("/", "__")


def _validate_commit(commit: str) -> str:
    if not isinstance(commit, str) or not _COMMIT_SHA_RE.match(commit):
        raise SnapshotError(f"invalid resolved commit sha: {commit!r}")
    return commit


def snapshot_dir(root: Path, repo_id: str, commit: str) -> Path:
    """Directory of one snapshot: ``<root>/<org__model>/<commit_sha>``."""
    return Path(root) / encode_repo_id(repo_id) / _validate_commit(commit)


def _safe_file_path(files_root: Path, filename: str) -> Path:
    """Join a repository filename under ``files_root``, rejecting traversal."""
    if not isinstance(filename, str) or not filename:
        raise SnapshotIntegrityError("empty filename in snapshot")
    if "\\" in filename or filename.startswith("/"):
        raise SnapshotIntegrityError(f"unsafe filename in snapshot: {filename!r}")
    segments = filename.split("/")
    if any(seg in ("", ".", "..") for seg in segments):
        raise SnapshotIntegrityError(f"path traversal in snapshot filename: {filename!r}")
    target = files_root.joinpath(*segments)
    resolved_root = files_root.resolve()
    resolved_target = target.resolve()  # non-strict: target may not exist yet
    if not resolved_target.is_relative_to(resolved_root):
        raise SnapshotIntegrityError(f"path escapes snapshot directory: {filename!r}")
    return target


def _manifest_from_collection(collection: CollectionResult) -> SnapshotManifest:
    return SnapshotManifest(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        repository=collection.repository,
        requested_revision=collection.requested_revision,
        resolved_commit_sha=collection.resolved_commit_sha or "",
        collected_at=collection.collected_at,
        status=collection.status,
        max_file_bytes=collection.max_file_bytes,
        retrieved=collection.retrieved,
        failed=collection.failed,
        skipped=collection.skipped,
        notes=collection.notes,
    )


def _identity(manifest: SnapshotManifest) -> dict:
    """Manifest content compared for reuse (volatile fields stripped).

    Timestamps and transient per-file error strings are excluded; identity is
    repository + commit + status + file content hashes + selection metadata.
    """
    data = manifest.model_dump(mode="json")
    data.pop("collected_at", None)
    for group in ("retrieved", "failed", "skipped"):
        for record in data.get(group, []):
            record.pop("retrieved_at", None)
            record.pop("error", None)
    return data


def _read_manifest(path: Path) -> SnapshotManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotIntegrityError(f"unreadable manifest at {path}: {exc}") from exc
    try:
        return SnapshotManifest.model_validate(raw)
    except Exception as exc:
        raise SnapshotIntegrityError(f"invalid manifest at {path}: {exc}") from exc


def _verify_existing(manifest: SnapshotManifest, snap_dir: Path) -> None:
    """Validate that an existing snapshot's files are present (and match)."""
    files_root = snap_dir / "files"
    for record in manifest.retrieved:
        path = _safe_file_path(files_root, record.filename)
        if not path.is_file():
            raise SnapshotIntegrityError(
                f"snapshot file missing: {record.filename} in {snap_dir}"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if record.sha256 and record.sha256 != digest:
            raise SnapshotIntegrityError(
                f"snapshot file hash mismatch: {record.filename}"
            )


def save_snapshot(
    collection: CollectionResult,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
) -> SnapshotManifest:
    """Freeze a collection result under ``<root>/<org__model>/<commit>/``.

    Creates ``files/`` + ``manifest.json``. If the identical snapshot already
    exists it is validated and reused; if a different snapshot exists for the
    same identity, raises :class:`SnapshotConflictError`.
    """
    if collection.status not in _FREEZABLE_STATUSES:
        raise SnapshotError(
            f"status {collection.status.value} carries no freezable evidence"
        )
    commit = _validate_commit(collection.resolved_commit_sha or "")
    manifest = _manifest_from_collection(collection)

    snap_dir = snapshot_dir(root, manifest.repository, commit)
    manifest_path = snap_dir / "manifest.json"

    if manifest_path.is_file():
        existing = _read_manifest(manifest_path)
        if _identity(existing) == _identity(manifest):
            _verify_existing(existing, snap_dir)  # validate before reuse
            return existing
        raise SnapshotConflictError(
            f"snapshot {manifest.repository}@{commit} already exists with "
            "different content; refusing to overwrite immutable evidence"
        )
    if snap_dir.exists():
        raise SnapshotConflictError(
            f"directory {snap_dir} exists without a manifest (incomplete snapshot)"
        )

    files_root = snap_dir / "files"
    files_root.mkdir(parents=True, exist_ok=False)
    for filename, text in collection.contents.items():
        target = _safe_file_path(files_root, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        os.chmod(target, 0o444)  # frozen: readable, not casually writable

    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.chmod(manifest_path, 0o444)
    return manifest


@dataclass(frozen=True)
class LoadedSnapshot:
    """A snapshot loaded fully offline: manifest + decoded file contents."""

    manifest: SnapshotManifest
    contents: dict[str, str]
    path: Path

    @property
    def repository(self) -> str:
        return self.manifest.repository

    @property
    def resolved_commit_sha(self) -> str:
        return self.manifest.resolved_commit_sha

    def text(self, filename: str) -> str:
        return self.contents[filename]


def load_snapshot(
    repo_id: str,
    commit: str,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    verify_hashes: bool = True,
) -> LoadedSnapshot:
    """Load a frozen snapshot without any network access.

    Validates manifest identity, path safety, file presence, and (by default)
    content hashes so downstream parsing can trust the frozen bytes.
    """
    snap_dir = snapshot_dir(root, repo_id, commit)
    manifest_path = snap_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SnapshotNotFoundError(f"no snapshot at {snap_dir}")
    manifest = _read_manifest(manifest_path)
    if manifest.repository != repo_id or manifest.resolved_commit_sha != commit:
        raise SnapshotIntegrityError(
            f"manifest identity mismatch: {manifest.repository}@"
            f"{manifest.resolved_commit_sha} != {repo_id}@{commit}"
        )

    files_root = snap_dir / "files"
    contents: dict[str, str] = {}
    for record in manifest.retrieved:
        path = _safe_file_path(files_root, record.filename)
        if not path.is_file():
            raise SnapshotIntegrityError(f"snapshot file missing: {record.filename}")
        data = path.read_bytes()
        if verify_hashes and record.sha256:
            digest = hashlib.sha256(data).hexdigest()
            if digest != record.sha256:
                raise SnapshotIntegrityError(
                    f"snapshot hash mismatch: {record.filename}"
                )
        try:
            contents[record.filename] = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SnapshotIntegrityError(
                f"snapshot file is not UTF-8 text: {record.filename}"
            ) from exc
    return LoadedSnapshot(manifest=manifest, contents=contents, path=snap_dir)


def save_extracted_evidence(
    repo_id: str,
    commit: str,
    extraction_payload: dict,
    *,
    root: Path = DEFAULT_SNAPSHOT_ROOT,
    overwrite: bool = False,
) -> Path:
    """Persist deterministic extraction output next to the snapshot files.

    Reuses an identical ``extracted_evidence.json``; refuses to replace a
    differing one unless ``overwrite=True`` (derived data, but still not
    silently mutated).
    """
    snap_dir = snapshot_dir(root, repo_id, commit)
    if not (snap_dir / "manifest.json").is_file():
        raise SnapshotNotFoundError(f"no snapshot at {snap_dir}")
    target = snap_dir / "extracted_evidence.json"
    payload = json.dumps(extraction_payload, indent=2, ensure_ascii=False) + "\n"
    if target.is_file():
        if target.read_text(encoding="utf-8") == payload:
            return target
        if not overwrite:
            raise SnapshotConflictError(
                f"extracted_evidence.json already exists at {target} with "
                "different content; pass overwrite=True to replace derived data"
            )
    tmp = target.with_suffix(".json.tmp")
    if tmp.exists():  # stale temp from an interrupted run
        tmp.chmod(0o644)
    tmp.write_text(payload, encoding="utf-8")
    os.chmod(tmp, 0o444)
    tmp.replace(target)
    return target
