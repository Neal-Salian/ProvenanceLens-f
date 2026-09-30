"""Baselines, dataset loading, runner determinism, and offline guarantees."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from provenancelens.evaluation.baselines import (
    BASELINE_NAMES,
    LLMOracleBaseline,
    SOURCE_PRIORITY,
    run_baseline,
)
from provenancelens.evaluation.dataset import (
    benchmark_summary,
    load_benchmark,
    load_controlled_benchmark,
    load_real_benchmark,
)
from provenancelens.evaluation.run import (
    DEFAULT_SYSTEMS,
    run_benchmark,
    selective_csv,
    write_artifacts,
)
from provenancelens.evaluation.runner import run_case
from provenancelens.evaluation.schema import BenchmarkCase, Track
from provenancelens.evaluation.validation import assert_valid_benchmark
from provenancelens.schemas.audit import Decision
from provenancelens.schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from provenancelens.schemas.lineage import Relation

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"
EVAL_DIR = REPO_ROOT / "src" / "provenancelens" / "evaluation"


def _ev(source_type: SourceType, name: str, parent: str, relation=None,
        reliability: Reliability = Reliability.HIGH, key_path: str | None = None):
    return EvidenceItem(
        source_type=source_type, role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.DETERMINISTIC, reliability=reliability,
        source_name=name, candidate_parent=parent, relation=relation, key_path=key_path,
        explicitness=Explicitness.EXPLICIT,
    )


def _case(**overrides) -> BenchmarkCase:
    from provenancelens.evaluation.schema import (
        Adjudication, GroundTruth, LabelProvenance, MetadataState, TruthStatus,
    )

    base = dict(
        case_id="UNIT", track=Track.CONTROLLED, title="unit",
        evidence=(), declared_base_model="org/base", declared_relation_raw="finetune",
        truth=GroundTruth(
            parents=("org/base",), parents_status=TruthStatus.KNOWN,
            relation=Relation.FINETUNE, relation_status=TruthStatus.KNOWN,
            metadata_state=MetadataState.VALID, rationale="unit",
        ),
        expected_action=Decision.KEEP, acceptable_actions=(Decision.KEEP,),
        adjudication=Adjudication(
            provenance=LabelProvenance.SYNTHETIC_CONSTRUCTION, adjudicator="unit"),
    )
    base.update(overrides)
    return BenchmarkCase(**base)


# --- dataset ----------------------------------------------------------------


def test_controlled_track_loads_and_validates():
    cases = load_controlled_benchmark()
    assert len(cases) == 26
    assert all(case.track is Track.CONTROLLED for case in cases)
    assert_valid_benchmark(cases)


def test_real_track_loads_from_frozen_snapshots():
    cases = load_real_benchmark()
    assert len(cases) == 44
    assert len({case.repository for case in cases}) == 44
    assert len({case.snapshot_commit for case in cases}) == 44
    for case in cases:
        assert case.track is Track.REAL
        assert case.repository and case.snapshot_commit and case.snapshot_files
        assert case.adjudication.provenance.value == "manual_adjudication"
        assert case.adjudication.evidence_used


def test_benchmark_summary_reports_tracks_separately():
    summary = benchmark_summary(load_benchmark())
    assert summary["by_track"] == {"controlled": 26, "real": 44}
    assert summary["by_label_provenance"]["manual_adjudication"] == 44
    assert summary["by_expected_action"]["ABSTAIN"] > summary["by_expected_action"]["ADD"]
    assert summary["non_known_parent_truth"] > 0


def test_single_track_selection():
    cases = load_benchmark("real")
    assert {case.track for case in cases} == {Track.REAL}


def test_real_adjudication_does_not_assert_a_relation_it_cannot_know():
    cases = {case.repository: case for case in load_real_benchmark()}
    openhermes = cases["teknium/OpenHermes-2.5-Mistral-7B"]
    assert openhermes.truth.relation is None
    assert openhermes.truth.relation_status.value == "unknown"
    assert openhermes.truth.metadata_state.value == "undetermined"
    assert openhermes.expected_action is Decision.ABSTAIN
    assert Decision.KEEP in openhermes.acceptable_actions

    qwen = cases["mergekit-community/Qwen3-1.5B-Instruct"]
    assert qwen.truth.parents_status.value == "ambiguous"
    assert len(qwen.truth.parent_set_alternatives) == 2

    adapter = cases["peft-internal-testing/tiny-OPTForCausalLM-lora"]
    assert adapter.truth.parents_status.value == "known"
    assert adapter.truth.relation is Relation.ADAPTER
    assert adapter.truth.metadata_state.value == "missing"


def test_missing_snapshot_root_is_reported_clearly(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_real_benchmark(tmp_path)


# --- runner -----------------------------------------------------------------


def test_runner_produces_deterministic_results():
    first = run_benchmark(systems=("provenancelens",), include_extraction=False)
    second = run_benchmark(systems=("provenancelens",), include_extraction=False)
    assert first["provenancelens"].model_dump() == second["provenancelens"].model_dump()


def test_runner_uses_snapshot_files_for_real_cases():
    case = next(c for c in load_real_benchmark()
                if c.repository == "peft-internal-testing/tiny-OPTForCausalLM-lora")
    result = run_case(case)
    assert result.predicted_action is Decision.ADD
    assert result.predicted_parents == ("hf-internal-testing/tiny-random-OPTForCausalLM",)
    assert result.repair_attempted and result.false_repair is False


def test_abstention_is_recorded_and_never_counted_correct():
    case = next(c for c in load_controlled_benchmark()
                if c.case_id == "CONTROLLED-05-abstain-no-evidence")
    result = run_case(case)
    assert result.predicted_action is Decision.ABSTAIN
    assert result.abstained and not result.repair_attempted
    assert result.false_repair is False  # nothing was attempted
    assert result.parent_scored is False  # truth not knowable here


def test_unverifiable_attempt_is_neither_correct_nor_false():
    case = next(c for c in load_controlled_benchmark()
                if c.case_id == "CONTROLLED-07-abstain-ambiguous-identifier")
    # force a repair attempt with non-knowable truth to exercise the accounting
    from provenancelens.evaluation.runner import score_decision
    from provenancelens.schemas.audit import AuditDecision
    from provenancelens.schemas.lineage import Lineage, LineageEntry

    decision = AuditDecision(
        model_id="unit",
        current_lineage=case_truth(case) if False else __import__(
            "provenancelens.schemas.lineage", fromlist=["x"]
        ).DeclaredLineage(),
        decision=Decision.ADD,
        proposed_lineage=Lineage(entries=[LineageEntry(parent="org/x", relation=None)]),
        support_score=0.9,
        reasoning_summary="forced",
    )
    result = score_decision(case, decision, system="unit")
    assert result.repair_attempted is True
    assert result.repair_verifiable is False
    assert result.false_repair is None  # neither credited nor blamed


# --- baselines --------------------------------------------------------------


def test_all_default_systems_are_available():
    assert set(DEFAULT_SYSTEMS) == {"provenancelens", *BASELINE_NAMES}
    for name in BASELINE_NAMES:
        case = load_controlled_benchmark()[0]
        assert run_baseline(name, case).system == name


def test_declared_metadata_baseline_never_infers():
    keep = _case()
    assert run_baseline("declared_metadata", keep).predicted_action is Decision.KEEP
    missing = _case(
        declared_base_model=None, declared_relation_raw=None,
        expected_action=Decision.ABSTAIN, acceptable_actions=(Decision.ABSTAIN,),
        truth=_missing_truth(),
    )
    assert run_baseline("declared_metadata", missing).predicted_action is Decision.ABSTAIN


def _missing_truth():
    from provenancelens.evaluation.schema import (
        GroundTruth, MetadataState, TruthStatus,
    )

    return GroundTruth(
        parents=("org/base",), parents_status=TruthStatus.KNOWN,
        metadata_state=MetadataState.MISSING, rationale="nothing declared",
    )


def test_always_keep_matches_declared_metadata_baseline():
    case = load_controlled_benchmark()[0]
    assert (run_baseline("always_keep", case).predicted_action
            is run_baseline("declared_metadata", case).predicted_action)


def test_config_only_baseline_filters_evidence():
    case = _case(evidence=(
        _ev(SourceType.CONFIG, "config.json", "org/base", None, Reliability.MEDIUM,
            key_path="_name_or_path"),
    ))
    result = run_baseline("config_only", case)
    # honest result: a single framework config hint names a parent but states no
    # relation, which is not enough to certify the declared lineage
    assert result.predicted_action is Decision.ABSTAIN
    no_config = _case(
        evidence=(_ev(SourceType.TRAINING_CONFIG, "train.yaml", "org/base",
                      Relation.FINETUNE),),
    )
    assert run_baseline("config_only", no_config).predicted_action is Decision.ABSTAIN


def test_prose_only_baseline_ignores_structured_evidence():
    case = _case(evidence=(
        _ev(SourceType.ADAPTER_CONFIG, "adapter_config.json", "org/base", Relation.ADAPTER,
            Reliability.VERY_HIGH, key_path="base_model_name_or_path"),
    ))
    assert run_baseline("prose_only", case).predicted_action is Decision.ABSTAIN


def test_majority_count_picks_the_most_frequent_parent():
    case = _case(
        declared_base_model=None, declared_relation_raw=None,
        expected_action=Decision.ADD, acceptable_actions=(Decision.ADD,),
        truth=_missing_truth(),
        evidence=(
            _ev(SourceType.TRAINING_CONFIG, "train.yaml", "org/base",
                Relation.FINETUNE),
            _ev(SourceType.README, "README.md", "org/base", Relation.FINETUNE),
            _ev(SourceType.README, "NOTES.md", "org/other", Relation.FINETUNE,
                Reliability.WEAK),
        ),
    )
    result = run_baseline("majority_count", case)
    assert result.predicted_action is Decision.ADD
    assert result.predicted_parents == ("org/base",)


def test_majority_count_abstains_on_a_tie():
    case = _case(
        declared_base_model=None, declared_relation_raw=None,
        expected_action=Decision.ABSTAIN, acceptable_actions=(Decision.ABSTAIN,),
        truth=_missing_truth(),
        evidence=(
            _ev(SourceType.TRAINING_CONFIG, "train.yaml", "org/base", Relation.FINETUNE),
            _ev(SourceType.TRAINING_CONFIG, "train_b.yaml", "org/other", Relation.FINETUNE),
        ),
    )
    assert run_baseline("majority_count", case).predicted_action is Decision.ABSTAIN


def test_rule_priority_prefers_the_adapter_config():
    case = _case(
        declared_base_model=None, declared_relation_raw=None,
        expected_action=Decision.ADD, acceptable_actions=(Decision.ADD,),
        truth=_missing_truth(),
        evidence=(
            _ev(SourceType.TRAINING_CONFIG, "train.yaml", "org/base", Relation.FINETUNE),
            _ev(SourceType.ADAPTER_CONFIG, "adapter_config.json", "org/base",
                Relation.ADAPTER, Reliability.VERY_HIGH,
                key_path="base_model_name_or_path"),
        ),
    )
    result = run_baseline("rule_priority", case)
    assert result.predicted_parents == ("org/base",)
    assert result.predicted_relation is Relation.ADAPTER


def test_rule_priority_documents_its_fixed_hierarchy():
    kinds = [kind for kind, _ in SOURCE_PRIORITY]
    assert kinds.index(SourceType.ADAPTER_CONFIG) < kinds.index(SourceType.TRAINING_CONFIG)
    assert kinds.index(SourceType.MERGE_CONFIG) < kinds.index(SourceType.CONFIG)


def test_llm_oracle_baseline_is_an_interface_only():
    assert hasattr(LLMOracleBaseline, "run")
    from provenancelens.evaluation.baselines import BASELINES
    assert "llm_full_context" not in BASELINES  # never a required dependency
    assert "llm_full_context" not in DEFAULT_SYSTEMS


# --- artifacts / CLI --------------------------------------------------------


def test_artifacts_are_written_and_machine_readable(tmp_path: Path):
    runs = run_benchmark(systems=("provenancelens", "rule_priority"),
                         include_extraction=False)
    written = write_artifacts(runs, tmp_path)
    assert (tmp_path / "metrics.json").is_file()
    assert (tmp_path / "selective_metrics.csv").is_file()
    payload = json.loads((tmp_path / "metrics.json").read_text())
    assert "provenancelens" in payload and "action" in payload["provenancelens"]
    csv_text = selective_csv(runs)
    assert csv_text.startswith("system,threshold")
    assert written


def test_cli_validate_runs_offline(tmp_path: Path):
    env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-m", "provenancelens.evaluation", "validate"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["n_cases"] == 70
    assert payload["errors"] == []


def test_cli_run_writes_artifacts(tmp_path: Path):
    env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-m", "provenancelens.evaluation", "run",
         "--track", "real", "--output", str(tmp_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "metrics.json").is_file()


# --- integrity --------------------------------------------------------------


def test_evaluation_does_not_modify_frozen_snapshots():
    def digest() -> dict[str, str]:
        return {
            str(path.relative_to(SNAPSHOT_ROOT)): hashlib.sha256(
                path.read_bytes()).hexdigest()
            for path in sorted(SNAPSHOT_ROOT.rglob("*")) if path.is_file()
        }

    before = digest()
    run_benchmark(include_extraction=True)
    assert digest() == before


def test_decision_evaluation_runs_without_the_optional_llm_stack():
    """Phase F metrics must not depend on the Phase E extra."""
    guard = """
import builtins
_real = builtins.__import__
def _guard(name, g=None, l=None, fromlist=(), level=0):
    if name.split('.')[0] in ('langchain_core', 'langchain', 'langchain_ollama', 'ollama'):
        raise ImportError('blocked: ' + name)
    return _real(name, g, l, fromlist, level)
builtins.__import__ = _guard
from provenancelens.evaluation.run import run_benchmark
runs = run_benchmark(include_extraction=True)
print('ACTION', runs['provenancelens'].metrics['action']['accuracy']['numerator'])
print('EXTRACTION', runs['provenancelens'].extraction.get('status', 'computed'))
"""
    env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-c", guard], capture_output=True, text=True,
        cwd=str(REPO_ROOT), env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ACTION 62" in result.stdout
    # extraction metrics are reported as unavailable rather than crashing
    assert "EXTRACTION unavailable" in result.stdout


def test_evaluation_package_does_not_import_the_network_or_llm():
    for name in ("dataset.py", "controlled.py", "real.py", "runner.py", "metrics.py",
                 "selective.py", "validation.py", "baselines.py", "run.py"):
        text = (EVAL_DIR / name).read_text(encoding="utf-8")
        for forbidden in ("huggingface_hub", "requests.", "urllib.request", "httpx",
                          "subprocess", "os.system"):
            assert forbidden not in text, f"{name} references {forbidden}"
    # the decision-metric modules never import the optional LLM stack
    for name in ("metrics.py", "baselines.py", "selective.py", "dataset.py"):
        text = (EVAL_DIR / name).read_text(encoding="utf-8")
        assert "langchain" not in text, f"{name} imports langchain"
