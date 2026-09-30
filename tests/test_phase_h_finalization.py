"""Phase H finalisation: can the documentation be trusted?

Documentation drifts silently, so these tests bind the documents to the
machine-readable results instead of to prose.  They check that:

* every documented number still matches a fresh, offline run;
* the canonical result set verifies against its own manifest;
* the committed results are reproducible from the frozen evidence;
* the demo and CLI cases still exist and still say what they claim;
* the documented commands actually work;
* the evaluated production system did not change during finalisation;
* nothing reintroduced a network import, a secret, a weight file or a claim of
  probability for ``support_score``.

A failing test here means a document is stale, not that the system is broken.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from provenancelens.demo import DEMO_CASES, demo_cases
from provenancelens.evaluation import load_benchmark
from provenancelens.evaluation.canonical import (
    CANONICAL_GENERATION_COMMAND,
    METRIC_DEFINITIONS_VERSION,
    render_results_document,
    verify_canonical_results,
)
from provenancelens.evaluation.phase_g import run_phase_g
from provenancelens.evaluation.report import report_digest
from provenancelens.evaluation.runner import run_case

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "results" / "phase_g"
NOTEBOOK = "ProvenanceLens_Phase2 (1).ipynb"

#: Phase G merge commit: the evaluated system must be identical to it.
PHASE_G_START = "1e4efbf"

#: SHA-256 of the legacy notebook, unchanged since the original commit.
NOTEBOOK_SHA256 = "7b168dbf1f36f62f5224933253fa990c80b7ebe5c2926517ac3135aea9c33de6"

DOCS = tuple(sorted((REPO_ROOT / "docs").glob("*.md")))


def _canonical_manifest() -> dict:
    return json.loads((CANONICAL / "manifest.json").read_text(encoding="utf-8"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- canonical results are the single source of truth ------------------------

def test_canonical_result_set_exists_and_verifies():
    verification = verify_canonical_results(CANONICAL)
    assert verification["ok"], verification["problems"]
    assert verification["n_files"] >= 25


def test_canonical_manifest_records_the_expected_composition():
    manifest = _canonical_manifest()
    assert manifest["n_cases"] == 70
    assert manifest["n_controlled"] == 26
    assert manifest["n_real"] == 44
    assert manifest["benchmark_version"] == "1.0"
    assert manifest["metric_definitions_version"] == METRIC_DEFINITIONS_VERSION
    assert manifest["label_provenance"] == {
        "manual_adjudication": 44, "synthetic_construction": 26,
    }


def test_canonical_manifest_pins_every_snapshot_revision():
    manifest = _canonical_manifest()
    revisions = manifest["snapshot_revisions"]
    assert len(revisions) == 44
    cases = {case.repository: case.snapshot_commit
             for case in load_benchmark(validate=False)
             if case.snapshot_commit}
    for repository, revision in revisions.items():
        assert repository in cases, repository
        assert cases[repository] == revision, repository


def test_canonical_manifest_is_free_of_absolute_paths_and_timestamps():
    """Byte-determinism is the point, so nothing machine-specific may leak in."""
    text = _read(CANONICAL / "manifest.json")
    assert not re.search(r"/(Users|home)/[A-Za-z0-9_.-]+", text)
    # no wall-clock duration and no ISO-8601 timestamp value anywhere
    assert not re.search(r'"elapsed_seconds"\s*:\s*[0-9]', text)
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:", text)
    for key in ("random_seed", "seed_note", "network_used", "llm_used",
                "timestamps_in_canonical_files"):
        assert key in _canonical_manifest()["determinism"]


def test_canonical_manifest_rejects_a_tampered_file(tmp_path):
    """The digests must actually detect modification."""
    import shutil

    copy = tmp_path / "canonical"
    shutil.copytree(CANONICAL, copy)
    assert verify_canonical_results(copy)["ok"]
    (copy / "tables" / "headline_metrics.csv").write_text("tampered\n", encoding="utf-8")
    verification = verify_canonical_results(copy)
    assert not verification["ok"]
    assert any("digest mismatch" in problem for problem in verification["problems"])


# --- documentation cannot drift from measurements ----------------------------

def test_results_document_matches_a_fresh_run():
    """docs/RESULTS.md is generated; a stale number must fail here."""
    report = run_phase_g(include_extraction=False)
    expected = render_results_document(report, {
        "metric_definitions_version": METRIC_DEFINITIONS_VERSION,
    })
    assert _read(CANONICAL / "RESULTS.md") == expected


def test_committed_results_reproduce_from_the_frozen_evidence():
    """The committed digest must be what today's code produces offline."""
    report = run_phase_g(include_extraction=False)
    assert report_digest(report) == _canonical_manifest()["report_digest"]


def test_results_document_states_the_measured_headline():
    report = run_phase_g(include_extraction=False)
    text = _read(CANONICAL / "RESULTS.md")
    main = report["systems"]["provenancelens"]
    for scope, key in (("COMBINED", "headline"), ("REAL", "headline_real"),
                       ("CONTROLLED", "headline_controlled")):
        assert f"Main results — {scope}" in text
        for row in main[key]:
            expected = f"| {row['numerator']} | {row['denominator']} |"
            assert expected in text, f"{scope}/{row['metric']} missing {expected}"


def test_readme_quotes_the_current_headline_numbers():
    """The README summary table must agree with the generated results."""
    report = run_phase_g(include_ablations=False, include_extraction=False)
    main = report["systems"]["provenancelens"]
    readme = _read(REPO_ROOT / "README.md")
    for key in ("headline", "headline_real"):
        for row in main[key]:
            fraction = f"{row['numerator']}/{row['denominator']} = {row['value']:.3f}"
            assert fraction in readme, f"README is stale for {row['metric']}: {fraction}"
    assert "62/70" in readme and "36/44" in readme and "0/12" in readme


def test_benchmark_composition_is_documented_consistently():
    cases = load_benchmark()
    real = sum(1 for case in cases if case.track.value == "real")
    controlled = sum(1 for case in cases if case.track.value == "controlled")
    assert (len(cases), real, controlled) == (70, 44, 26)
    for document in (REPO_ROOT / "README.md", REPO_ROOT / "FINAL_PROJECT_STATUS.md",
                     REPO_ROOT / "docs" / "QUICKSTART.md"):
        text = _read(document)
        assert "70" in text
    assert _canonical_manifest()["n_cases"] == len(cases)


def test_every_doc_links_to_existing_files():
    """No broken internal references: the docs must stay navigable."""
    pattern = re.compile(r"\]\((?!https?://)([^)#]+)(?:#[^)]*)?\)")
    for document in (REPO_ROOT / "README.md", REPO_ROOT / "FINAL_PROJECT_STATUS.md",
                     REPO_ROOT / "CHANGELOG.md", *DOCS):
        for target in pattern.findall(_read(document)):
            if not target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            assert resolved.exists(), f"{document.name} links to missing {target}"


def test_documented_commands_exist_as_code():
    """Every command a reader is told to run must exist in the code base."""
    sources = "\n".join(
        _read(path) for path in
        (REPO_ROOT / "src" / "provenancelens").rglob("*.py")
    )
    for command in (
        "provenancelens.demo", "provenancelens.cli", "phase_g_cli",
        "verified",  # sanity: the study must still verify
    ):
        assert command.split(".")[-1] in sources, command
    assert "publish" in sources and "verify-canonical" in sources


def test_documented_test_count_matches_reality():
    """The docs quote a test count; keep it honest or stop quoting it."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stdout[-2000:]
    collected = int(re.search(r"(\d+) tests? collected", result.stdout).group(1))
    for document in (REPO_ROOT / "README.md", REPO_ROOT / "FINAL_PROJECT_STATUS.md",
                     REPO_ROOT / "docs" / "QUICKSTART.md",
                     REPO_ROOT / "docs" / "REPRODUCIBILITY.md"):
        quoted = re.findall(r"(\d{3}) passed", _read(document))
        for count in quoted:
            # a quoted count may be a subset of the suite, but never more than it
            assert int(count) <= collected, f"{document.name} quotes {count} passed"


# --- demo and CLI ------------------------------------------------------------

def test_demo_cases_exist_and_cover_every_decision():
    cases = demo_cases()
    assert len(cases) == len(DEMO_CASES)
    decisions = {case.case_id: run_case(case).predicted_action.value for case in cases}
    assert set(decisions.values()) == {"KEEP", "ADD", "REPLACE", "ABSTAIN"}


def test_demo_labels_real_and_controlled_cases_distinctly():
    """A controlled case is a specification check and must never look like a fact."""
    for case in demo_cases():
        assert case.track.value in ("real", "controlled")
        if case.track.value == "real":
            assert case.snapshot_commit, "a REAL demo case must be a frozen snapshot"
            assert case.repository
    rendered = "\n".join(
        _read(path) for path in (REPO_ROOT / "src" / "provenancelens" / "demo.py",)
    )
    assert "CONTROLLED" in rendered and "REAL" in rendered


def test_demo_runs_offline_and_prints_the_expected_sections(capsys):
    from provenancelens.demo import render_case

    case = demo_cases()[0]
    text = render_case(case)
    for section in ("repository", "revision (pinned)", "Declared metadata",
                    "independent evidence", "conflicts", "support score",
                    "DECISION"):
        assert section in text, section
    assert "not a probability" in text
    assert "chain-of-thought" not in text.lower()


def test_demo_json_output_is_machine_readable(capsys):
    from provenancelens.demo import main as demo_main

    assert demo_main(["--json", "--case", demo_cases()[0].case_id]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["decision"] in ("KEEP", "ADD", "REPLACE", "ABSTAIN")
    assert "support_score" in payload[0]
    assert "probability" not in json.dumps(payload[0]).lower()


def test_cli_help_works_for_every_command(capsys):
    from provenancelens.cli import main as cli_main

    with pytest.raises(SystemExit) as excinfo:
        cli_main(["--help"])
    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    for command in ("audit", "demo", "benchmark", "study"):
        assert command in output


def test_cli_audit_reports_a_missing_snapshot_helpfully(capsys):
    from provenancelens.cli import main as cli_main

    assert cli_main(["audit", "definitely/not-frozen"]) == 2
    error = capsys.readouterr().err
    assert "no frozen snapshot" in error
    assert "frozen" in error.lower()


def test_cli_audit_renders_a_frozen_repository(capsys):
    from provenancelens.cli import main as cli_main

    assert cli_main(["audit", "peft-internal-testing/tiny-OPTForCausalLM-lora"]) == 0
    output = capsys.readouterr().out
    assert "DECISION" in output and "NOT a probability" in output
    assert "never writes" in output


def test_cli_audit_rejects_a_revision_mismatch(capsys):
    from provenancelens.cli import main as cli_main

    code = cli_main(["audit", "peft-internal-testing/tiny-OPTForCausalLM-lora",
                     "--revision", "0" * 40])
    assert code == 2
    assert "pinned revision" in capsys.readouterr().err


# --- the evaluated system must not have changed ------------------------------

@pytest.mark.parametrize("production", [
    "collectors", "parsers", "reasoning", "resolution", "fusion", "schemas",
    "pipeline.py", "snapshots", "reporting", "prose", "llm_runtime.py",
    "langchain_integration", "tools.py",
])
def test_production_behaviour_is_unchanged_since_phase_g(production):
    """Phase H is finalisation: the evaluated system must be byte-identical."""
    target = f"src/provenancelens/{production}"
    result = subprocess.run(
        ["git", "diff", "--stat", PHASE_G_START, "--", target],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:  # pragma: no cover - source checkout without history
        pytest.skip("git history unavailable")
    assert result.stdout.strip() == "", (
        f"production code changed during finalisation:\n{result.stdout}"
    )


def test_notebook_is_byte_identical():
    import hashlib

    digest = hashlib.sha256((REPO_ROOT / NOTEBOOK).read_bytes()).hexdigest()
    assert digest == NOTEBOOK_SHA256
    result = subprocess.run(
        ["git", "log", "--format=%h", "-1", "--", NOTEBOOK],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.stdout.strip(), "the notebook must still be tracked"


def test_benchmark_labels_unchanged_since_phase_g():
    """Finalisation must not quietly re-adjudicate the benchmark."""
    result = subprocess.run(
        ["git", "diff", "--stat", PHASE_G_START, "--",
         "src/provenancelens/evaluation/adjudication", "src/provenancelens/evaluation/controlled.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:  # pragma: no cover
        pytest.skip("git history unavailable")
    assert result.stdout.strip() == "", f"benchmark labels changed:\n{result.stdout}"


def test_evaluation_package_still_imports_without_the_network_stack():
    """Regression guard for the Phase G fix: no httpx/huggingface_hub import."""
    guard = """
import sys
class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name in ('httpx', 'huggingface_hub'):
            raise ImportError('blocked: ' + name)
        return None
sys.meta_path.insert(0, Blocker())
import provenancelens.evaluation as e
print(e.benchmark_summary(e.load_benchmark())['n_cases'])
"""
    env = {"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-c", guard], capture_output=True, text=True,
        cwd=str(REPO_ROOT), env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "70"


# --- repository hygiene ------------------------------------------------------

def test_no_secrets_or_weights_are_tracked():
    import hashlib

    forbidden_suffixes = (".safetensors", ".gguf", ".bin", ".pt", ".pth", ".onnx")
    credential = re.compile(
        r"(hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|"
        r"-----BEGIN [A-Z ]*PRIVATE KEY)"
    )
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True,
        cwd=str(REPO_ROOT),
    ).stdout.split("\0")
    checked = 0
    for name in filter(None, tracked):
        path = REPO_ROOT / name
        assert not name.endswith(forbidden_suffixes), f"weight file tracked: {name}"
        if path.stat().st_size > 200_000 or "__pycache__" in name or name.endswith(".pyc"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not credential.search(text), f"credential-shaped string in {name}"
        assert not re.search(r"/(Users|home)/[A-Za-z0-9_.-]+", text), \
            f"absolute private path in {name}"
        checked += 1
    assert checked > 50


def test_canonical_results_are_small_enough_to_commit():
    total = sum(path.stat().st_size for path in CANONICAL.rglob("*") if path.is_file())
    assert total < 2_000_000, f"canonical results are {total} bytes"


def test_results_directory_is_the_only_committed_result_source():
    """One source of truth: results/ is committed, artifacts/ stays scratch."""
    assert "artifacts/" in _read(REPO_ROOT / ".gitignore")
    tracked_results = {
        name for name in subprocess.run(
            ["git", "ls-files", "-z"], capture_output=True, text=True,
            cwd=str(REPO_ROOT),
        ).stdout.split("\0") if name.startswith("results/")
    }
    assert tracked_results, "canonical results must be committed"
    assert not any(name.startswith("artifacts/") for name in tracked_results)


# --- honest language ---------------------------------------------------------

#: words that turn a following phrase into a denial
_NEGATIONS = ("not ", "never ", "no ", "refuse", "cannot", "without", "rather than")


def _assert_never_asserted(document: Path, phrase: str, *, window: int = 90) -> None:
    """Fail only when ``phrase`` appears *without* a nearby negation.

    Documents must be able to say "refuse to treat support_score as a
    probability" - that is the honest phrasing - while never stating the claim.
    """
    # markdown emphasis must not hide a negation (e.g. "**not** claimed")
    text = _read(document).replace("*", "").replace("`", "").lower()
    needle = phrase.lower()
    start = 0
    while (index := text.find(needle, start)) != -1:
        prefix = text[max(0, index - window):index]
        assert any(negation in prefix for negation in _NEGATIONS), (
            f"{document.name} asserts '{phrase}' without a negation: "
            f"...{text[max(0, index - 60):index + len(needle) + 20]}..."
        )
        start = index + len(needle)


def test_support_score_is_never_called_a_probability():
    """A non-probability must never be described as one."""
    documents = [REPO_ROOT / "README.md", REPO_ROOT / "FINAL_PROJECT_STATUS.md",
                 REPO_ROOT / "CHANGELOG.md", *DOCS,
                 CANONICAL / "RESULTS.md"]
    for document in documents:
        for phrase in ("is a probability", "as a probability", "probability of",
                       "calibrated confidence", "confidence percentage"):
            _assert_never_asserted(document, phrase)


def test_false_repair_rate_is_always_reported_with_its_denominator():
    report = run_phase_g(include_ablations=False, include_extraction=False)
    main = report["systems"]["provenancelens"]
    for key in ("headline", "headline_real"):
        row = next(r for r in main[key] if r["metric"] == "false_repair_rate")
        assert row["denominator"] > 0
        text = _read(CANONICAL / "RESULTS.md")
        assert f"{row['numerator']}/{row['denominator']}" in text
    definition = next(
        r["definition"] for r in main["headline"]
        if r["metric"] == "false_repair_rate"
    )
    assert "incorrect attempted repairs" in definition
    assert "attempted repairs" in definition


def test_claims_document_separates_supported_from_unsupported():
    text = _read(REPO_ROOT / "docs" / "CLAIMS.md")
    assert "## Supported" in text and "## Not supported" in text
    for forbidden in ("never makes incorrect repairs", "guarantees safety",
                      "state of the art"):
        assert forbidden.lower() in text.lower(), (
            f"the claims document should explicitly reject: {forbidden}"
        )


def test_limitations_and_threats_are_present_and_substantial():
    limitations = _read(REPO_ROOT / "docs" / "LIMITATIONS.md")
    threats = _read(REPO_ROOT / "docs" / "THREATS_TO_VALIDITY.md")
    for required in ("not a calibrated probability", "quantized_awq", "0/12",
                     "does **not** mean"):
        assert required in limitations, f"LIMITATIONS.md should state: {required}"
    for section in ("Internal validity", "External validity", "Construct validity",
                    "Conclusion validity"):
        assert section in threats, f"THREATS_TO_VALIDITY.md lacks {section}"
    assert len(threats) > 3000 and len(limitations) > 3000


def test_paper_notes_avoid_unsupported_novelty_claims():
    text = _read(REPO_ROOT / "docs" / "PAPER_NOTES.md")
    assert "Working title" in text and "Threats to validity" in text
    for banned in ("first-ever", "state of the art", "guarantees safety",
                   "universally superior", "state-of-the-art"):
        _assert_never_asserted(REPO_ROOT / "docs" / "PAPER_NOTES.md", banned)
    assert "not claimed" in text.lower().replace("*", "").replace("`", "")


def test_methodology_defines_the_false_repair_rate_explicitly():
    text = _read(REPO_ROOT / "docs" / "METHODOLOGY.md")
    assert "**False Repair Rate = incorrect attempted repairs / total attempted repairs.**" \
        in text.replace("\n", " ").replace("  ", " ") or \
        "False Repair Rate = incorrect attempted repairs / total attempted repairs" \
        in text.replace("\n", " ")
    for required in ("independence", "Wilson", "unverifiable", "calibration",
                     "ambiguous"):
        assert required in text, f"METHODOLOGY.md should define {required}"
