"""Hugging Face collector: selection, limits, statuses — all offline/mocked."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from huggingface_hub.errors import (
    GatedRepoError,
    HfHubHTTPError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)

from provenancelens.collectors import (
    classify_selection,
    collect_repository,
    is_excluded_artifact,
)
from provenancelens.collectors.huggingface import (
    DEFAULT_MAX_FILE_BYTES,
    FileFetchError,
    FileTooLargeError,
    HuggingFaceCollector,
)
from provenancelens.schemas import CollectionStatus, FileCategory, FileStatus

SHA = "c" * 40
REQ = httpx.Request("GET", "https://huggingface.co/x")


def _resp(status: int) -> httpx.Response:
    return httpx.Response(status, request=REQ)


class FakeApi:
    """Stand-in for HfApi.model_info."""

    def __init__(self, *, sha: str = SHA, siblings=(), error: Exception | None = None):
        self._sha = sha
        self._siblings = siblings
        self._error = error
        self.calls: list[dict] = []

    def model_info(self, repo_id, revision=None, files_metadata=True):
        self.calls.append({"repo_id": repo_id, "revision": revision,
                           "files_metadata": files_metadata})
        if self._error is not None:
            raise self._error
        return SimpleNamespace(sha=self._sha, siblings=list(self._siblings))


def _sibling(name: str, size: int | None = 100) -> SimpleNamespace:
    return SimpleNamespace(rfilename=name, size=size)


def _fetcher(contents: dict[str, bytes] | None = None, errors: dict[str, Exception] | None = None):
    """Recorder fetcher: returns canned bytes or raises per-filename."""
    calls: list[str] = []

    def fetch(url: str, *, token=None, max_bytes: int, timeout: float) -> bytes:
        calls.append(url)
        for name, exc in (errors or {}).items():
            if name in url:
                raise exc
        for name, data in (contents or {}).items():
            if name in url:
                return data
        return b"{}"

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


# --- selection primitives ---------------------------------------------------


def test_priority_files_select_with_reason():
    assert classify_selection("README.md") == (
        FileCategory.MODEL_CARD, "high-priority provenance file")
    assert classify_selection("adapter_config.json")[0] is FileCategory.ADAPTER


def test_keyword_selection_by_basename():
    category, reason = classify_selection("configs/mergekit.yaml")
    assert category is FileCategory.MERGE
    assert "mergekit" in reason
    assert classify_selection("train_lora.yml")[0] is FileCategory.TRAINING
    assert classify_selection("notes.txt") is None


def test_weights_and_indices_excluded_before_selection():
    assert is_excluded_artifact("model.safetensors")
    assert is_excluded_artifact("model.safetensors.index.json")
    assert is_excluded_artifact("pytorch_model.bin")
    assert is_excluded_artifact("weights/model-00001-of-00002.safetensors")
    # index JSON has an allowed extension but a weight marker in the name
    assert classify_selection("model.safetensors.index.json") is None
    assert not is_excluded_artifact("README.md")


def test_subdirectory_ignored_for_priority_names():
    # Only exact repository-root names count as priority files.
    assert classify_selection("docs/README.md") is None
    assert classify_selection("configs/config.json") is None


# --- happy path -------------------------------------------------------------


def test_collect_success_full_repository():
    api = FakeApi(siblings=[
        _sibling("README.md", 500),
        _sibling("config.json", 200),
        _sibling("mergekit.yaml", 120),
        _sibling("model.safetensors", 10_000_000),
        _sibling("random.txt", 40),
    ])
    fetch = _fetcher(contents={
        "README.md": b"# card\n",
        "config.json": b'{"architectures": []}',
        "mergekit.yaml": b"models: []\n",
    })
    result = HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")

    assert result.status is CollectionStatus.SUCCESS
    assert result.resolved_commit_sha == SHA
    assert api.calls[0]["files_metadata"] is True
    assert result.contents["README.md"] == "# card\n"
    selected = [f.filename for f in result.files if f.status is FileStatus.SUCCESS]
    assert selected == ["README.md", "config.json", "mergekit.yaml"]
    weights = next(f for f in result.files if f.filename == "model.safetensors")
    assert weights.status is FileStatus.SKIPPED
    assert "excluded" in weights.selection_reason
    readme = next(f for f in result.files if f.filename == "README.md")
    assert readme.sha256 and len(readme.sha256) == 64
    assert readme.source_url == f"https://huggingface.co/org/model/resolve/{SHA}/README.md"
    assert fetch.calls and all(SHA in url for url in fetch.calls)


def test_fetch_only_selected_files():
    api = FakeApi(siblings=[
        _sibling("README.md", 10),
        _sibling("training/train.yaml", 10),
        _sibling("video.mp4", 5),
        _sibling("LICENSE", 10),
    ])
    fetch = _fetcher()
    HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")
    assert len(fetch.calls) == 2


# --- size safety ------------------------------------------------------------


def test_declared_oversize_file_skipped_before_download():
    api = FakeApi(siblings=[
        _sibling("README.md", 10),
        _sibling("huge_training.yaml", DEFAULT_MAX_FILE_BYTES + 1),
    ])
    fetch = _fetcher()
    result = HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")
    huge = next(f for f in result.files if f.filename == "huge_training.yaml")
    assert huge.status is FileStatus.SKIPPED
    assert "exceeds limit" in huge.selection_reason
    assert all("huge_training" not in url for url in fetch.calls)
    assert result.status is CollectionStatus.SUCCESS


def test_missing_size_refused_without_download():
    api = FakeApi(siblings=[_sibling("README.md", None)])
    fetch = _fetcher()
    result = HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")
    only = next(f for f in result.files if f.filename == "README.md")
    assert only.status is FileStatus.SKIPPED
    assert "size metadata" in only.selection_reason
    assert fetch.calls == []


def test_streaming_cap_enforced_even_if_metadata_lies():
    api = FakeApi(siblings=[
        _sibling("README.md", 10),
        _sibling("train_big.yaml", 10),  # metadata claims small...
    ])
    fetch = _fetcher(errors={"train_big.yaml": FileTooLargeError("file exceeded limit of 10 bytes")})
    result = HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")
    big = next(f for f in result.files if f.filename == "train_big.yaml")
    assert big.status is FileStatus.SKIPPED
    assert "exceeded limit" in (big.error or "")
    assert result.status is CollectionStatus.SUCCESS
    assert any("train_big.yaml" in url for url in fetch.calls)  # attempted despite lie


def test_custom_max_file_bytes_is_respected():
    api = FakeApi(siblings=[_sibling("README.md", 500)])
    fetch = _fetcher()
    result = HuggingFaceCollector(api=api, fetcher=fetch, max_file_bytes=100).collect("org/model")
    readme = next(f for f in result.files if f.filename == "README.md")
    assert readme.status is FileStatus.SKIPPED
    assert fetch.calls == []


# --- statuses ---------------------------------------------------------------


def test_partial_when_some_fetches_fail():
    api = FakeApi(siblings=[_sibling("README.md", 10), _sibling("config.json", 10)])
    fetch = _fetcher(contents={"README.md": b"# ok"},
                     errors={"config.json": FileFetchError("HTTP 500")})
    result = HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")
    assert result.status is CollectionStatus.PARTIAL
    failed = next(f for f in result.files if f.filename == "config.json")
    assert failed.status is FileStatus.FAILED
    assert "HTTP 500" in (failed.error or "")


def test_all_fetches_failed_maps_to_network_error():
    api = FakeApi(siblings=[_sibling("README.md", 10)])
    fetch = _fetcher(errors={"README.md": FileFetchError("transport error")})
    result = HuggingFaceCollector(api=api, fetcher=fetch).collect("org/model")
    assert result.status is CollectionStatus.NETWORK_ERROR
    assert result.notes and "README.md" in result.notes[0]


def test_repository_not_found():
    api = FakeApi(error=RepositoryNotFoundError("404", response=_resp(404)))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/missing")
    assert result.status is CollectionStatus.NOT_FOUND
    assert result.files == []


def test_private_or_gated_repository():
    api = FakeApi(error=GatedRepoError("gated", response=_resp(403)))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/gated")
    assert result.status is CollectionStatus.PRIVATE_OR_GATED


def test_revision_not_found_maps_to_not_found():
    api = FakeApi(error=RevisionNotFoundError(
        "revision bad-rev not found", response=_resp(404)))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/model", "bad-rev")
    assert result.status is CollectionStatus.NOT_FOUND
    assert any("bad-rev" in note for note in result.notes)


def test_rate_limited():
    api = FakeApi(error=HfHubHTTPError("slow down", response=_resp(429)))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/model")
    assert result.status is CollectionStatus.RATE_LIMITED


def test_network_error_from_transport():
    api = FakeApi(error=httpx.ConnectError("dns", request=REQ))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/model")
    assert result.status is CollectionStatus.NETWORK_ERROR


def test_unexpected_exception_never_escapes():
    api = FakeApi(error=RuntimeError("boom"))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/model")
    assert result.status is CollectionStatus.NETWORK_ERROR
    assert any("boom" in note for note in result.notes)


def test_invalid_repository_id_rejected_locally():
    api = FakeApi()
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("not a repo id")
    assert result.status is CollectionStatus.INVALID_REPOSITORY
    assert api.calls == []


def test_non_string_repository_id_rejected():
    result = HuggingFaceCollector(api=FakeApi(), fetcher=_fetcher()).collect(12345)
    assert result.status is CollectionStatus.INVALID_REPOSITORY


def test_no_relevant_files():
    api = FakeApi(siblings=[_sibling("LICENSE", 10), _sibling("model.safetensors", 10)])
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/model")
    assert result.status is CollectionStatus.NO_RELEVANT_FILES
    assert result.resolved_commit_sha == SHA


# --- hygiene ----------------------------------------------------------------


def test_error_notes_redact_tokens(monkeypatch):
    monkeypatch.setattr("huggingface_hub.get_token", lambda: "hf_secrettoken123", raising=False)
    monkeypatch.setattr(
        "provenancelens.collectors.huggingface.get_token",
        lambda: "hf_secrettoken123",
    )
    api = FakeApi(error=RepositoryNotFoundError(
        "401 for https://hf.co/x?token=hf_secrettoken123", response=_resp(404)))
    result = HuggingFaceCollector(api=api, fetcher=_fetcher()).collect("org/model")
    joined = " ".join(result.notes)
    assert "hf_secrettoken123" not in joined
    assert "***" in joined


def test_collect_never_returns_contents_for_error_statuses():
    for error in (
        RepositoryNotFoundError("404", response=_resp(404)),
        httpx.ConnectError("dns", request=REQ),
    ):
        result = HuggingFaceCollector(api=FakeApi(error=error),
                                      fetcher=_fetcher()).collect("org/model")
        assert result.contents == {}
        assert result.status is not CollectionStatus.SUCCESS


def test_convenience_wrapper_matches_direct_call():
    # collect_repository builds its own real HfApi; here we only assert the
    # seam exists and validates input without touching the network.
    result = collect_repository("bad id")
    assert result.status is CollectionStatus.INVALID_REPOSITORY
