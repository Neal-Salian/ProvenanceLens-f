"""LineageRepairBench: reproducible, offline evaluation of ProvenanceLens.

The benchmark keeps synthetic (CONTROLLED) and manually adjudicated (REAL)
labels separate, validates itself before use, and scores repairs with an
explicit false-repair definition. ``support_score`` is a heuristic evidence
strength throughout: no metric in this package treats it as a calibrated
probability.
"""

from .controlled import CONTROLLED_CASES, build_controlled_benchmark
from .ablations import ABLATIONS, ABLATION_NAMES, ablation_table, run_ablations
from .dataset import (
    benchmark_summary,
    load_benchmark,
    load_controlled_benchmark,
    load_real_benchmark,
    validation_report,
)
from .acquisition import (
    STRATA,
    AcquisitionReport,
    CandidateRecord,
    acquire_real_snapshots,
)
from .phase_g import (
    ablation_effects,
    evidence_usage,
    failure_analysis,
    headline_metrics,
    run_phase_g,
    selective_risk_curve,
    stratified_results,
    wilson_interval,
)
from .report import build_manifest, report_digest, write_phase_g_report
from .real import (
    ADJUDICATOR,
    ADJUDICATION_FILE,
    PRECEDENCE,
    adjudication_summary,
    load_adjudication_file,
)
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
    "ABLATIONS",
    "ABLATION_NAMES",
    "ADJUDICATOR",
    "ADJUDICATION_FILE",
    "BENCHMARK_VERSION",
    "CONTROLLED_CASES",
    "PRECEDENCE",
    "STRATA",
    "AcquisitionReport",
    "CandidateRecord",
    "ablation_effects",
    "ablation_table",
    "acquire_real_snapshots",
    "build_manifest",
    "adjudication_summary",
    "evidence_usage",
    "failure_analysis",
    "headline_metrics",
    "load_adjudication_file",
    "report_digest",
    "run_ablations",
    "run_phase_g",
    "selective_risk_curve",
    "stratified_results",
    "wilson_interval",
    "write_phase_g_report",
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
