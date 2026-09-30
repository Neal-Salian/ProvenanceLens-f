"""LineageRepairBench: reproducible, offline evaluation of ProvenanceLens.

The benchmark keeps synthetic (CONTROLLED) and manually adjudicated (REAL)
labels separate, validates itself before use, and scores repairs with an
explicit false-repair definition. ``support_score`` is a heuristic evidence
strength throughout: no metric in this package treats it as a calibrated
probability.
"""

from .controlled import CONTROLLED_CASES, build_controlled_benchmark
from .dataset import (
    benchmark_summary,
    load_benchmark,
    load_controlled_benchmark,
    load_real_benchmark,
    validation_report,
)
from .real import REAL_CASE_SPECS
from .schema import (
    BENCHMARK_VERSION,
    Adjudication,
    BenchmarkCase,
    BenchmarkRun,
    CaseResult,
    ClassificationMetrics,
    CountMetric,
    GroundTruth,
    LabelProvenance,
    MetadataState,
    RepairSafetyMetrics,
    Track,
    TrackMetrics,
    TruthStatus,
)
from .validation import (
    BenchmarkValidationError,
    Severity,
    ValidationIssue,
    assert_valid_benchmark,
    validate_benchmark,
    validate_case,
)

__all__ = [
    "BENCHMARK_VERSION",
    "CONTROLLED_CASES",
    "REAL_CASE_SPECS",
    "Adjudication",
    "BenchmarkCase",
    "BenchmarkRun",
    "BenchmarkValidationError",
    "CaseResult",
    "ClassificationMetrics",
    "CountMetric",
    "GroundTruth",
    "LabelProvenance",
    "MetadataState",
    "RepairSafetyMetrics",
    "Severity",
    "Track",
    "TrackMetrics",
    "TruthStatus",
    "ValidationIssue",
    "assert_valid_benchmark",
    "benchmark_summary",
    "build_controlled_benchmark",
    "load_benchmark",
    "load_controlled_benchmark",
    "load_real_benchmark",
    "validate_benchmark",
    "validate_case",
    "validation_report",
]
