"""Deterministic, bounded prose chunking.

No embeddings, no vector search, no model involvement: chunks are produced by
explainable rules so any claim can be traced back to exact character offsets
in the original file.

Policy:

1. YAML front matter is removed first - declared metadata is parsed
   deterministically and must never be re-read by the LLM ("LLM last").
2. Fenced code blocks and indented code are dropped, so commands, shell
   snippets, and Python files can never be handed to the model as content.
3. The remaining prose is split on markdown headings, then on blank-line
   paragraph boundaries, then hard-split if a single paragraph exceeds the
   character budget.
4. Every chunk keeps ``start``/``end`` offsets into the *original* document so
   evidence spans can be located in the untouched source text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Bounded default sizes. Tuned for a 8 GB laptop CPU/GPU-unified inference:
#: small enough to stay fast, large enough to keep a lineage sentence intact.
DEFAULT_MAX_CHUNK_CHARS = 1200
DEFAULT_MAX_CHUNKS = 6

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_FENCED_CODE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
#: Inline code spans (shell commands, flags, paths) are not prose.
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_INDENTED_CODE_RE = re.compile(r"^(?: {4}|\t).*$", re.MULTILINE)


@dataclass(frozen=True)
class ProseChunk:
    """One bounded piece of repository prose with traceable offsets."""

    index: int
    text: str
    start: int
    end: int
    heading: str | None = None
    section: str | None = None

    @property
    def size(self) -> int:
        return len(self.text)


def strip_front_matter(text: str) -> tuple[str, int]:
    """Return (text without YAML front matter, offset where prose starts)."""
    match = _FRONTMATTER_RE.match(text or "")
    if not match:
        return text or "", 0
    return text[match.end() :], match.end()


def strip_non_prose(text: str) -> str:
    """Remove fenced and inline code, HTML comments, and indented code.

    Commands and code are never treated as prose: they cannot become evidence
    and they are never handed to the model.
    """
    without_fences = _FENCED_CODE_RE.sub("\n", text)
    without_inline = _INLINE_CODE_RE.sub(" ", without_fences)
    without_comments = _HTML_COMMENT_RE.sub("\n", without_inline)
    return _INDENTED_CODE_RE.sub("", without_comments)


def _split_units(text: str) -> list[tuple[str | None, str]]:
    """Split into (heading, block) units, preserving reading order."""
    units: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            units.append((current_heading, body))

    for block in re.split(r"\n\s*\n", text):
        block = block.strip("\n")
        if not block.strip():
            continue
        heading_match = _HEADING_RE.match(block.strip())
        if heading_match:
            flush()
            buffer = []
            current_heading = heading_match.group(2).strip()
            # text directly after a heading line stays in the same unit
            remainder = block.strip()[heading_match.end():].strip()
            if remainder:
                buffer.append(remainder)
            continue
        buffer.append(block)
    flush()
    return units


def _hard_split(body: str, max_chars: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    pieces: list[str] = []
    remaining = body
    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        cut = max(window.rfind(". "), window.rfind("\n"), window.rfind("! "),
                   window.rfind("? "))
        if cut <= max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        pieces.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        pieces.append(remaining)
    return [piece for piece in pieces if piece]


def chunk_prose(
    text: str,
    *,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    max_chunks: int | None = None,
) -> list[ProseChunk]:
    """Split repository prose into bounded, traceable chunks.

    ``max_chunks`` caps how many chunks are produced (headings and paragraph
    order are preserved, so the first sections win; the caller decides which
    chunks are actually sent to the model).
    """
    prose, offset = strip_front_matter(text or "")
    cleaned = strip_non_prose(prose)

    # Recompute offsets against the original document by tracking a cursor.
    chunks: list[ProseChunk] = []
    cursor = 0
    for heading, body in _split_units(cleaned):
        for piece in _hard_split(body, max_chunk_chars):
            start_in_cleaned = cleaned.find(piece, cursor)
            if start_in_cleaned == -1:  # pragma: no cover - defensive
                start_in_cleaned = cursor
            cursor = start_in_cleaned + len(piece)
            chunks.append(ProseChunk(
                index=len(chunks),
                text=piece,
                start=offset + start_in_cleaned,
                end=offset + start_in_cleaned + len(piece),
                heading=heading,
                section=heading,
            ))
    if max_chunks is not None:
        chunks = chunks[:max_chunks]
    return chunks
