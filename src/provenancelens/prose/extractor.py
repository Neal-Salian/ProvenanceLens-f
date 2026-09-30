"""LLM prose extraction: LangChain chain, bounded chunks, strict validation.

The chain is a real LCEL pipeline::

    PromptTemplate  ->  ChatModel  ->  StrOutputParser  ->  PydanticOutputParser

Only the model invocation is injectable, so tests exercise the actual prompt
rendering, chain composition, structured parsing, and validation path while
replacing nothing but local inference.

Two deliberate properties:

* **LLM last** - the model is only ever shown prose the deterministic parsers
  could not structure. Front matter is stripped before chunking, so declared
  metadata is never re-read by the model.
* **Fail closed** - a chunk that cannot be parsed, or a claim whose span or
  parent is not in the source, is recorded as a structural failure and
  contributes no evidence. The audit continues deterministically.
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import Runnable

from .chunking import DEFAULT_MAX_CHUNK_CHARS, DEFAULT_MAX_CHUNKS, ProseChunk, chunk_prose
from .prompt import (
    PROSE_EXTRACTION_PROMPT,
    PROSE_EXTRACTION_PROMPT_VERSION,
    prompt_digest,
    render_prose_block,
)
from .schema import (
    ClaimStatus,
    ProseClaimSet,
    ProseExtractionReport,
    ProseExtractionStatus,
    ProseFailure,
    ProseFailureCode,
    ProseLineageClaim,
    build_llm_evidence_item,
)
from .selection import select_provenance_chunks
from .validation import validate_claim

__all__ = [
    "LLMProseExtractor",
    "LLMUnavailable",
    "unavailable_report",
]


class LLMUnavailable(RuntimeError):
    """The configured local chat model cannot be used (dependency or runtime)."""


class LLMProseExtractor:
    """Extract lineage claims from repository prose with a local chat model."""

    def __init__(
        self,
        chat_model: Any,
        *,
        model_name: str | None = None,
        prompt: Any = PROSE_EXTRACTION_PROMPT,
        parser: PydanticOutputParser | None = None,
        max_chunks: int = DEFAULT_MAX_CHUNKS,
        max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        clock: Any = time.perf_counter,
    ) -> None:
        self._chat_model = chat_model
        self._model_name = model_name or getattr(chat_model, "model", None) or "unknown"
        self._prompt = prompt
        self._parser = parser or PydanticOutputParser(pydantic_object=ProseClaimSet)
        self._max_chunks = max_chunks
        self._max_chunk_chars = max_chunk_chars
        self._clock = clock
        self.chain: Runnable = self._build_chain()

    # -- LCEL ---------------------------------------------------------------

    def _build_chain(self) -> Runnable:
        """``PromptTemplate | ChatModel | text parser | structured parser``."""
        return self._prompt | self._chat_model | StrOutputParser() | self._parser

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def prompt_version(self) -> str:
        return PROSE_EXTRACTION_PROMPT_VERSION

    # -- extraction ---------------------------------------------------------

    def select_chunks(self, text: str) -> list[ProseChunk]:
        """Chunks that would be sent: deterministic, bounded, model not involved."""
        chunks = chunk_prose(text, max_chunk_chars=self._max_chunk_chars)
        return select_provenance_chunks(chunks, max_chunks=self._max_chunks)

    def extract(
        self,
        text: str,
        *,
        source_name: str,
        repository: str | None = None,
        revision: str | None = None,
        source_url: str | None = None,
    ) -> ProseExtractionReport:
        """Extract, validate, and convert claims into Phase 3 evidence items."""
        started = self._clock()
        all_chunks = chunk_prose(text, max_chunk_chars=self._max_chunk_chars)
        selected = select_provenance_chunks(all_chunks, max_chunks=self._max_chunks)

        report = ProseExtractionReport(
            status=ProseExtractionStatus.OK,
            source_name=source_name,
            prompt_version=self.prompt_version,
            prompt_digest=prompt_digest(),
            model=self._model_name,
            chunks_available=len(all_chunks),
        )
        if not selected:
            report.reason = "no prose chunk selected for analysis"
            report.elapsed_seconds = round(self._clock() - started, 4)
            return report

        seen: set[tuple[str, str]] = set()
        for chunk in selected:
            report.chunks_processed += 1
            try:
                parsed = self.chain.invoke({"prose": render_prose_block(chunk.text)})
            except Exception as exc:  # malformed / refused / timeout: fail closed
                report.failures.append(ProseFailure(
                    source_name=source_name,
                    chunk_index=chunk.index,
                    code=ProseFailureCode.MALFORMED_OUTPUT,
                    detail=f"{type(exc).__name__}: {str(exc)[:200]}",
                ))
                continue
            if not isinstance(parsed, ProseClaimSet):  # pragma: no cover - defensive
                report.failures.append(ProseFailure(
                    source_name=source_name,
                    chunk_index=chunk.index,
                    code=ProseFailureCode.MALFORMED_OUTPUT,
                    detail=f"unexpected parsed type {type(parsed).__name__}",
                ))
                continue
            report.claims_reported += len(parsed.claims)
            for claim in parsed.claims:
                self._handle_claim(
                    claim,
                    chunk=chunk,
                    report=report,
                    source_name=source_name,
                    repository=repository,
                    revision=revision,
                    source_url=source_url,
                    seen=seen,
                )

        report.status = _final_status(report)
        report.elapsed_seconds = round(self._clock() - started, 4)
        return report

    def _handle_claim(
        self,
        claim: ProseLineageClaim,
        *,
        chunk: ProseChunk,
        report: ProseExtractionReport,
        source_name: str,
        repository: str | None,
        revision: str | None,
        source_url: str | None,
        seen: set[tuple[str, str]],
    ) -> None:
        validation = validate_claim(claim, chunk=chunk, source_name=source_name)
        if validation.failure is not None:
            report.failures.append(validation.failure)
            return
        if validation.is_no_claim:
            report.no_claim_chunks += 1
            return

        accepted = validation.claim
        key = (
            (accepted.candidate_parent or "").strip().lower(),
            (accepted.evidence_span or "").strip().lower(),
        )
        if key in seen:
            report.failures.append(ProseFailure(
                source_name=source_name,
                chunk_index=chunk.index,
                code=ProseFailureCode.DUPLICATE_CLAIM,
                detail=f"claim already accepted: {accepted.candidate_parent!r}",
                candidate_parent=accepted.candidate_parent,
            ))
            return
        seen.add(key)

        note_parts = [
            f"llm prose claim; prompt=v{PROSE_EXTRACTION_PROMPT_VERSION}",
            f"model={self._model_name}",
            f"claim_status={accepted.claim_status.value}",
            f"rationale={accepted.rationale_code.value}",
        ]
        if validation.relation_downgraded:
            note_parts.append("relation dropped: not stated in the quoted span")
        if validation.resolution_status is not None:
            note_parts.append(f"resolution={validation.resolution_status.value}")
        if accepted.uncertainty_note:
            note_parts.append(f"note={accepted.uncertainty_note}")

        report.evidence.append(build_llm_evidence_item(
            accepted,
            source_name=source_name,
            repository=repository,
            revision=revision,
            source_url=source_url,
            key_path=f"prose[chunk {chunk.index}]",
            note="; ".join(note_parts),
        ))
        report.claims_accepted += 1


def _final_status(report: ProseExtractionReport) -> ProseExtractionStatus:
    malformed = sum(
        1 for f in report.failures if f.code is ProseFailureCode.MALFORMED_OUTPUT
    )
    if report.chunks_processed - malformed <= 0:
        return ProseExtractionStatus.FAILED
    if report.failures:
        return ProseExtractionStatus.PARTIAL
    return ProseExtractionStatus.OK


def unavailable_report(
    source_name: str,
    reason: str,
    *,
    model: str | None = None,
) -> ProseExtractionReport:
    """Report an unusable LLM runtime without raising or inventing evidence."""
    return ProseExtractionReport(
        status=ProseExtractionStatus.UNAVAILABLE,
        source_name=source_name,
        prompt_version=PROSE_EXTRACTION_PROMPT_VERSION,
        prompt_digest=prompt_digest(),
        model=model,
        reason=reason,
    )
