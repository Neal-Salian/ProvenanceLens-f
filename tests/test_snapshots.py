"""Frozen snapshots: identity, immutability, path safety, offline load."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from provenancelens.schemas import (
    CollectionResult,
    CollectionStatus,
    FileStatus,
    RetrievedFile,
)
from provenancelens.snapshots import (
    SnapshotConflictError,
    SnapshotError,
    SnapshotIntegrityError,
    SnapshotNotFoundError,
    encode_repo_id,
    load_snapshot,
    save_extracted_evidence,
    save_snapshot,
)

SHA = "d" * 40
REPO = "org/model"


def make_collection(
    *,
    repo: str = REPO,
    sha: str | None = SHA,
    status: CollectionStatus = CollectionStatus.SUCCESS,
    contents: dict[str, str] | None = None,
    collected_at: str = "2026-01-01T00:00:00+00:00",
    note: str | None = None,
) -> CollectionResult:
    contents = contents if contents is not None else {"README.md": "# card\n"}
    files = [
        RetrievedFile(
            filename=name,
            status=FileStatus.SUCCESS,
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            retrieved_at=collected_at,
        )
        for name, text in contents.items()
    ]
    if note:
        files.append(RetrievedFile(filename="bad.json", status=FileStatus.FAILED, error=note))
    return CollectionResult(
        repository=repo,
        requested_revision="main",
        resolved_commit_sha=sha,
        collected_at=collected_at,
        status=status,
        max_file_bytes=1024,
        files=files,
        contents=contents,
        notes=[note] if note else [],
    )


# --- identity / paths -------------------------------------------------------


def test_encode_repo_id():
    assert encode_repo_id("org/model") == "org__model"
    assert encode_repo_id("org/sub.model") == "org__sub.model"
    for bad in ("no-slash", "a/b/c", "../x", "", None):
        with pytest.raises(SnapshotError):
            encode_repo_id(bad)  # type: ignore[arg-type]


def test_snapshot_dir_layout(tmp_path: Path):
    from provenancelens.snapshots import snapshot_dir
    d = snapshot_dir(tmp_path, REPO, SHA)
    assert d == tmp_path / "org__model" / SHA


# --- save / load round trip -------------------------------------------------


def test_save_and_load_round_trip(tmp_path: Path):
    collection = make_collection(contents={
        "README.md": "# card\n",
        "configs/train.yaml": "model_name_or_path: org/base\n",
    })
    manifest = save_snapshot(collection, root=tmp_path)
    assert manifest.repository == REPO
    assert manifest.resolved_commit_sha == SHA

    loaded = load_snapshot(REPO, SHA, root=tmp_path)
    assert loaded.contents["README.md"] == "# card\n"
    assert loaded.contents["configs/train.yaml"] == "model_name_or_path: org/base\n"
    assert loaded.text("README.md") == "# card\n"
    assert loaded.manifest.status is CollectionStatus.SUCCESS


def test_snapshot_files_are_frozen_read_only(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    stored = tmp_path / "org__model" / SHA / "files" / "README.md"
    assert stored.is_file()
    mode = os.stat(stored).st_mode & 0o777
    assert mode == 0o444
    manifest_mode = os.stat(tmp_path / "org__model" / SHA / "manifest.json").st_mode & 0o777
    assert manifest_mode == 0o444


def test_manifest_is_json_and_versioned(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    raw = json.loads(
        (tmp_path / "org__model" / SHA / "manifest.json").read_text(encoding="utf-8")
    )
    assert raw["schema_version"] == 1
    assert raw["repository"] == REPO
    assert raw["retrieved"][0]["filename"] == "README.md"


def test_no_volatile_content_in_manifest(tmp_path: Path):
    save_snapshot(make_collection(note="HTTP 500"), root=tmp_path)
    raw = (tmp_path / "org__model" / SHA / "manifest.json").read_text(encoding="utf-8")
    assert "# card" not in raw  # file bodies stay out of the manifest


# --- reuse / conflict -------------------------------------------------------


def test_identical_snapshot_reused_despite_new_timestamp(tmp_path: Path):
    first = make_collection(collected_at="2026-01-01T00:00:00+00:00")
    save_snapshot(first, root=tmp_path)
    second = make_collection(collected_at="2026-02-02T00:00:00+00:00")
    manifest = save_snapshot(second, root=tmp_path)  # no error
    assert manifest.collected_at == "2026-01-01T00:00:00+00:00"  # original kept


def test_different_content_for_same_identity_conflicts(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    changed = make_collection(contents={"README.md": "# DIFFERENT\n"})
    with pytest.raises(SnapshotConflictError):
        save_snapshot(changed, root=tmp_path)


def test_existing_directory_without_manifest_conflicts(tmp_path: Path):
    (tmp_path / "org__model" / SHA).mkdir(parents=True)
    with pytest.raises(SnapshotConflictError):
        save_snapshot(make_collection(), root=tmp_path)


def test_corrupt_existing_snapshot_detected_on_reuse(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    stored = tmp_path / "org__model" / SHA / "files" / "README.md"
    stored.chmod(0o644)
    stored.write_text("# tampered\n", encoding="utf-8")
    stored.chmod(0o444)
    with pytest.raises(SnapshotIntegrityError):
        # identical identity would be reused, but verification must fail first
        save_snapshot(make_collection(), root=tmp_path)


def test_non_freezable_status_refused(tmp_path: Path):
    with pytest.raises(SnapshotError):
        save_snapshot(make_collection(status=CollectionStatus.NOT_FOUND, contents={}), root=tmp_path)
    with pytest.raises(SnapshotError):
        save_snapshot(make_collection(status=CollectionStatus.NETWORK_ERROR, contents={}), root=tmp_path)


def test_invalid_commit_refused(tmp_path: Path):
    with pytest.raises(SnapshotError):
        save_snapshot(make_collection(sha="short"), root=tmp_path)


# --- path safety ------------------------------------------------------------


def test_path_traversal_filename_refused(tmp_path: Path):
    evil = make_collection(contents={"../../../etc/passwd": "root:x\n"})
    with pytest.raises(SnapshotIntegrityError):
        save_snapshot(evil, root=tmp_path)
    assert not (tmp_path.parent / "passwd").exists()


def test_absolute_filename_refused(tmp_path: Path):
    evil = make_collection(contents={"/etc/passwd": "root:x\n"})
    with pytest.raises(SnapshotIntegrityError):
        save_snapshot(evil, root=tmp_path)


def test_backslash_filename_refused(tmp_path: Path):
    evil = make_collection(contents={"..\\..\\evil.txt": "x"})
    with pytest.raises(SnapshotIntegrityError):
        save_snapshot(evil, root=tmp_path)


# --- offline load integrity -------------------------------------------------


def test_load_missing_snapshot_raises(tmp_path: Path):
    with pytest.raises(SnapshotNotFoundError):
        load_snapshot(REPO, SHA, root=tmp_path)


def test_tampered_file_fails_hash_verification(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    stored = tmp_path / "org__model" / SHA / "files" / "README.md"
    stored.chmod(0o644)
    stored.write_text("# tampered\n", encoding="utf-8")
    stored.chmod(0o444)
    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(REPO, SHA, root=tmp_path)
    loaded = load_snapshot(REPO, SHA, root=tmp_path, verify_hashes=False)
    assert loaded.contents["README.md"] == "# tampered\n"


def test_corrupt_manifest_fails_to_load(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    manifest = tmp_path / "org__model" / SHA / "manifest.json"
    manifest.chmod(0o644)
    manifest.write_text("{not json", encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(REPO, SHA, root=tmp_path)


def test_manifest_identity_mismatch_fails(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    manifest = tmp_path / "org__model" / SHA / "manifest.json"
    manifest.chmod(0o644)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["repository"] = "org/other"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(REPO, SHA, root=tmp_path)


def test_non_utf8_snapshot_file_fails_cleanly(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    stored = tmp_path / "org__model" / SHA / "files" / "README.md"
    stored.chmod(0o644)
    stored.write_bytes(b"\xff\xfe\x00binary")
    stored.chmod(0o444)
    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(REPO, SHA, root=tmp_path)


# --- extracted evidence persistence ----------------------------------------


def test_save_extracted_evidence_round_trip(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    payload = {"schema_version": 1, "repository": REPO, "independent_evidence": []}
    target = save_extracted_evidence(REPO, SHA, payload, root=tmp_path)
    assert json.loads(target.read_text(encoding="utf-8")) == payload
    # identical payload is reused silently
    assert save_extracted_evidence(REPO, SHA, payload, root=tmp_path) == target


def test_save_extracted_evidence_conflict_then_overwrite(tmp_path: Path):
    save_snapshot(make_collection(), root=tmp_path)
    save_extracted_evidence(REPO, SHA, {"v": 1}, root=tmp_path)
    with pytest.raises(SnapshotConflictError):
        save_extracted_evidence(REPO, SHA, {"v": 2}, root=tmp_path)
    target = save_extracted_evidence(REPO, SHA, {"v": 2}, root=tmp_path, overwrite=True)
    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 2}


def test_save_extracted_evidence_requires_snapshot(tmp_path: Path):
    with pytest.raises(SnapshotNotFoundError):
        save_extracted_evidence(REPO, SHA, {}, root=tmp_path)
