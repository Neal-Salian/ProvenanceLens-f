"""Lineage vocabulary and lineage value objects."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Relation(str, Enum):
    """Canonical direct-lineage relationships supported in Phase 3."""

    FINETUNE = "finetune"
    ADAPTER = "adapter"
    MERGE = "merge"
    QUANTIZED = "quantized"

    @classmethod
    def normalize(cls, value: object) -> Relation | None:
        """Map known vocabulary variants to the canonical relation.

        Returns ``None`` for missing or unknown values — unknown relationship
        text is NEVER silently accepted as a valid relation.
        """
        if isinstance(value, Relation):
            return value
        if not isinstance(value, str):
            return None
        key = value.strip().lower().replace("_", "-").replace(" ", "-")
        return _RELATION_ALIASES.get(key)


_RELATION_ALIASES: dict[str, Relation] = {
    "finetune": Relation.FINETUNE,
    "fine-tune": Relation.FINETUNE,
    "fine-tuned": Relation.FINETUNE,
    "finetuned": Relation.FINETUNE,
    "fine-tuning": Relation.FINETUNE,
    "finetuning": Relation.FINETUNE,
    "adapter": Relation.ADAPTER,
    "merge": Relation.MERGE,
    "merged": Relation.MERGE,
    "quantized": Relation.QUANTIZED,
    "quantised": Relation.QUANTIZED,
    "quantization": Relation.QUANTIZED,
    "quantisation": Relation.QUANTIZED,
}


class LineageEntry(BaseModel):
    """One direct lineage source (a merge can have several)."""

    model_config = ConfigDict(extra="forbid")

    parent: str = Field(min_length=1)
    relation: Relation | None = None


class Lineage(BaseModel):
    """Direct lineage as a list of sources.

    A list (rather than a single ``base_model`` slot) allows merge models to
    carry multiple direct source models without a schema rewrite.
    """

    model_config = ConfigDict(extra="forbid")

    entries: list[LineageEntry] = Field(default_factory=list)

    @property
    def parents(self) -> list[str]:
        return [entry.parent for entry in self.entries]

    @property
    def is_empty(self) -> bool:
        return not self.entries

    @classmethod
    def single(cls, parent: str, relation: Relation | None = None) -> Lineage:
        return cls(entries=[LineageEntry(parent=parent, relation=relation)])


class DeclaredLineage(BaseModel):
    """What the repository currently claims — the SUBJECT of the audit.

    ``relation_raw`` preserves the author-written value even when it does not
    map to a supported canonical relation (then ``relation`` is ``None``).
    """

    model_config = ConfigDict(extra="forbid")

    base_model: str | None = None
    relation_raw: str | None = None
    relation: Relation | None = None

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, object] | None) -> DeclaredLineage:
        if not isinstance(metadata, Mapping):
            return cls()
        base_model = metadata.get("base_model")
        if not isinstance(base_model, str) or not base_model.strip():
            base_model = None
        else:
            base_model = base_model.strip()
        relation_raw = metadata.get("base_model_relation")
        if not isinstance(relation_raw, str) or not relation_raw.strip():
            relation_raw = None
        else:
            relation_raw = relation_raw.strip()
        return cls(
            base_model=base_model,
            relation_raw=relation_raw,
            relation=Relation.normalize(relation_raw),
        )
