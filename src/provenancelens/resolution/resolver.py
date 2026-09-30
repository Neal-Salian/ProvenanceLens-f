"""Conservative model-identifier resolution.

The purpose is *not* fuzzy model search. The purpose is to decide when two
evidence strings clearly refer to the same model, and to refuse to guess
whenever that cannot be established from the evidence itself.

Deliberately NOT done here (see CURRENT_STATE.md for the audited Phase 2
flaws this layer replaces):

* no Hugging Face search / popularity queries,
* no architecture-based guessing (vocab size, hidden size, ...),
* no organization-only or substring matching (``Qwen/`` ~= ``Qwen2.5/...``),
* no version guessing (``"Mistral 7B"`` never becomes
  ``mistralai/Mistral-7B-v0.1``: several versions exist).

Only harmless syntactic normalization plus unambiguous within-evidence
referent matching is performed.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ResolutionStatus",
    "ModelResolution",
    "normalize_identifier",
    "resolve_identifier",
    "resolve_identifiers",
    "merge_sources_to_one",
]


class ResolutionStatus(str, Enum):
    """How confidently a raw string was identified as a model."""

    EXACT = "exact"            # already a canonical ``org/name`` id
    NORMALIZED = "normalized"  # equivalent after harmless formatting fixes
    REFERENT = "referent"      # same target as another id seen in the evidence
    UNRESOLVED = "unresolved"  # plausible reference, not safely identifiable
    AMBIGUOUS = "ambiguous"    # refers to several real targets
    INVALID = "invalid"        # not a model reference at all


# ``org/name`` — both parts identifier-like (same rule the Phase C extractor
# uses, re-stated here so resolution never depends on import side effects).
_IDENTIFIER = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_EXACT_ID_RE = re.compile(rf"^{_IDENTIFIER}/{_IDENTIFIER}$")

# Looks like a model reference but carries no organization namespace.
_BARE_REFERENCE_RE = re.compile(
    rf"^{_IDENTIFIER}(?:-{_IDENTIFIER})*$",
)

# Obvious shapes that are never model ids (paths, archives, modules, URLs).
_NEVER_ID_EXTENSIONS = (
    ".json", ".yaml", ".yml", ".txt", ".md", ".py", ".safetensors", ".bin",
    ".pt", ".pth", ".ckpt", ".gguf", ".onnx", ".zip", ".tar", ".gz", ".h5",
    ".csv", ".parquet",
)
_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]|^(?:\.{1,2}[\\/])|^[\\/]")

# Hub URL forms that are pure formatting noise around an ``org/name`` id.
_HUB_URL_PREFIXES: tuple[str, ...] = (
    "https://www.huggingface.co/", "http://www.huggingface.co/",
    "https://huggingface.co/", "http://huggingface.co/",
    "https://hf.co/", "http://hf.co/",
    "www.huggingface.co/", "huggingface.co/", "hf.co/",
)


def _looks_like_path(raw: str) -> bool:
    if _ABSOLUTE_PATH_RE.search(raw):
        return True
    tail = raw.replace("\\", "/").rsplit("/", 1)[-1]
    lowered = tail.lower()
    return any(lowered.endswith(ext) for ext in _NEVER_ID_EXTENSIONS)


class ModelResolution(BaseModel):
    """Outcome of resolving one raw identifier.

    ``resolved`` stays ``None`` whenever the identifier cannot be pinned to
    exactly one model. ``alternatives`` is only populated when the evidence
    itself shows a genuine referent ambiguity (never invented).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw: str
    status: ResolutionStatus
    resolved: str | None = None
    reason: str
    alternatives: list[str] = Field(default_factory=list)


def normalize_identifier(value: object) -> str | None:
    """Apply harmless formatting normalization; ``None`` if not a model ref.

    Whitespace trimming, inner-whitespace collapsing to a hyphen, and an
    optional ``huggingface.co/`` prefix removal. Nothing semantic.
    """
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    lowered = raw.lower()
    for prefix in _HUB_URL_PREFIXES:
        if lowered.startswith(prefix):
            return _strip_hub_url(raw[len(prefix) :])
    collapsed = re.sub(r"\s+", "-", raw.strip())
    if _looks_like_path(collapsed):
        return None
    return collapsed


def _strip_hub_url(tail: str) -> str:
    """``org/name/revisions/<sha>`` -> ``org/name`` (tolerates extra path parts)."""
    parts = [p for p in tail.split("/") if p]
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return tail.strip()


def _is_bare_reference(candidate: str) -> bool:
    if _EXACT_ID_RE.match(candidate):
        return False
    if "/" in candidate or " " in candidate:
        return False
    return bool(_BARE_REFERENCE_RE.match(candidate))


def _canonical_spelling(
    candidate: str, evidence_ids: dict[str, set[str]]
) -> str | None:
    """The evidence's spelling of ``candidate``, matched case-insensitively.

    Hugging Face routes ids case-insensitively, so ``Meta-Llama/X`` and
    ``meta-llama/x`` denote one model; the evidence's own spelling wins so that
    two spellings never become rival candidates.
    """
    matches = {
        model_id
        for model_id in evidence_ids
        if model_id.lower() == candidate.lower()
    }
    if len(matches) == 1:
        return next(iter(matches))
    return None


def _evidence_index(
    evidence_ids: dict[str, set[str]], *, organization_only: bool
) -> dict[str, list[str]]:
    """Invert ``model id -> evidence aliases`` into ``alias -> [model ids]``."""
    index: dict[str, list[str]] = {}
    for model_id, aliases in sorted(evidence_ids.items()):
        for alias in sorted(aliases):
            index.setdefault(alias, []).append(model_id)
    if not organization_only:
        return index
    # A qualified model may also be known by its bare name in the evidence.
    # Multiplicity is deliberately preserved: the caller turns "several targets
    # share this name" into AMBIGUOUS instead of silently picking one.
    by_tail: dict[str, set[str]] = {}
    for model_id, aliases in evidence_ids.items():
        _, _, name = model_id.partition("/")
        for alias in set(aliases) | {name, name.lower()}:
            by_tail.setdefault(alias.lower(), set()).add(model_id)
    for alias, ids in sorted(by_tail.items()):
        index.setdefault(alias, []).extend(sorted(ids))
    for key in index:
        index[key] = sorted(set(index[key]))
    return index


def resolve_identifier(
    value: object,
    *,
    evidence_ids: dict[str, set[str]] | None = None,
    require_resolved: bool = False,
) -> ModelResolution:
    """Resolve one identifier conservatively (pure function, no I/O)."""
    evidence_ids = evidence_ids or {}

    if not isinstance(value, str) or not value.strip():
        return ModelResolution(
            raw=str(value), status=ResolutionStatus.INVALID,
            reason="empty or non-string identifier",
        )

    raw = value.strip()
    candidate = normalize_identifier(raw)
    if candidate is None:
        return ModelResolution(
            raw=raw, status=ResolutionStatus.INVALID,
            reason="not a model reference (path, URL, archive or module name)",
        )

    if _EXACT_ID_RE.match(candidate):
        # A differently-cased spelling of a model the evidence already names is
        # the *same* model: prefer the evidence's canonical spelling. The stored
        # spelling itself is never rewritten (author-controlled form).
        canonical = _canonical_spelling(candidate, evidence_ids)
        if canonical is not None and canonical != candidate:
            return ModelResolution(
                raw=raw, status=ResolutionStatus.REFERENT, resolved=canonical,
                reason="same target as an equivalent identifier present in the evidence",
            )
        if candidate == raw:
            return ModelResolution(
                raw=raw, status=ResolutionStatus.EXACT, resolved=candidate,
                reason="already a canonical organization/model identifier",
            )
        return ModelResolution(
            raw=raw, status=ResolutionStatus.NORMALIZED, resolved=candidate,
            reason="canonical identifier after harmless formatting normalization",
        )

    index = _evidence_index(evidence_ids, organization_only=False)
    matches = [m for m in index.get(candidate.lower(), []) if m.lower() == candidate.lower()]

    if len(matches) == 1:
        return ModelResolution(
            raw=raw, status=ResolutionStatus.REFERENT, resolved=matches[0],
            reason="same target as an organization-qualified id present in the evidence",
        )
    if len(matches) > 1:
        return ModelResolution(
            raw=raw, status=ResolutionStatus.AMBIGUOUS, resolved=None,
            reason="evidence contains several distinct targets for this reference",
            alternatives=sorted(matches),
        )

    org_index = _evidence_index(evidence_ids, organization_only=True)
    org_matches = [
        m for m in org_index.get(candidate.lower(), [])
        if m.lower().endswith("/" + candidate.lower())
    ]
    if len(org_matches) == 1 and org_matches[0].lower().endswith("/" + candidate.lower()):
        return ModelResolution(
            raw=raw, status=ResolutionStatus.REFERENT, resolved=org_matches[0],
            reason=(
                "unique organization-qualified target for this bare name in the evidence"
            ),
        )
    if len(org_matches) > 1:
        return ModelResolution(
            raw=raw, status=ResolutionStatus.AMBIGUOUS, resolved=None,
            reason="several organization-qualified targets share this bare name",
            alternatives=sorted(set(org_matches)),
        )

    reason = (
        "model reference without an organization namespace; not resolvable "
        "without querying a hub (no popularity or version guessing)"
    )
    if _is_bare_reference(candidate):
        status = ResolutionStatus.AMBIGUOUS
    else:
        status = ResolutionStatus.UNRESOLVED

    if require_resolved and status is not ResolutionStatus.UNRESOLVED:
        # A bare, unresolvable name is treated as ambiguous: the exact model
        # (and version) is not determinable from the evidence.
        status = ResolutionStatus.AMBIGUOUS
        reason = (
            "bare model name without namespace; several versions may exist, so "
            "the target cannot be determined from the evidence"
        )

    return ModelResolution(raw=raw, status=status, resolved=None, reason=reason)


def resolve_identifiers(
    values: Iterable[object],
    *,
    evidence_ids: dict[str, set[str]] | None = None,
) -> dict[str, ModelResolution]:
    """Resolve a set of identifiers (keyed by the raw string)."""
    return {v: resolve_identifier(v, evidence_ids=evidence_ids) for v in values}


def merge_sources_to_one(
    parents: list[str], *, evidence_ids: dict[str, set[str]] | None = None
) -> bool:
    """True when every observed merge source is the same resolved model.

    MergeKit emits one entry per source slot, so ``A`` appearing three times is
    a single source model repeated, not three independent sources.
    """
    resolved: set[str] = set()
    for parent in parents:
        resolution = resolve_identifier(parent, evidence_ids=evidence_ids)
        if resolution.resolved is None:
            return False
        resolved.add(resolution.resolved)
    return len(resolved) <= 1
