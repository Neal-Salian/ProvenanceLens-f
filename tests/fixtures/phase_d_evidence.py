"""Shared builders for Phase D reasoning tests (structured Phase 3 evidence)."""

from __future__ import annotations

from provenancelens.schemas import (
    DeclaredLineage,
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from provenancelens.schemas.extraction import ExtractionIssue

A = "org/model-a"
B = "org/model-b"
C = "org/model-c"


def evidence(
    source_type: SourceType,
    source_name: str,
    parent: str,
    relation: object = None,
    reliability: Reliability = Reliability.HIGH,
    *,
    key_path: str | None = None,
    role: EvidenceRole = EvidenceRole.INDEPENDENT,
    explicitness: Explicitness = Explicitness.EXPLICIT,
    note: str | None = None,
) -> EvidenceItem:
    """One traceable evidence item (Phase 3 structured form)."""
    return EvidenceItem(
        source_type=source_type,
        role=role,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        reliability=reliability,
        source_name=source_name,
        candidate_parent=parent,
        relation=relation,  # type: ignore[arg-type]
        key_path=key_path,
        explicitness=explicitness,
        note=note,
    )


def declared(
    base_model: str | None = None,
    relation_raw: str | None = None,
    additional: tuple[str, ...] = (),
) -> DeclaredLineage:
    """Declared lineage (the audit subject) built like the Phase C extractor."""
    value: object = base_model
    if additional:
        value = [base_model, *additional] if base_model else list(additional)
    return DeclaredLineage.from_metadata({
        "base_model": value,
        "base_model_relation": relation_raw,
    })


def declared_item(
    base_model: str,
    relation_raw: str | None = None,
    source_name: str = "README.md",
) -> EvidenceItem:
    """A DECLARED evidence item, used to prove it never supports itself."""
    return EvidenceItem(
        source_type=SourceType.DECLARED_METADATA,
        role=EvidenceRole.DECLARED,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        reliability=Reliability.NOT_APPLICABLE,
        source_name=source_name,
        candidate_parent=base_model,
        relation_raw=relation_raw,
        key_path="base_model",
        explicitness=Explicitness.EXPLICIT,
    )


def issue(
    source_name: str = "train.yaml",
    message: str = "invalid YAML",
    severity: str = "error",
) -> ExtractionIssue:
    return ExtractionIssue(
        source_name=source_name, message=message, severity=severity  # type: ignore[arg-type]
    )


def adapter_evidence(parent: str, *, source_name: str = "adapter_config.json"):
    """Adapter config claim: explicit parent AND the adapter relation."""
    return evidence(
        SourceType.ADAPTER_CONFIG, source_name, parent, "adapter",
        Reliability.VERY_HIGH, key_path="base_model_name_or_path",
    )


def merge_evidence(parents, *, source_name: str = "mergekit_config.yml"):
    return [
        evidence(
            SourceType.MERGE_CONFIG, source_name, parent, "merge",
            Reliability.HIGH, key_path=f"models[{i}].model",
        )
        for i, parent in enumerate(parents)
    ]


def training_evidence(
    parent: str, *, relation: object = None, source_name: str = "train.yaml",
    key_path: str = "model_name_or_path",
):
    return evidence(
        SourceType.TRAINING_CONFIG, source_name, parent, relation,
        Reliability.HIGH, key_path=key_path,
    )
