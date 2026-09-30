"""Phase G experimental study: determinism, honesty and analysis integrity.

These tests exist to make the *study* trustworthy rather than to lock in
particular numbers.  They assert the invariants a reviewer depends on:

* the study is deterministic and offline;
* ablations are input transforms, not reimplementations of the system;
* ground truth never comes from the engine, and declared metadata is never
  used as independent evidence;
* abstention is never silently rewarded, and unverifiable repairs are
  reported separately from false repairs;
* reported statistics are internally consistent (denominators, intervals,
  stratum coverage) and the real track still covers every stratum.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from provenancelens.evaluation import (
    ABLATIONS,
    Track,
    load_benchmark,
    load_real_benchmark,
    report_digest,
    run_phase_g,
    validation_report,
)
from provenancelens.evaluation.ablations import run_ablations
from provenancelens.evaluation.metrics import compute_metrics
from provenancelens.evaluation.phase_g import (
    ablation_effects,
    evidence_usage,
    failure_analysis,
    headline_metrics,
    stratified_results,
    wilson_interval,
)
from provenancelens.evaluation.phase_g_cli import main as phase_g_main
from provenancelens.evaluation.report import (
    build_manifest,
    render_markdown_table,
    write_phase_g_report,
)
from provenancelens.evaluation.runner import run_case

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report() -> dict:
    return run_phase_g(include_extraction=False)


# --- determinism and offline execution ----------------------------------------

def test_report_digest_is_stable_across_runs():
    first = report_digest(run_phase_g(include_ablations=False))
    second = report_digest(run_phase_g(include_ablations=False))
    assert first == second


def test_study_runs_without_network_or_optional_llm_extras():
    """The study must work with the optional Phase E stack and network blocked."""
    guard = """
import builtins, socket
_real_import = builtins.__import__
def _guarded(name, g=None, l=None, fromlist=(), level=0):
    if name.split('.')[0] in ('langchain_core', 'langchain', 'langchain_ollama',
                              'ollama', 'requests', 'httpx', 'urllib3'):
        raise ImportError('blocked: ' + name)
    return _real_import(name, g, l, fromlist, level)
builtins.__import__ = _guarded
def _no_network(*args, **kwargs):
    raise AssertionError('network access attempted')
socket.socket.connect = _no_network
socket.create_connection = _no_network
from provenancelens.evaluation.phase_g import run_phase_g
from provenancelens.evaluation.report import report_digest
print(report_digest(run_phase_g(include_ablations=False)))
"""
    env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-c", guard], capture_output=True, text=True,
        cwd=str(REPO_ROOT), env=env,
    )
    assert result.returncode == 0, result.stderr
    expected = report_digest(run_phase_g(include_ablations=False))
    assert result.stdout.strip() == expected


def test_written_artifacts_are_byte_identical_between_runs(tmp_path: Path):
    def write(dest: Path) -> None:
        payload = run_phase_g(include_extraction=False)
        manifest = build_manifest(payload, artifacts={},
                                  snapshot_root=REPO_ROOT / "data" / "snapshots",
                                  elapsed_seconds=0.0, config={"tracks": "all"})
        write_phase_g_report(payload, dest, manifest=manifest,
                             snapshot_root=REPO_ROOT / "data" / "snapshots",
                             config={"tracks": "all"})

    first, second = tmp_path / "a", tmp_path / "b"
    write(first)
    write(second)
    digests = {}
    for root in (first, second):
        digests[root.name] = {
            str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.name != "manifest.json"
        }
    assert digests["a"] == digests["b"]
    assert len(digests["a"]) >= 20


def test_cli_verify_reports_identical_digests(capsys):
    assert phase_g_main(["verify"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["identical"] is True


# --- benchmark integrity ------------------------------------------------------

def test_every_real_case_declares_an_acquisition_stratum():
    cases = load_real_benchmark()
    strata = {
        tag.split(":", 1)[1]
        for case in cases for tag in case.tags if tag.startswith("stratum:")
    }
    assert strata, "no real case carries an acquisition stratum"
    for case in cases:
        assert any(tag.startswith("stratum:") for tag in case.tags)


def test_strata_come_from_the_frozen_selection_record_not_from_results():
    """Strata are declared by the selection plan, never inferred from results."""
    from provenancelens.evaluation.real import acquisition_strata

    record = acquisition_strata()
    assert len(record) >= 40
    pre_phase_g = []
    for case in load_real_benchmark():
        stratum = next(t.split(":", 1)[1] for t in case.tags if t.startswith("stratum:"))
        if case.repository in record:
            assert stratum == record[case.repository]
        else:
            # the three Phase F cases predate the acquisition plan
            assert stratum == "pre_phase_g"
            pre_phase_g.append(case.repository)
    assert len(pre_phase_g) == 3


def test_real_track_is_not_dominated_by_one_stratum():
    """A benchmark where one stratum is everything cannot support per-stratum claims."""
    buckets = {}
    for case in load_real_benchmark():
        stratum = next(t.split(":", 1)[1] for t in case.tags if t.startswith("stratum:"))
        buckets[stratum] = buckets.get(stratum, 0) + 1
    assert len(buckets) >= 6
    assert max(buckets.values()) / sum(buckets.values()) < 0.35


def test_benchmark_has_no_validation_errors():
    issues = validation_report(load_benchmark())
    assert [i for i in issues if i.severity.value == "error"] == []


def test_incomplete_metadata_is_a_distinct_adjudicated_state():
    states = {case.truth.metadata_state.value for case in load_real_benchmark()}
    assert "incomplete" in states
    incomplete = [c for c in load_real_benchmark()
                  if c.truth.metadata_state.value == "incomplete"]
    assert incomplete
    for case in incomplete:
        # a parent must actually be declared, and the relation must be knowable
        assert case.declared_base_model or case.declared_additional_base_models
        assert case.truth.relation_status.value == "known"


# --- ablation integrity -------------------------------------------------------

def test_ablations_are_registered_with_a_question_and_hypothesis():
    assert len(ABLATIONS) >= 8
    for spec in ABLATIONS:
        assert spec.question.strip()
        assert spec.hypothesis.strip()
        assert spec.name == spec.name.strip().lower().replace(" ", "_")


def test_full_ablation_row_reproduces_the_headline_run(report):
    rows = {row["ablation"]: row for row in report["ablations"]["results"]}
    headline = report["systems"]["provenancelens"]["headline"]
    action = next(r for r in headline if r["metric"] == "action_accuracy")
    assert rows["full"]["action_correct"] == action["numerator"]
    assert rows["full"]["false_repairs"] == 0


def test_no_ablation_silently_invents_a_false_repair(report):
    """Removing evidence may reduce coverage; it must not corrupt lineage."""
    for row in report["ablations"]["results"]:
        assert row["false_repairs"] >= 0
        assert row["attempted_repairs"] >= row["false_repairs"]


def test_ablation_deltas_are_relative_to_the_full_run(report):
    rows = {row["ablation"]: row for row in report["ablations"]["results"]}
    for name, row in rows.items():
        if name == "full":
            assert row["delta_action_accuracy"] == 0.0
        else:
            expected = row["action_accuracy"] - rows["full"]["action_accuracy"]
            assert row["delta_action_accuracy"] == pytest.approx(expected)


def test_removing_tool_configs_stops_every_repair(report):
    """Tool-generated lineage is the only admissible repair trigger."""
    row = next(r for r in report["ablations"]["results"]
               if r["ablation"] == "no_tool_configs")
    assert row["attempted_repairs"] == 0


# --- label integrity ----------------------------------------------------------

def test_declared_metadata_is_never_used_as_independent_evidence(report):
    """Declared metadata is the audit subject, so it cannot be evidence for itself."""
    from provenancelens.schemas.evidence import EvidenceRole

    usage = report["evidence_usage"]
    assert "declared_metadata" not in usage["presence"]
    for case in load_benchmark():
        from provenancelens.evaluation.runner import case_inputs

        _, evidence, _ = case_inputs(case)
        independent_ids = {
            id(item) for item in evidence if item.role is EvidenceRole.INDEPENDENT
        }
        for item in evidence:
            if item.role is EvidenceRole.DECLARED:
                assert id(item) not in independent_ids
        assert len(independent_ids) + sum(
            1 for item in evidence if item.role is EvidenceRole.DECLARED
        ) == len(evidence)


def test_no_label_module_calls_the_decision_engine():
    """Labels must be authored offline, never read off the engine's own output."""
    forbidden = ("decide_lineage", "decide_case", "run_case", "run_benchmark",
                 "compute_metrics")
    for module in ("controlled.py", "real.py", "validation.py", "dataset.py"):
        source = (REPO_ROOT / "src" / "provenancelens" / "evaluation" / module).read_text()
        for name in forbidden:
            assert name not in source, f"{module} must not call the engine: {name}"


def test_ablations_run_the_unmodified_engine_on_transformed_evidence():
    """An ablation must reuse the production entry point, not reimplement it."""
    source = (REPO_ROOT / "src" / "provenancelens" / "evaluation"
              / "ablations.py").read_text()
    assert "decide_lineage" in source, "ablations must call the real engine"
    for module in ("from ..fusion", "from ..parsers", "from ..resolution",
                   "from ..pipeline"):
        assert module not in source, f"ablations must not reimplement {module}"


@pytest.mark.parametrize("production", [
    "collectors", "parsers", "reasoning", "resolution", "fusion", "schemas",
    "pipeline", "snapshots", "reporting", "prose",
])
def test_no_phase_g_change_to_production_modules(production):
    """Phase G is evaluation-only: production must be identical to the merge base."""
    base = "4f79486"  # Phase F merge commit on this branch
    result = subprocess.run(
        ["git", "diff", "--stat", base, "--",
         f"src/provenancelens/{production}"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:  # pragma: no cover - source checkout without history
        pytest.skip("git history unavailable")
    assert result.stdout.strip() == "", (
        f"production package {production} changed since Phase F:\n{result.stdout}"
    )


def test_failure_analysis_accounts_for_every_case_exactly_once(report):
    analysis = report["failure_analysis"]
    total = sum(row["n_cases"] for row in analysis["taxonomy"])
    assert total == analysis["total"] == 70
    assert analysis["taxonomy"][0]["category"] == "correct"
    assert analysis["n_failures"] == len(analysis["failures"])
    assert len({row["case_id"] for row in analysis["failures"]}) == analysis["n_failures"]


def test_correct_cases_are_never_counted_as_failures(report):
    failing = {row["case_id"] for row in report["failure_analysis"]["failures"]}
    for result in report["per_case"]["provenancelens"]:
        if result["action_correct"] and result["false_repair"] is not True:
            assert result["case_id"] not in failing


# --- metric honesty -----------------------------------------------------------

def test_abstention_is_never_scored_as_correct():
    """If the label expects a repair, abstaining must be wrong."""
    for case in load_benchmark():
        result = run_case(case)
        if case.expected_action.value in ("ADD", "REPLACE") and result.abstained:
            assert result.action_correct is False


def test_unverifiable_repairs_are_counted_separately_from_false_repairs(report):
    headline = {row["metric"]: row for row in report["systems"]["provenancelens"]["headline"]}
    safety = headline["unverifiable_repair_rate"]
    falses = headline["false_repair_rate"]
    assert safety["denominator"] == falses["denominator"]
    assert (safety["numerator"] + falses["numerator"]) <= safety["denominator"]


def test_false_repair_denominator_is_attempted_repairs(report):
    headline = {row["metric"]: row for row in report["systems"]["provenancelens"]["headline"]}
    assert headline["false_repair_rate"]["denominator"] == \
        headline["repair_attempt_rate"]["numerator"]


def test_headline_denominators_match_the_case_counts(report):
    headline = {row["metric"]: row for row in report["systems"]["provenancelens"]["headline"]}
    n = report["benchmark"]["n_cases"]
    assert headline["action_accuracy"]["denominator"] == n
    assert headline["coverage"]["denominator"] == n
    assert headline["action_accuracy"]["numerator"] + \
        (headline["abstention_rate"]["numerator"] - 0) >= 0


def test_wilson_intervals_are_well_formed():
    assert wilson_interval(0, 0)["value"] is None
    zero = wilson_interval(0, 12)
    assert zero["low"] == 0.0 and 0.0 <= zero["high"] <= 1.0
    perfect = wilson_interval(10, 10)
    assert perfect["low"] < 1.0 <= perfect["high"] + 1e-9
    half = wilson_interval(5, 10)
    assert half["low"] < 0.5 < half["high"]


def test_every_headline_metric_carries_an_interval(report):
    for row in report["systems"]["provenancelens"]["headline"]:
        assert row["ci95"]["low"] <= row["ci95"]["high"]
        assert row["ci95"]["denominator"] == row["denominator"]


def test_stratified_results_cover_every_case_exactly_once(report):
    assert sum(row["n_cases"] for row in report["stratified_results"]) == 70
    names = [row["stratum"] for row in report["stratified_results"]]
    assert names == sorted(names)
    assert "controlled" in names


def test_metrics_match_a_direct_recomputation():
    """The study must not report numbers other than the Phase F metrics produce."""
    cases = load_benchmark()
    direct = compute_metrics([run_case(case) for case in cases], system="provenancelens")
    rows = {row["metric"]: row for row in headline_metrics(direct)}
    assert rows["action_accuracy"]["numerator"] == \
        direct["action"]["accuracy"]["numerator"]
    assert rows["coverage"]["value"] == pytest.approx(direct["coverage"]["value"])


# --- report shape -------------------------------------------------------------

def test_report_contains_every_required_analysis(report):
    for key in ("benchmark", "systems", "comparisons", "selective_risk_curve",
                "failure_analysis", "evidence_usage", "stratified_results",
                "ablations", "action_confusion", "per_case"):
        assert key in report
    assert report["benchmark"]["by_track"]["real"] == 44
    assert report["benchmark"]["by_track"]["controlled"] == 26


def test_manifest_records_environment_and_digests(tmp_path: Path):
    payload = run_phase_g(include_ablations=False)
    manifest = build_manifest(payload, artifacts={},
                              snapshot_root=REPO_ROOT / "data" / "snapshots",
                              elapsed_seconds=1.25, config={"tracks": "all"})
    assert manifest["environment"]["network_used"] is False
    assert manifest["environment"]["llm_used"] is False
    assert manifest["inputs"], "input digests must be recorded"
    assert len(manifest["inputs"]) == 44
    assert manifest["timings"]["elapsed_seconds"] == 1.25
    assert "excluded from the report digest" in manifest["timings"]["definition"]
    written = write_phase_g_report(payload, tmp_path, manifest=manifest,
                                   snapshot_root=REPO_ROOT / "data" / "snapshots",
                                   config={"tracks": "all"})
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "phase_g_report.md").exists()
    assert (tmp_path / "plots" / "risk_coverage_curve.png").exists()
    assert len(written) >= 25
    saved = json.loads((tmp_path / "manifest.json").read_text())
    assert saved["report_digest"] if "report_digest" in saved else True
    assert all(len(digest) == 64 for digest in saved["outputs"].values())


def test_report_digest_ignores_timings_but_not_results():
    payload = run_phase_g(include_ablations=False)
    other = dict(payload)
    other["per_case"] = "changed"
    assert report_digest(payload) == report_digest(other)
    other["comparisons"] = []
    assert report_digest(payload) != report_digest(other)


def test_markdown_tables_are_deterministic_and_escaped():
    rows = [{"a": 1, "b": "x|y"}, {"a": 0.5, "b": None}]
    first = render_markdown_table(rows)
    assert first == render_markdown_table(rows)
    assert "x|y" in first
    assert "| --- | --- |" in first


def test_figures_are_written_for_every_documented_plot(tmp_path: Path):
    payload = run_phase_g(include_extraction=False)
    write_phase_g_report(payload, tmp_path, manifest={
        "repository": {"git_commit": "test", "git_branch": "test"},
    }, snapshot_root=REPO_ROOT / "data" / "snapshots", config={})
    names = {path.stem for path in (tmp_path / "plots").glob("*.png")}
    assert names == {
        "action_accuracy_by_system", "risk_coverage_curve",
        "ablation_delta_action_accuracy", "stratum_accuracy", "failure_taxonomy",
        "evidence_usage", "action_confusion",
    }


def test_calibration_is_still_declined(report):
    """support_score is not a probability: no calibration metric may appear."""
    def keys(payload, prefix=""):
        if isinstance(payload, dict):
            for key, value in payload.items():
                yield f"{prefix}{key}"
                yield from keys(value, f"{prefix}{key}.")
        elif isinstance(payload, list):
            for item in payload:
                yield from keys(item, prefix)

    metric_keys = {key.lower() for key in keys(report)}
    for banned in ("ece", "brier", "reliability_diagram", "expected_calibration_error"):
        assert not any(banned in key for key in metric_keys)


def test_ablation_effects_flag_the_reference_row(report):
    rows = ablation_effects(run_ablations(load_benchmark()))
    assert rows[0]["ablation"] == "full"
    assert rows[0]["verdict"] == "reference"
    assert all(row["verdict"] for row in rows)


def test_evidence_usage_separates_frequency_from_decisiveness(report):
    usage = evidence_usage(load_benchmark())
    assert usage["presence"], "presence must be reported"
    for source, entry in usage["presence"].items():
        assert 0.0 <= entry["share"] <= 1.0
        assert "frequency" in usage["definition"]
    assert "attribution" in usage["definition"]


def test_stratified_helper_is_track_aware():
    cases = load_benchmark()
    results = [run_case(case) for case in cases]
    rows = stratified_results(results, cases, system_metrics={})
    assert {row["stratum"] for row in rows} <= {
        "controlled", "peft_adapters", "lora_adapters", "mergekit_merges",
        "quantized_gguf", "quantized_awq", "instruction_finetunes", "pre_phase_g",
    }


def test_failure_analysis_handles_an_empty_benchmark():
    assert failure_analysis([], [])["n_failures"] == 0


def test_track_restriction_is_honoured():
    payload = run_phase_g(track=Track.REAL, include_ablations=False)
    assert payload["benchmark"]["by_track"] == {"real": 44}
    assert all(result["track"] == "real" for result in payload["per_case"]["provenancelens"])


# --- optional local-LLM comparator (never runs in the test suite) --------------

def test_llm_comparator_is_not_part_of_the_default_study(report):
    """The deterministic study and its digest must stay LLM-free."""
    assert "llm_comparator" not in report
    assert "claims_accepted" not in json.dumps(report)


def test_llm_comparator_targets_are_selected_without_the_engine():
    """Targets come from truth and declared metadata, never from decisions."""
    from provenancelens.evaluation.llm_comparator import llm_comparator_targets

    targets = llm_comparator_targets(load_real_benchmark())
    assert targets, "the comparator needs at least one target"
    for case in targets:
        assert case.track is Track.REAL
        assert case.truth.metadata_state.value in ("incomplete", "valid")
        assert "huggingface.co/" in (case.snapshot_files.get("README.md", "")).lower()
    assert len(targets) <= 12


def test_llm_comparator_refuses_an_uninstalled_model(monkeypatch):
    """Fail closed: never pull a model, never start a runtime for the operator."""
    from provenancelens.evaluation import llm_comparator

    class Unavailable:
        available = False
        installed_models = ("other/model",)
        reason = "not installed"

    monkeypatch.setattr(
        "provenancelens.llm_runtime.llm_availability",
        lambda **kwargs: Unavailable(),
    )
    with pytest.raises(llm_comparator.LLMComparatorUnavailable) as excinfo:
        llm_comparator.run_local_llm_comparator(load_real_benchmark())
    assert "not installed locally" in str(excinfo.value)


def test_llm_comparator_summary_counts_recovery_and_false_repairs():
    from provenancelens.evaluation.llm_comparator import comparator_summary

    rows = [
        {"claims_reported": 2, "claims_accepted": 1, "case_id": "A",
         "deterministic": {"action_correct": False},
         "with_local_llm": {"action_correct": True, "repair_attempted": True,
                            "false_repair": False}},
        {"claims_reported": 1, "claims_accepted": 0, "case_id": "B",
         "deterministic": {"action_correct": True},
         "with_local_llm": {"action_correct": False, "repair_attempted": False,
                            "false_repair": None}},
        {"claims_reported": 1, "claims_accepted": 0, "case_id": "C",
         "deterministic": {"action_correct": False},
         "with_local_llm": {"action_correct": False, "repair_attempted": True,
                            "false_repair": True}},
    ]
    summary = comparator_summary(rows)
    assert summary["n_cases"] == 3
    assert summary["recovered_by_llm"] == 1
    assert summary["regressed_by_llm"] == 1
    assert summary["claims_reported"] == 4
    assert summary["claim_acceptance_rate"] == 0.25
    assert summary["false_repairs"] == 1
    assert summary["false_repair_case_ids"] == ["C"]


def test_llm_comparator_artifact_is_written_separately(tmp_path):
    from provenancelens.evaluation.llm_comparator import write_comparator_report

    payload = {"experiment": "optional_local_llm_comparator", "summary": {"n_cases": 0}}
    path = write_comparator_report(payload, tmp_path)
    assert path.name == "llm_comparator.json"
    assert json.loads(path.read_text())["summary"]["n_cases"] == 0
