"""Phase D evidence reasoning: candidates, fusion, conflicts, decisions.

:mod:`provenancelens.reasoning.legacy` (Phase 2 regression baseline) is kept
untouched; the modules below implement the separate Phase D engine.
"""

from .candidates import (
    CandidateHypothesis,
    CandidateMethod,
    CandidateSet,
    ControlDomain,
    EvidenceCluster,
    aggregate_candidates,
)
from .conflicts import (
    DeclaredComparison,
    compare_declared_lineage,
    detect_conflicts,
    is_competing,
)
from .decision import DecisionResult, decide_lineage
from .fusion import (
    DEFAULT_POLICY,
    ITEM_WEIGHTS,
    DecisionPolicy,
    LineagePlan,
    SupportAssessment,
    compute_support,
)

__all__ = [
    "DEFAULT_POLICY",
    "ITEM_WEIGHTS",
    "CandidateHypothesis",
    "CandidateMethod",
    "CandidateSet",
    "ControlDomain",
    "DeclaredComparison",
    "DecisionPolicy",
    "DecisionResult",
    "EvidenceCluster",
    "LineagePlan",
    "SupportAssessment",
    "aggregate_candidates",
    "compare_declared_lineage",
    "compute_support",
    "decide_lineage",
    "detect_conflicts",
    "is_competing",
]
