"""LineageRepairBench assembly: the two tracks, kept separate.

``load_benchmark`` never merges synthetic and adjudicated labels into one
undifferentiated pool: every case carries its ``track`` and label provenance, so
metrics can always be reported per track and a reader can tell synthetic
construction from manual adjudication.
"""

from __future__ import annotations

from pathlib import Path

from .controlled import build_controlled_benchmark
from .real import load_real_benchmark
from .schema import BENCHMARK_VERSION, BenchmarkCase, Track
from .validation import ValidationIssue, assert_valid_benchmark, validate_benchmark

__all__ = [
    "BENCHMARK_VERSION",
    "load_benchmark",
    "load_controlled_benchmark",
    "load_real_benchmark",
    "benchmark_summary",
    "BenchmarkCase",
    "Track",
]


def load_controlled_benchmark() -> list[BenchmarkCase]:
    return build_controlled_benchmark()


def load_benchmark(
    track: Track | str | None = None, *, root: Path | None = None,
    validate: bool = True,
) -> list[BenchmarkCase]:
    """Load a benchmark track (default: both), validating unless told otherwise."""
    wanted = Track(track) if track is not None else None
    cases: list[BenchmarkCase] = []
    if wanted in (None, Track.CONTROLLED):
        cases.extend(build_controlled_benchmark())
    if wanted in (None, Track.REAL):
        cases.extend(load_real_benchmark(root))
    if validate:
        assert_valid_benchmark(cases)
    return cases


def benchmark_summary(cases: list[BenchmarkCase]) -> dict[str, object]:
    """Counts and label provenance, for reports."""
    by_track: dict[str, int] = {}
    by_action: dict[str, int] = {}
    by_state: dict[str, int] = {}
    provenance: dict[str, int] = {}
    ambiguous = 0
    for case in cases:
        by_track[case.track.value] = by_track.get(case.track.value, 0) + 1
        by_action[case.expected_action.value] = by_action.get(case.expected_action.value, 0) + 1
        state = case.truth.metadata_state.value
        by_state[state] = by_state.get(state, 0) + 1
        source = case.adjudication.provenance.value
        provenance[source] = provenance.get(source, 0) + 1
        if case.truth.parents_status.value != "known":
            ambiguous += 1
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "n_cases": len(cases),
        "by_track": by_track,
        "by_expected_action": by_action,
        "by_metadata_state": by_state,
        "by_label_provenance": provenance,
        "non_known_parent_truth": ambiguous,
    }


def validation_report(cases: list[BenchmarkCase]) -> list[ValidationIssue]:
    return validate_benchmark(cases)
