"""Optional integrations must never break the deterministic core package."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from provenancelens import langchain_integration as lc

SRC_DIR = Path(__file__).resolve().parents[1] / "src"


def test_langchain_available_flag_is_a_bool():
    assert isinstance(lc.LANGCHAIN_AVAILABLE, bool)


def test_builders_do_not_raise_when_langchain_missing_or_present():
    prompt = lc.build_claim_prompt()
    parser = lc.build_decision_parser()
    chain = lc.build_legacy_audit_chain()
    if lc.LANGCHAIN_AVAILABLE:
        assert prompt is not None
        assert parser is not None
        assert chain is not None
    else:
        assert prompt is None
        assert parser is None
        assert chain is None


@pytest.mark.skipif(not lc.LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
def test_legacy_chain_parity_with_plain_audit():
    from provenancelens.reasoning.legacy import audit
    from fixtures.phase2_samples import PHASE2_EXPECTED, PHASE2_SAMPLES

    chain = lc.build_legacy_audit_chain()
    for sample, expected in zip(PHASE2_SAMPLES, PHASE2_EXPECTED, strict=True):
        assert chain.invoke(sample) == expected
        assert audit(sample) == expected


def test_core_package_imports_with_langchain_blocked():
    """A subprocess without langchain must still import and run the core."""
    script = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_spec(self, fullname, path=None, target=None):
                if fullname.startswith("langchain"):
                    raise ImportError("langchain blocked by test")
                return None

        sys.meta_path.insert(0, _Blocker())

        import provenancelens
        from provenancelens import parsers, reporting, schemas
        from provenancelens.reasoning import legacy
        from provenancelens import langchain_integration as lc

        assert lc.LANGCHAIN_AVAILABLE is False
        assert lc.build_claim_prompt() is None
        assert lc.build_claim_prompt() is None
        assert lc.build_legacy_audit_chain() is None

        result = legacy.audit(
            {
                "model_id": "demo/x",
                "metadata": {},
                "config": {},
                "readme": "",
                "tool_errors": [],
            }
        )
        assert result["action"] == "ABSTAIN", result

        items = parsers.extract_prose_claims("Fine-tuned from org/base-model.")
        assert items[0].relation.value == "finetune"
        print("CORE_OK")
        """
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC_DIR), env["PYTHONPATH"]] if env.get("PYTHONPATH") else [str(SRC_DIR)]
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "CORE_OK" in proc.stdout
