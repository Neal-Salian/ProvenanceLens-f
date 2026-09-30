"""LangChain tools: they work, they are safe, and the workflow really uses them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool

from provenancelens.tools import (
    build_list_snapshots_tool,
    build_readme_prose_tool,
    build_snapshot_evidence_tool,
    build_snapshot_tools,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"

ADAPTER = "peft-internal-testing/tiny-OPTForCausalLM-lora"
MERGE = "mergekit-community/Qwen3-1.5B-Instruct"


@pytest.fixture
def tools() -> list[StructuredTool]:
    return build_snapshot_tools(root=SNAPSHOT_ROOT)


# --- the tools are real LangChain tools -------------------------------------


def test_tools_are_structured_langchain_tools(tools: list[StructuredTool]):
    assert len(tools) == 3
    for tool in tools:
        assert isinstance(tool, StructuredTool)
        assert tool.name
        assert tool.description
        assert tool.args_schema is not None


def test_tool_names_are_stable(tools: list[StructuredTool]):
    assert sorted(t.name for t in tools) == [
        "list_frozen_snapshots",
        "lookup_frozen_lineage_evidence",
        "read_frozen_model_card",
    ]


def test_list_snapshots_tool_returns_the_frozen_repositories(tools):
    tool = next(t for t in tools if t.name == "list_frozen_snapshots")
    payload = json.loads(tool.invoke({}))
    repositories = {entry["repository"] for entry in payload["snapshots"]}
    assert ADAPTER in repositories
    assert MERGE in repositories
    assert all(len(entry["commit"]) == 40 for entry in payload["snapshots"])


def test_evidence_tool_returns_structured_deterministic_evidence(tools):
    tool = next(t for t in tools if t.name == "lookup_frozen_lineage_evidence")
    payload = json.loads(tool.invoke({"repository": ADAPTER}))
    assert payload["found"] is True
    assert payload["commit"]
    assert payload["independent_evidence"]
    first = payload["independent_evidence"][0]
    assert set(first) >= {
        "source_type", "source_name", "candidate_parent", "relation",
        "reliability", "explicitness", "extraction_method",
    }
    adapter_items = [
        item for item in payload["independent_evidence"]
        if item["source_type"] == "adapter_config"
    ]
    assert adapter_items and adapter_items[0]["relation"] == "adapter"


def test_readme_tool_returns_raw_prose(tools):
    tool = next(t for t in tools if t.name == "read_frozen_model_card")
    payload = json.loads(tool.invoke({"repository": ADAPTER}))
    assert payload["found"] is True
    assert isinstance(payload["text"], str)
    assert payload["text"].strip()


# --- safety -----------------------------------------------------------------


def test_unknown_repository_is_reported_not_raised(tools):
    for name, args in (
        ("lookup_frozen_lineage_evidence", {"repository": "org/does-not-exist"}),
        ("read_frozen_model_card", {"repository": "org/does-not-exist"}),
    ):
        tool = next(t for t in tools if t.name == name)
        payload = json.loads(tool.invoke(args))
        assert payload["found"] is False
        assert "no frozen snapshot" in payload["reason"]


def test_path_traversal_source_name_is_refused(tools):
    tool = next(t for t in tools if t.name == "read_frozen_model_card")
    payload = json.loads(tool.invoke({
        "repository": ADAPTER, "source_name": "../../../etc/passwd",
    }))
    assert payload["found"] is False


def test_absolute_source_name_is_refused(tools):
    tool = next(t for t in tools if t.name == "read_frozen_model_card")
    payload = json.loads(tool.invoke({
        "repository": ADAPTER, "source_name": "/etc/passwd",
    }))
    assert payload["found"] is False


def test_missing_artifact_is_reported(tools):
    tool = next(t for t in tools if t.name == "read_frozen_model_card")
    payload = json.loads(tool.invoke({
        "repository": ADAPTER, "source_name": "does-not-exist.md",
    }))
    assert payload["found"] is False
    assert "not present" in payload["reason"]


def test_invalid_repository_id_is_reported(tools):
    tool = next(t for t in tools if t.name == "lookup_frozen_lineage_evidence")
    payload = json.loads(tool.invoke({"repository": "not a repo"}))
    assert payload["found"] is False


def test_tools_never_write_anything(tmp_path: Path):
    """Read-only guarantee: auditing with tools leaves the snapshots untouched."""
    import hashlib

    def digest_tree(root: Path) -> dict[str, str]:
        return {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()
        }

    before = digest_tree(SNAPSHOT_ROOT)
    tools = build_snapshot_tools(root=SNAPSHOT_ROOT)
    for tool in tools:
        tool.invoke({} if tool.name == "list_frozen_snapshots" else {"repository": ADAPTER})
    assert digest_tree(SNAPSHOT_ROOT) == before


def test_tool_arguments_are_narrow_and_read_only(tools):
    """Arguments only ever name a repository, a commit, or a file name."""
    for tool in tools:
        properties = tool.args_schema.model_json_schema().get("properties", {})
        assert set(properties) <= {
            "repository", "commit", "source_name",
        }, f"{tool.name} exposes unexpected arguments: {sorted(properties)}"
        assert "required" not in tool.args_schema.model_json_schema() or set(
            tool.args_schema.model_json_schema()["required"]
        ) <= {"repository"}


def test_missing_snapshot_root_is_handled(tmp_path: Path):
    tool = build_list_snapshots_tool(root=tmp_path / "absent")
    assert json.loads(tool.invoke({})) == {"snapshots": []}
    evidence_tool = build_snapshot_evidence_tool(root=tmp_path / "absent")
    payload = json.loads(evidence_tool.invoke({"repository": ADAPTER}))
    assert payload["found"] is False


# --- the workflow uses the tool ---------------------------------------------


def test_prose_workflow_invokes_the_snapshot_tool():
    """Phase E obtains the model card through the tool, not by reading files."""
    from provenancelens.prose import LLMProseExtractor
    from fixtures.phase_e_llm import CannedChatModel, claim_set, NO_CLAIM

    real_tool = build_readme_prose_tool(root=SNAPSHOT_ROOT)
    calls: list[dict] = []

    def tracking(repository: str, source_name: str = "README.md") -> str:
        calls.append({"repository": repository, "source_name": source_name})
        return real_tool.invoke({"repository": repository, "source_name": source_name})

    spy = StructuredTool.from_function(
        func=tracking,
        name=real_tool.name,
        description=real_tool.description,
        args_schema=real_tool.args_schema,
    )
    from provenancelens.pipeline import audit_repository_with_prose

    extractor = LLMProseExtractor(CannedChatModel(responses=[claim_set(NO_CLAIM)]))
    outcome = audit_repository_with_prose(
        ADAPTER, root=SNAPSHOT_ROOT, extractor=extractor, tool=spy
    )
    assert calls, "the LangChain tool must participate in the Phase E workflow"
    assert calls[0]["repository"] == ADAPTER
    assert outcome.report.chunks_processed >= 1
    assert outcome.decision.decision.value == "ADD"  # unchanged by empty prose
