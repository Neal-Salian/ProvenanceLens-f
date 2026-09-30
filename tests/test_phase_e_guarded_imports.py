"""The deterministic core must not require LangChain, Ollama, or a network.

These checks run in **subprocesses** on purpose: simulating a missing optional
dependency in-process would reload ``provenancelens`` and create duplicate
class objects, which pollutes other tests. A fresh interpreter genuinely
proves the core imports, parses, and audits with LangChain unavailable.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
DATA = REPO_ROOT / "data" / "snapshots"
ADAPTER = "peft-internal-testing/tiny-OPTForCausalLM-lora"

_BLOCK_LANGCHAIN = """
import builtins, sys
_real = builtins.__import__
def guard(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if root in ("langchain", "langchain_core", "langchain_ollama", "ollama"):
        raise ImportError("blocked for test: " + name)
    return _real(name, globals, locals, fromlist, level)
builtins.__import__ = guard
for name in [n for n in list(sys.modules) if n.split(".")[0] in ("langchain", "langchain_core", "langchain_ollama", "ollama")]:
    del sys.modules[name]
"""


def run_without_langchain(body: str) -> str:
    script = _BLOCK_LANGCHAIN + textwrap.dedent(body)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, (
        f"subprocess failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout


def test_core_imports_without_langchain():
    output = run_without_langchain("""
        import provenancelens
        import provenancelens.collectors, provenancelens.parsers
        import provenancelens.snapshots, provenancelens.reasoning
        import provenancelens.pipeline, provenancelens.reporting
        print("CORE_IMPORTS_OK", provenancelens.__version__)
    """)
    assert "CORE_IMPORTS_OK" in output


def test_deterministic_audit_runs_without_langchain():
    output = run_without_langchain(f"""
        from pathlib import Path
        from provenancelens.pipeline import audit_repository
        result = audit_repository({ADAPTER!r}, root=Path({str(DATA)!r}))
        print("DECISION", result.decision.decision.value,
              result.decision.support_score,
              bool(result.decision.recommended_patch))
    """)
    assert "DECISION ADD" in output


def test_availability_probe_reports_unavailable_without_langchain():
    output = run_without_langchain("""
        from provenancelens import llm_runtime
        availability = llm_runtime.llm_availability(require_dependency=True)
        print("AVAILABLE", availability.available)
        print("REASON", availability.reason)
        print("DEFAULT", llm_runtime.configured_model(), llm_runtime.DEFAULT_LLM_BASE_URL)
    """)
    assert "AVAILABLE False" in output
    assert "langchain-ollama" in output
    assert "DEFAULT llama3.2:3b" in output


def test_prose_extraction_reports_unavailable_rather_than_crashing():
    """A configured LLM path that cannot import must degrade, not explode."""
    output = run_without_langchain(f"""
        from pathlib import Path
        from provenancelens.pipeline import audit_repository_with_prose
        outcome = audit_repository_with_prose({ADAPTER!r}, root=Path({str(DATA)!r}))
        print("MODE", outcome.mode)
        print("STATUS", outcome.report.status.value)
        print("DECISION", outcome.decision.decision.value)
    """)
    assert "MODE deterministic-only" in output
    assert "STATUS UNAVAILABLE" in output
    assert "DECISION ADD" in output


def test_langchain_is_not_a_hard_dependency_of_the_core():
    """The installed core must import langchain only inside prose modules."""
    core_modules = [
        "provenancelens/__init__.py",
        "provenancelens/pipeline.py",
        "provenancelens/reasoning/decision.py",
        "provenancelens/parsers/bundle.py",
        "provenancelens/collectors/huggingface.py",
    ]
    for relative in core_modules:
        text = (SRC / relative).read_text(encoding="utf-8")
        assert "import langchain" not in text, relative
        assert "from langchain" not in text, relative


# --- source-level safety invariants -----------------------------------------


def test_phase_e_code_never_imports_a_paid_api():
    """No paid inference provider may be imported anywhere in the package."""
    forbidden_imports = (
        "import openai", "from openai", "import anthropic", "from anthropic",
        "google.generativeai", "from langchain_openai", "from langchain_anthropic",
        "from langchain_google_genai", "from langchain_cohere",
        "from langchain_mistralai", "chatopenai", "chatanthropic",
        "huggingface_hub_inference",
    )
    for path in (SRC / "provenancelens").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden_imports:
            assert needle not in text, f"{path.name} imports a paid provider: {needle}"


def test_package_never_executes_commands():
    """Model pulls, repository commands, and shell calls are never executed."""
    for path in (SRC / "provenancelens").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "os.popen", "shutil.rmtree"):
            assert forbidden not in text, f"{path.name} uses {forbidden}"


def test_manual_install_hint_is_only_a_message():
    """The 'ollama pull' string may appear only as advice, never as a command."""
    hits = []
    for path in (SRC / "provenancelens").rglob("*.py"):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "ollama pull" in line:
                hits.append((path.name, number, line.strip()))
    assert hits, "expected a manual install hint for unavailable models"
    for name, _number, line in hits:
        assert "subprocess" not in line
        assert "os.system" not in line
