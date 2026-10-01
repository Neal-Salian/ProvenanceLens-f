"""Provenance-relevant prose section selection.

Which chunks are worth sending to a local model is a *deterministic* decision
made here, not by the LLM (the model never chooses which files to read).

Policy:

1. **Heading priority.** Sections whose heading matches a lineage term
   (``base model``, ``fine-tun``, ``train``, ``merge``, ``quantiz``,
   ``adapter``, ``lineage``, ``provenance``, ``how the model was created``,
   ``model details``, ...) are selected first, in document order.
2. **Content priority.** Among the remaining chunks, those containing lineage
   *verbs* together with a model-id-shaped token are selected next.
3. **Bounded fallback.** If nothing matched, the first ``fallback_chunks``
   prose chunks are sent anyway, because an unusual heading should not hide a
   lineage statement.
4. **Budget.** At most ``max_chunks`` chunks are ever selected, and a document
   with no prose at all selects nothing.
"""

from __future__ import annotations

import re

from .chunking import ProseChunk

__all__ = [
    "HEADING_PRIORITY_TERMS",
    "LINEAGE_VERBS",
    "select_provenance_chunks",
]

HEADING_PRIORITY_TERMS: tuple[str, ...] = (
    "base model", "parent model", "model details", "model description",
    "how the model was created", "lineage", "provenance", "fine-tun",
    "finetun", "fine-tun", "training", "trained", "train", "fine-tuning",
    "merge", "merging", "merged", "adapter", "lora", "peft", "quantiz",
    "quantis", "quantization", "derivation", "pre-train", "pretrain",
    "checkpoint", "weights", "model info", "model card", "about",
)

LINEAGE_VERBS: tuple[str, ...] = (
    "fine-tun", "finetun", "fine_tun", "trained on", "trained from",
    "trained on top of", "further train", "continued pre-training",
    "continued pretraining", "pre-trained on", "pretrained on",
    "initialized from", "initialised from", "built on", "built from",
    "based on", "derived from", "adapted from", "adaptor for", "adapter for",
    "lora for", "merged from", "merge of", "merged with", "combined from",
    "combination of", "quantized from", "quantised from", "quantized version",
    "quantised version", "gguf version of", "distilled from",
)

_MODEL_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*")
_BARE_NAME_RE = re.compile(
    r"\b(?:llama|mistral|qwen|gemma|phi|falcon|mpt|opt|bloom|mixtral)\b",
    re.IGNORECASE,
)


def _heading_priority(chunk: ProseChunk) -> int:
    heading = (chunk.heading or "").lower()
    return sum(1 for term in HEADING_PRIORITY_TERMS if term in heading)


def _content_priority(chunk: ProseChunk) -> int:
    lowered = chunk.text.lower()
    verbs = sum(1 for verb in LINEAGE_VERBS if verb in lowered)
    has_id = 1 if _MODEL_ID_RE.search(chunk.text) else 0
    has_bare = 1 if _BARE_NAME_RE.search(chunk.text) else 0
    return verbs * 2 + has_id + has_bare


def select_provenance_chunks(
    chunks: list[ProseChunk],
    *,
    max_chunks: int,
    fallback_chunks: int = 1,
) -> list[ProseChunk]:
    """Select lineage-relevant chunks deterministically, in document order."""
    if not chunks or max_chunks <= 0:
        return []

    scored: list[tuple[int, int, ProseChunk]] = []
    for chunk in chunks:
        score = _heading_priority(chunk) * 10 + _content_priority(chunk)
        if score > 0:
            scored.append((-score, chunk.index, chunk))

    if not scored:
        # Bounded fallback: unfamiliar headings must not hide a lineage claim.
        return chunks[: min(fallback_chunks, max_chunks)]

    scored.sort()
    selected = [chunk for _neg, _idx, chunk in scored[:max_chunks]]
    return sorted(selected, key=lambda c: c.index)
