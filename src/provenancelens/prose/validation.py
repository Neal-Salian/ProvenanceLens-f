"""Deterministic validation of LLM prose claims against the source text.

This module is the fail-closed boundary. A claim survives only if every check
below passes, each of them anchored in the repository text:

1. **Shape** - the parser already enforced the schema (status/parent/span
   coherence, canonical relation vocabulary, no extra fields).
2. **Span exists** - ``evidence_span`` must be a substring of the chunk that
   was actually sent, allowing only whitespace/case differences. Fabricated
   citations are rejected; no fuzzy or semantic matching is used.
3. **Parent is in the span** - the parent identifier must occur inside the
   quoted span, so a claim cannot borrow a span from one sentence and a parent
   from another (or from the model's memory).
4. **Model id validation** - the parent goes through the Phase D resolver.
   Values that are not model references at all are rejected; bare names stay
   unresolved on purpose and are never repaired into a canonical id.
5. **Relation corroboration** - a stated relation must have a matching cue in
   the span. An unsupported relation is downgraded to ``None`` (never invented
   and never silently accepted), with a deterministic rationale code.
6. **Duplicates** - identical (parent, span) pairs are counted once.

Rejections are recorded structurally as :class:`ProseFailure`; they never
raise into the audit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..resolution import ResolutionStatus, resolve_identifier
from ..schemas.lineage import Relation
from .chunking import ProseChunk
from .schema import (
    ClaimStatus,
    ProseFailure,
    ProseFailureCode,
    ProseLineageClaim,
    RationaleCode,
)

__all__ = [
    "RELATION_CUES",
    "LINEAGE_CUES",
    "NON_LINEAGE_CUES",
    "INJECTION_PATTERNS",
    "ClaimValidation",
    "span_occurs_in",
    "looks_like_injection",
    "states_lineage",
    "validate_claim",
]

#: Lexical cues that make a span a *lineage statement* rather than a mention.
#: An EXPLICIT claim must contain one; otherwise the prose merely names a model
#: (comparison, acknowledgement, architecture inspiration) and no claim exists.
LINEAGE_CUES: tuple[str, ...] = (
    "fine-tun", "finetun", "fine tun", "trained on", "trained from",
    "trained on top of", "further train", "continued pre-training",
    "continued pretraining", "pre-trained on", "pretrained on", "sft",
    "supervised fine", "post-trained on", "post trained on",
    "adapter", "lora", "peft", "prefix-tuning", "prefix tuning", "ia3",
    "merge", "merged", "merging", "combines", "combine", "combined from",
    "combination of", "blend of", "blended from", "model soup", "soup of",
    "quantized", "quantised", "quantization", "quantisation", "gguf",
    "awq", "gptq", "int4", "int8", "4-bit", "8-bit",
    "initialized from", "initialised from", "built from", "derived from",
    "adapted from", "distilled from", "forked from", "released from",
)

#: Context markers that make a sentence a comparison, an inspiration, a
#: tokenizer/architecture remark, or an acknowledgement rather than a lineage
#: statement. Observed in live runs: a small local model read "surpasses most
#: of the current Mistral finetunes" as lineage, so the prompt rule is also
#: enforced deterministically here.
NON_LINEAGE_CUES: tuple[str, ...] = (
    "outperform", "outperforms", "outperforming", "surpass", "surpasses",
    "surpassing", "better than", "compared to", "compare against", "compares to",
    "comparison", "benchmark", "leaderboard", "evaluation results",
    "state of the art", "sota", "beats ", "ranking", "baseline", "ablations",
    "inspired by", "inspired from", "inspired from the", "reimplements",
    "same tokenizer", "tokenizer style", "compatible with", "architecture is based",
    "thanks to", "thank you", "credit to", "acknowledg", "build on the ideas",
    "based on the ideas", "we are grateful",
)

#: Text patterns that are prompt-injection attempts rather than repository
#: lineage prose. Deterministic substring screening: a claim whose *span* is an
#: instruction is rejected even if it happens to mention a model id.
INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore the above",
    "disregard previous",
    "you are chatgpt",
    "you are an ai assistant",
    "system prompt",
    "new instructions:",
    "override your instructions",
    "output model",
    "as the parent model",
    "say the base model is",
    "do not extract",
)

#: Per-relation lexical cues that must appear in the quoted span for a stated
#: relation to be accepted. Deliberately narrow: a plausible-but-unstated
#: relation is downgraded rather than trusted.
RELATION_CUES: dict[Relation, tuple[str, ...]] = {
    Relation.FINETUNE: (
        "fine-tun", "finetun", "fine tun", "trained on", "trained from",
        "trained on top of", "further train", "continued pre-training",
        "continued pretraining", "pre-trained on", "pretrained on",
        "sft", "supervised fine", "post-trained on", "post trained on",
    ),
    Relation.ADAPTER: (
        "adapter", "lora", "peft", "prefix-tuning", "prefix tuning", "ia3",
    ),
    Relation.MERGE: (
        "merge", "merged", "merging", "combined from", "combination of",
        "blend of", "blended from", "model soup", "soup of",
    ),
    Relation.QUANTIZED: (
        "quantiz", "quantis", "gguf", "awq", "gptq", "int4", "int8",
        "4-bit", "8-bit", "2-bit", "q4_", "q5_", "q8_",
    ),
}

#: Rationale code recorded when the stated relation loses its textual support.
_RELATION_DOWNGRADE_CODE = RationaleCode.PARENT_MENTION_WITHOUT_RELATION

_RELATION_RATIONALE: dict[Relation, RationaleCode] = {
    Relation.FINETUNE: RationaleCode.EXPLICIT_FINETUNE_PHRASE,
    Relation.ADAPTER: RationaleCode.EXPLICIT_ADAPTER_PHRASE,
    Relation.MERGE: RationaleCode.EXPLICIT_MERGE_PHRASE,
    Relation.QUANTIZED: RationaleCode.EXPLICIT_QUANTIZED_PHRASE,
}


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def span_occurs_in(span: str, haystack: str) -> bool:
    """True when ``span`` is literally present in ``haystack``.

    Exact substring first; the only leniency is collapsing whitespace and
    case, which cannot manufacture a citation that is not in the source.
    """
    if not span or not haystack:
        return False
    if span in haystack:
        return True
    return _normalize_whitespace(span) in _normalize_whitespace(haystack)


def _relation_is_corroborated(relation: Relation, span: str) -> bool:
    lowered = span.lower()
    return any(cue in lowered for cue in RELATION_CUES.get(relation, ()))


def states_lineage(span: str) -> bool:
    """True when the span reads as a lineage statement, not a mere mention."""
    lowered = span.lower()
    return any(cue in lowered for cue in LINEAGE_CUES)


def looks_like_injection(span: str) -> bool:
    """True when the span is (or contains) an instruction aimed at the model."""
    lowered = span.lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)


def has_non_lineage_context(span: str) -> bool:
    """True when the span reads as comparison, inspiration, or an acknowledgement."""
    lowered = span.lower()
    return any(marker in lowered for marker in NON_LINEAGE_CUES)


@dataclass(frozen=True)
class ClaimValidation:
    """Outcome of validating one claim against its source chunk."""

    claim: ProseLineageClaim
    accepted: bool
    is_no_claim: bool = False
    relation_downgraded: bool = False
    resolution_status: ResolutionStatus | None = None
    failure: ProseFailure | None = None

    @property
    def outcome(self) -> str:
        if self.failure is not None:
            return "rejected"
        return "no_claim" if self.is_no_claim else "accepted"


def validate_claim(
    claim: ProseLineageClaim,
    *,
    chunk: ProseChunk,
    source_name: str,
) -> ClaimValidation:
    """Validate one parsed claim against the chunk it was produced from."""
    if claim.claim_status is ClaimStatus.NO_CLAIM:
        return ClaimValidation(claim=claim, accepted=False, is_no_claim=True)

    def reject(code: ProseFailureCode, detail: str) -> ClaimValidation:
        return ClaimValidation(
            claim=claim,
            accepted=False,
            failure=ProseFailure(
                source_name=source_name,
                chunk_index=chunk.index,
                code=code,
                detail=detail,
                candidate_parent=claim.candidate_parent,
            ),
        )

    span = claim.evidence_span or ""
    if looks_like_injection(span):
        # Fail closed: untrusted text cannot instruct the extractor, and a span
        # that is an instruction is not a lineage statement.
        return reject(
            ProseFailureCode.INJECTION_DETECTED,
            "quoted span looks like a prompt-injection instruction, not a lineage claim",
        )
    if not span_occurs_in(span, chunk.text):
        return reject(
            ProseFailureCode.SPAN_NOT_FOUND,
            "quoted evidence span does not occur in the supplied prose",
        )
    if claim.claim_status is ClaimStatus.EXPLICIT and not states_lineage(span):
        return reject(
            ProseFailureCode.LINEAGE_NOT_STATED,
            "quoted span names a model but does not state a lineage relationship",
        )
    if claim.claim_status is ClaimStatus.EXPLICIT and has_non_lineage_context(span):
        return reject(
            ProseFailureCode.NON_LINEAGE_CONTEXT,
            "quoted span is a comparison, inspiration, or acknowledgement, not lineage",
        )

    parent = (claim.candidate_parent or "").strip()
    if not span_occurs_in(parent, span):
        return reject(
            ProseFailureCode.PARENT_NOT_IN_SOURCE,
            f"candidate parent {parent!r} does not occur in the quoted span",
        )

    resolution = resolve_identifier(parent)
    if resolution.status is ResolutionStatus.INVALID:
        return reject(
            ProseFailureCode.INVALID_MODEL_ID,
            f"candidate parent {parent!r} is not a model reference ({resolution.reason})",
        )

    downgraded = False
    validated = claim
    if claim.relation is not None and not _relation_is_corroborated(claim.relation, span):
        # The parent may be explicit while the relation is not stated: keep the
        # parent, drop the unsupported relation, and record why.
        validated = claim.model_copy(update={
            "relation": None,
            "rationale_code": _RELATION_DOWNGRADE_CODE,
        })
        downgraded = True

    if (
        validated.relation is None
        and validated.rationale_code not in (*_RELATION_RATIONALE.values(),)
    ):
        validated = validated.model_copy(update={
            "rationale_code": _RELATION_DOWNGRADE_CODE,
        })

    return ClaimValidation(
        claim=validated,
        accepted=True,
        relation_downgraded=downgraded,
        resolution_status=resolution.status,
    )
