"""Strict schema for LLM-extracted prose lineage claims.

The model answers one narrow question per chunk: *does this repository prose
explicitly state a direct lineage claim, and if so which parent and which
relation?* It is never asked whether metadata should change.

Design rules encoded here:

* ``NO_CLAIM`` is a first-class, valid answer - not a malformed empty result.
* Only the four canonical relations exist; any other label fails validation.
* Unknown extra fields are rejected, so a chatty model cannot smuggle in
  fields (or free-form reasoning) that the pipeline would have to interpret.
* No chain-of-thought: explanations are short deterministic codes plus an
  optional brief ``uncertainty_note``, never step-by-step reasoning.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from ..schemas.lineage import Relation

__all__ = [
    "ClaimStatus",
    "RationaleCode",
    "ProseLineageClaim",
    "ProseClaimSet",
    "ProseFailureCode",
    "ProseExtractionStatus",
    "ProseFailure",
    "ProseExtractionReport",
    "MAX_UNCERTAINTY_NOTE_CHARS",
    "llm_evidence_reliability",
]

MAX_UNCERTAINTY_NOTE_CHARS = 200

# An LLM-extracted prose claim is author-controlled documentation evidence.
# Extraction by a model does not raise the authority of the source text: prose
# can never outrank a tool-generated artifact (adapter/training/merge config).
LLM_PROSE_RELIABILITY: Reliability = Reliability.MEDIUM


def llm_evidence_reliability() -> Reliability:
    """Reliability assigned to validated LLM prose evidence (capped)."""
    return LLM_PROSE_RELIABILITY


class ClaimStatus(str, Enum):
    """What the model found in the supplied prose."""

    EXPLICIT = "explicit"    # a direct parent (and relation) is clearly stated
    NO_CLAIM = "no_claim"    # the prose contains no direct lineage statement
    AMBIGUOUS = "ambiguous"  # lineage-like wording, but not a precise parent


class RationaleCode(str, Enum):
    """Deterministic explanation codes (never free-form reasoning)."""

    EXPLICIT_FINETUNE_PHRASE = "EXPLICIT_FINETUNE_PHRASE"
    EXPLICIT_ADAPTER_PHRASE = "EXPLICIT_ADAPTER_PHRASE"
    EXPLICIT_MERGE_PHRASE = "EXPLICIT_MERGE_PHRASE"
    EXPLICIT_QUANTIZED_PHRASE = "EXPLICIT_QUANTIZED_PHRASE"
    EXPLICIT_PARENT_PHRASE = "EXPLICIT_PARENT_PHRASE"
    PARENT_MENTION_WITHOUT_RELATION = "PARENT_MENTION_WITHOUT_RELATION"
    AMBIGUOUS_UNSPECIFIED_VERSION = "AMBIGUOUS_UNSPECIFIED_VERSION"
    AMBIGUOUS_UNRESOLVED_PARENT = "AMBIGUOUS_UNRESOLVED_PARENT"
    NO_DIRECT_LINEAGE_CLAIM = "NO_DIRECT_LINEAGE_CLAIM"


class ProseLineageClaim(BaseModel):
    """One extracted claim. Extra fields are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_parent: str | None = None
    relation: Relation | None = None
    claim_status: ClaimStatus
    evidence_span: str | None = None
    rationale_code: RationaleCode
    uncertainty_note: str | None = Field(default=None, max_length=MAX_UNCERTAINTY_NOTE_CHARS)

    @model_validator(mode="after")
    def _check_claim_shape(self) -> ProseLineageClaim:
        if self.claim_status is ClaimStatus.NO_CLAIM:
            forbidden = [
                name for name, value in (
                    ("candidate_parent", self.candidate_parent),
                    ("relation", self.relation),
                    ("evidence_span", self.evidence_span),
                ) if value is not None
            ]
            if forbidden:
                raise ValueError(
                    f"NO_CLAIM must not carry {', '.join(forbidden)}"
                )
            return self
        if not self.candidate_parent:
            raise ValueError(
                f"{self.claim_status.value} claim requires a candidate_parent"
            )
        if not self.evidence_span:
            raise ValueError(
                f"{self.claim_status.value} claim requires an evidence_span"
            )
        return self


class ProseClaimSet(BaseModel):
    """The JSON object the model must return for one prose chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claims: list[ProseLineageClaim] = Field(default_factory=list)


class ProseFailureCode(str, Enum):
    """Why a chunk or claim was not turned into evidence."""

    MALFORMED_OUTPUT = "malformed_output"      # unparsable / schema-invalid JSON
    SPAN_NOT_FOUND = "span_not_found"          # quoted span absent from the prose
    PARENT_NOT_IN_SOURCE = "parent_not_in_source"  # invented parent identifier
    INVALID_MODEL_ID = "invalid_model_id"      # not a model reference at all
    DUPLICATE_CLAIM = "duplicate_claim"        # already accepted from another chunk


class ProseExtractionStatus(str, Enum):
    OK = "OK"                    # at least one chunk parsed cleanly
    PARTIAL = "PARTIAL"          # some chunks parsed, some failed
    FAILED = "FAILED"            # every processed chunk failed
    UNAVAILABLE = "UNAVAILABLE"  # LLM runtime/dependency not usable


class ProseFailure(BaseModel):
    """A structural extraction failure (never an exception to the caller)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: str
    chunk_index: int
    code: ProseFailureCode
    detail: str
    candidate_parent: str | None = None


class ProseExtractionReport(BaseModel):
    """Run metadata plus validated evidence for one prose source.

    ``elapsed_seconds`` is operational metadata and is intentionally *not*
    part of any :class:`EvidenceItem`, so evidence stays comparable.
    """

    model_config = ConfigDict(extra="forbid")

    status: ProseExtractionStatus
    source_name: str
    prompt_version: str
    prompt_digest: str
    model: str | None = None
    reason: str | None = None
    chunks_available: int = 0
    chunks_processed: int = 0
    claims_reported: int = 0
    claims_accepted: int = 0
    no_claim_chunks: int = 0
    failures: list[ProseFailure] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    elapsed_seconds: float | None = None

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)

    def summary(self) -> str:
        """Concise status line suitable for an audit report."""
        if self.status is ProseExtractionStatus.UNAVAILABLE:
            return f"LLM prose extraction unavailable: {self.reason}"
        if self.status is ProseExtractionStatus.FAILED:
            return f"LLM prose extraction failed: {self.reason}"
        return (
            f"LLM prose extraction {self.status.value}: {self.chunks_processed} chunk(s), "
            f"{self.claims_accepted} accepted claim(s), {len(self.failures)} failure(s) "
            f"[prompt {self.prompt_version}, model {self.model}]"
        )


def build_llm_evidence_item(
    claim: ProseLineageClaim,
    *,
    source_name: str,
    repository: str | None = None,
    revision: str | None = None,
    source_url: str | None = None,
    key_path: str,
    note: str,
) -> EvidenceItem:
    """Convert a validated claim into the existing Phase 3 evidence schema.

    Role stays ``INDEPENDENT`` (prose is compared against declared metadata),
    extraction method is ``LLM``, reliability is capped at author-controlled
    prose level, and explicitness follows the model's own claim status.
    """
    return EvidenceItem(
        source_type=SourceType.README,
        role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.LLM,
        reliability=llm_evidence_reliability(),
        source_name=source_name,
        repository=repository,
        revision=revision,
        candidate_parent=claim.candidate_parent,
        relation=claim.relation,
        raw_value=claim.candidate_parent,
        evidence_span=claim.evidence_span,
        key_path=key_path,
        explicitness=(
            Explicitness.IMPLICIT
            if claim.claim_status is ClaimStatus.AMBIGUOUS
            else Explicitness.EXPLICIT
        ),
        source_url=source_url,
        note=note,
    )
