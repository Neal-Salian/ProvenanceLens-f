"""Regression: the five Phase 2 scenarios must behave exactly as the notebook.

These tests compare the extracted legacy engine against full result dicts
captured by executing the ORIGINAL notebook — not against values adjusted to
fit the refactor.
"""

from __future__ import annotations

import json

import pytest

from provenancelens.reasoning.legacy import audit, extract_evidence
from provenancelens.reporting import format_results_table, to_json
from fixtures.phase2_samples import (
    PHASE2_EXPECTED,
    PHASE2_EXPECTED_ACTIONS,
    PHASE2_SAMPLES,
)

IDS = [sample["model_id"] for sample in PHASE2_SAMPLES]


@pytest.mark.parametrize(
    "sample,expected",
    list(zip(PHASE2_SAMPLES, PHASE2_EXPECTED, strict=True)),
    ids=IDS,
)
def test_phase2_scenario_full_output(sample, expected):
    assert audit(sample) == expected


@pytest.mark.parametrize("expected_action", PHASE2_EXPECTED_ACTIONS, ids=IDS)
def test_phase2_expected_actions(expected_action):
    """Approved decision sequence: ADD, REPLACE, KEEP, ABSTAIN, ABSTAIN."""
    results = [audit(sample) for sample in PHASE2_SAMPLES]
    assert [r["action"] for r in results] == PHASE2_EXPECTED_ACTIONS


def test_phase2_claim_extraction_shape():
    """Legacy extraction keeps its claim structure (weights, sources, labels)."""
    item = extract_evidence(PHASE2_SAMPLES[1])
    assert item["claims"] == [
        {"parent": "mistralai/Mistral-7B-v0.1", "relation": "fine-tune", "source": "metadata", "weight": 0},
        {"parent": "meta-llama/Llama-3.2-1B", "relation": "fine-tune", "source": "config.json", "weight": 3},
        {"parent": "meta-llama/Llama-3.2-1B", "relation": "fine-tune", "source": "README", "weight": 2},
    ]


def test_phase2_results_table_format():
    """The notebook's summary table is reproducible from the package."""
    results = [audit(sample) for sample in PHASE2_SAMPLES]
    table = format_results_table(results)
    lines = table.splitlines()
    assert lines[0] == f"{'MODEL':38} {'ACTION':9} {'PARENT':32} CONFIDENCE"
    assert lines[1] == "-" * 94
    assert lines[2].startswith("demo/missing-lineage-model")
    assert "ADD" in lines[2] and "0.90" in lines[2]
    assert lines[6].startswith("demo/tool-failure-model")
    assert "ABSTAIN" in lines[6] and "0.10" in lines[6]


def test_phase2_structured_json_output():
    """The notebook's REPLACE JSON example round-trips through to_json."""
    results = [audit(sample) for sample in PHASE2_SAMPLES]
    parsed = json.loads(to_json(results[1]))
    assert parsed == PHASE2_EXPECTED[1]
    assert parsed["action"] == "REPLACE"
    assert parsed["confidence"] == 0.9
    assert parsed["supporting_evidence"][0].startswith("config.json:")


def test_phase2_extract_does_not_mutate_input():
    sample = dict(PHASE2_SAMPLES[0])
    original = json.loads(json.dumps(sample))
    extract_evidence(sample)
    assert sample == original
