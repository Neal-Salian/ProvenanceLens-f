"""Phase E run outcome: LLM status plus the Phase D decision it fed.

Kept in the prose package (not in the reasoning/pipeline modules) so the
deterministic core never imports the optional Phase E dependencies, and so
the Phase D schemas stay untouched: every decision is still produced by the
Phase D engine.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..schemas.audit import AuditDecision
from .schema import ProseExtractionReport

__all__ = ["ProseExtractionOutcome"]


class ProseExtractionOutcome(BaseModel):
    """Deterministic-only decision, prose report, and the combined decision."""

    model_config = ConfigDict(extra="forbid")

    report: ProseExtractionReport
    decision: AuditDecision
    deterministic_decision: str
    decision_changed: bool

    @property
    def llm_evidence_count(self) -> int:
        return len(self.report.evidence)

    @property
    def mode(self) -> str:
        return "deterministic+llm" if self.report.evidence else "deterministic-only"
