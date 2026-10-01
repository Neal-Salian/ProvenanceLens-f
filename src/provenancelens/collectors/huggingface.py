"""Lightweight Hugging Face repository collection.

Collects only provenance-relevant *text* artifacts (model card, configs,
training/merge configurations). Model weights and other binary artifacts are
never downloaded: filename/type exclusion applies first, then a conservative
maximum file size is enforced from repository metadata before any bytes are
transferred, and enforced again during streaming as a hard stop.

All downloaded content is treated as untrusted data: it is only decoded as
UTF-8 text and later parsed as JSON/YAML/Markdown - never executed or
imported. Authentication tokens are used for requests when available but are
never stored in results, manifests, or error messages.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import PurePosixPath

import httpx
from huggingface_hub import HfApi, get_token, hf_hub_url
from huggingface_hub.errors import (
    GatedRepoError,
    HFValidationError,
    HfHubHTTPError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)

from .. import __version__
from ..schemas.collection import (
    CollectionResult,
    CollectionStatus,
    FileCategory,
    FileStatus,
    RetrievedFile,
)

# Conservative default: no single metadata file larger than 1 MiB is
# retrieved (README/config/training/merge files are far smaller in practice).
DEFAULT_MAX_FILE_BYTES = 1 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 30.0

# Exact repository-root filenames that are always provenance-relevant.
PRIORITY_FILES: dict[str, FileCategory] = {
    "README.md": FileCategory.MODEL_CARD,
    "config.json": FileCategory.CORE_CONFIG,
    "adapter_config.json": FileCategory.ADAPTER,
    "tokenizer_config.json": FileCategory.TOKENIZER_CONFIG,
    "generation_config.json": FileCategory.GENERATION_CONFIG,
}

# Basename keywords that make an otherwise-unknown text file relevant.
# Order matters for deterministic category assignment (most specific first).
KEYWORD_CATEGORIES: tuple[tuple[str, FileCategory], ...] = (
    ("mergekit", FileCategory.MERGE),
    ("merge", FileCategory.MERGE),
    ("trainer", FileCategory.TRAINING),
    ("training", FileCategory.TRAINING),
    ("train", FileCategory.TRAINING),
    ("adapter", FileCategory.ADAPTER),
    ("quantiz", FileCategory.QUANTIZATION),
    ("provenance", FileCategory.PROVENANCE),
)

KEYWORD_EXTENSIONS = {".json", ".yaml", ".yml", ".md"}

# Model weights and other binary/large artifacts: never selected, regardless
# of size or keyword matches.
EXCLUDED_EXTENSIONS = (
    ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf", ".ggml",
    ".h5", ".hdf5", ".onnx", ".pb", ".tflite", ".npz", ".npy", ".pkl",
    ".pickle", ".joblib", ".msgpack", ".parquet", ".arrow", ".feather",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico",
    ".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mov", ".avi", ".mkv",
    ".exe", ".so", ".dll", ".dylib", ".whl", ".egg", ".deb", ".rpm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
)

# Names that indicate weight artifacts even with an allowed extension
# (e.g. ``model.safetensors.index.json``).
EXCLUDED_NAME_MARKERS = ("safetensors", "pytorch_model")

_REPO_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")


class FileFetchError(Exception):
    """A single selected file could not be retrieved."""


class FileTooLargeError(FileFetchError):
    """Download aborted because the file exceeded the configured limit."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(text: str, token: str | None) -> str:
    if token:
        text = text.replace(token, "***")
    return text


def is_excluded_artifact(filename: str) -> bool:
    """True for model weights / binary artifacts that must never be fetched."""
    name = PurePosixPath(filename).name.lower()
    if name.endswith(EXCLUDED_EXTENSIONS):
        return True
    return any(marker in name for marker in EXCLUDED_NAME_MARKERS)


def classify_selection(filename: str) -> tuple[FileCategory, str] | None:
    """Return (category, reason) if the file should be collected, else None.

    Weight/binary exclusion is applied first so an excluded artifact is never
    selected because of a keyword match.
    """
    if is_excluded_artifact(filename):
        return None
    if filename in PRIORITY_FILES:
        return PRIORITY_FILES[filename], "high-priority provenance file"
    path = PurePosixPath(filename)
    base = path.name.lower()
    if path.suffix.lower() not in KEYWORD_EXTENSIONS:
        return None
    for keyword, category in KEYWORD_CATEGORIES:
        if keyword in base:
            return category, f"filename keyword match: '{keyword}'"
    return None


def _package_version() -> str:
    return __version__


def _fetch_file(url: str, *, token: str | None, max_bytes: int, timeout: float) -> bytes:
    """Stream one file with a hard byte cap; raise FileFetchError on any issue."""
    headers = {"User-Agent": f"provenancelens/{_package_version()}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    raise FileFetchError(f"HTTP {response.status_code}")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise FileTooLargeError(
                            f"file exceeded limit of {max_bytes} bytes"
                        )
                    chunks.append(chunk)
                return b"".join(chunks)
    except FileFetchError:
        raise
    except httpx.HTTPError as exc:
        raise FileFetchError(f"transport error: {type(exc).__name__}: {exc}") from exc


def _safe_token() -> str | None:
    try:
        return get_token()
    except Exception:
        return None


def _status_for_http_error(exc: HfHubHTTPError) -> CollectionStatus:
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    if status_code == 429:
        return CollectionStatus.RATE_LIMITED
    if status_code in (401, 403):
        return CollectionStatus.PRIVATE_OR_GATED
    if status_code == 404:
        return CollectionStatus.NOT_FOUND
    return CollectionStatus.NETWORK_ERROR


def _plan_files(
    siblings: list[object], max_file_bytes: int
) -> tuple[list[tuple[str, FileCategory, str, int | None]], list[RetrievedFile]]:
    """Split repository files into (to-download, skipped-with-reason)."""
    selected: list[tuple[str, FileCategory, str, int | None]] = []
    skipped: list[RetrievedFile] = []
    for sibling in siblings:
        filename = str(getattr(sibling, "rfilename", "") or "")
        if not filename:
            continue
        size = getattr(sibling, "size", None)
        size_int = size if isinstance(size, int) else None

        if is_excluded_artifact(filename):
            skipped.append(RetrievedFile(
                filename=filename, status=FileStatus.SKIPPED,
                selection_reason="excluded model/binary artifact",
                size_bytes=size_int,
            ))
            continue
        plan = classify_selection(filename)
        if plan is None:
            skipped.append(RetrievedFile(
                filename=filename, status=FileStatus.SKIPPED,
                selection_reason="not provenance-relevant",
                size_bytes=size_int,
            ))
            continue
        category, reason = plan
        if size_int is None:
            skipped.append(RetrievedFile(
                filename=filename, status=FileStatus.SKIPPED,
                category=category,
                selection_reason="file size unavailable; refused without size metadata",
            ))
            continue
        if size_int > max_file_bytes:
            skipped.append(RetrievedFile(
                filename=filename, status=FileStatus.SKIPPED,
                category=category,
                selection_reason=f"size {size_int} exceeds limit {max_file_bytes}",
                size_bytes=size_int,
            ))
            continue
        selected.append((filename, category, reason, size_int))
    return selected, skipped


class HuggingFaceCollector:
    """Collects provenance-relevant files from a Hugging Face model repository.

    Network access is confined to two injectable seams so unit tests can mock
    them: ``api`` (repository metadata via ``HfApi``) and ``fetcher`` (bytes).
    """

    def __init__(
        self,
        *,
        api: object | None = None,
        fetcher: Callable[..., bytes] | None = None,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._api = api if api is not None else HfApi()
        self._fetch = fetcher if fetcher is not None else _fetch_file
        self.max_file_bytes = max_file_bytes
        self.timeout = timeout

    def collect(self, repo_id: object, revision: str | None = None) -> CollectionResult:
        """Collect provenance-relevant files. Never raises on repository failure."""
        token = _safe_token()
        collected_at = _utc_now()
        base: dict[str, object] = {
            "repository": repo_id if isinstance(repo_id, str) else str(repo_id),
            "requested_revision": revision,
            "collected_at": collected_at,
            "max_file_bytes": self.max_file_bytes,
        }

        if not isinstance(repo_id, str) or not _REPO_ID_RE.match(repo_id.strip()):
            return CollectionResult(
                **base,
                status=CollectionStatus.INVALID_REPOSITORY,
                notes=[f"invalid repository id: {base['repository']!r}"],
            )
        repo_id = repo_id.strip()

        info, error_result = self._resolve_repository(repo_id, revision, base, token)
        if error_result is not None:
            return error_result

        commit = str(info.sha)
        siblings = list(getattr(info, "siblings", []) or [])
        selected, skipped = _plan_files(siblings, self.max_file_bytes)

        files: list[RetrievedFile] = list(skipped)
        contents: dict[str, str] = {}

        if not selected:
            return CollectionResult(
                **base, resolved_commit_sha=commit,
                status=CollectionStatus.NO_RELEVANT_FILES,
                files=files,
                notes=["repository resolved; no provenance-relevant lightweight files found"],
            )

        for filename, category, reason, size in selected:
            record = RetrievedFile(
                filename=filename,
                status=FileStatus.FAILED,
                category=category,
                selection_reason=reason,
                source_url=hf_hub_url(repo_id, filename, revision=commit),
                size_bytes=size,
            )
            try:
                data = self._fetch(
                    record.source_url,
                    token=token,
                    max_bytes=self.max_file_bytes,
                    timeout=self.timeout,
                )
                text = data.decode("utf-8")
            except FileTooLargeError as exc:
                record.status = FileStatus.SKIPPED
                record.error = _redact(str(exc), token)
            except (FileFetchError, UnicodeDecodeError) as exc:
                record.error = _redact(str(exc), token)
            except Exception as exc:  # one bad file must not lose the rest
                record.error = _redact(f"{type(exc).__name__}: {exc}", token)
            else:
                record.status = FileStatus.SUCCESS
                record.sha256 = hashlib.sha256(data).hexdigest()
                record.size_bytes = len(data)
                record.retrieved_at = _utc_now()
                contents[filename] = text
            files.append(record)

        return CollectionResult(
            **base,
            resolved_commit_sha=commit,
            status=_overall_status(files),
            files=files,
            contents=contents,
            notes=_overall_notes(files),
        )

    def _resolve_repository(
        self, repo_id: str, revision: str | None, base: dict[str, object], token: str | None
    ) -> tuple[object, CollectionResult | None]:
        try:
            info = self._api.model_info(  # type: ignore[attr-defined]
                repo_id, revision=revision, files_metadata=True
            )
        except GatedRepoError as exc:
            return None, CollectionResult(
                **base, status=CollectionStatus.PRIVATE_OR_GATED,
                notes=[_redact(str(exc), token)],
            )
        except RevisionNotFoundError as exc:
            return None, CollectionResult(
                **base, status=CollectionStatus.NOT_FOUND,
                notes=[f"revision not found: {_redact(str(exc), token)}"],
            )
        except RepositoryNotFoundError as exc:
            # NOTE: Hugging Face also answers 404 for private/gated repos when
            # unauthenticated, so NOT_FOUND can mean "invisible to us".
            return None, CollectionResult(
                **base, status=CollectionStatus.NOT_FOUND,
                notes=[_redact(str(exc), token)],
            )
        except HFValidationError as exc:
            return None, CollectionResult(
                **base, status=CollectionStatus.INVALID_REPOSITORY,
                notes=[_redact(str(exc), token)],
            )
        except HfHubHTTPError as exc:
            return None, CollectionResult(
                **base, status=_status_for_http_error(exc),
                notes=[_redact(str(exc), token)],
            )
        except httpx.HTTPError as exc:
            return None, CollectionResult(
                **base, status=CollectionStatus.NETWORK_ERROR,
                notes=[_redact(f"{type(exc).__name__}: {exc}", token)],
            )
        except Exception as exc:  # safety net: collection never crashes the audit
            return None, CollectionResult(
                **base, status=CollectionStatus.NETWORK_ERROR,
                notes=[_redact(f"unexpected collector error: {type(exc).__name__}: {exc}", token)],
            )
        return info, None


def collect_repository(
    repo_id: str, revision: str | None = None, **kwargs: object
) -> CollectionResult:
    """Convenience wrapper around :class:`HuggingFaceCollector`."""
    collector = HuggingFaceCollector(**kwargs)  # type: ignore[arg-type]
    return collector.collect(repo_id, revision)


def _overall_status(files: list[RetrievedFile]) -> CollectionStatus:
    successes = sum(1 for f in files if f.status is FileStatus.SUCCESS)
    failures = sum(1 for f in files if f.status is FileStatus.FAILED)
    if failures == 0:
        return CollectionStatus.SUCCESS
    if successes > 0:
        return CollectionStatus.PARTIAL
    return CollectionStatus.NETWORK_ERROR


def _overall_notes(files: list[RetrievedFile]) -> list[str]:
    if _overall_status(files) is not CollectionStatus.NETWORK_ERROR:
        return []
    failed = [f.filename for f in files if f.status is FileStatus.FAILED]
    return [f"all selected files failed: {', '.join(failed)}"]
