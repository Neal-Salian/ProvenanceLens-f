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

    Repositories (notably merges) may declare several ``base_model`` values;
    the first lives in ``base_model`` for stable JSON output and the rest in
    ``additional_base_models``.
    """

    model_config = ConfigDict(extra="forbid")

    base_model: str | None = None
    relation_raw: str | None = None
    relation: Relation | None = None
    additional_base_models: list[str] = Field(default_factory=list)

    @property
    def base_models(self) -> list[str]:
        """All declared base models in declaration order."""
        if self.base_model is None:
            return list(self.additional_base_models)
        return [self.base_model, *self.additional_base_models]

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, object] | None) -> DeclaredLineage:
        if not isinstance(metadata, Mapping):
            return cls()
        models: list[str] = []
        raw_base = metadata.get("base_model")
        if isinstance(raw_base, str):
            if raw_base.strip():
                models = [raw_base.strip()]
        elif isinstance(raw_base, list):
            for entry in raw_base:
                name = _coerce_model_name(entry)
                if name is not None:
                    models.append(name)
        elif isinstance(raw_base, dict):
            name = _coerce_model_name(raw_base)
            if name is not None:
                models.append(name)
        relation_raw = metadata.get("base_model_relation")
        if not isinstance(relation_raw, str) or not relation_raw.strip():
            relation_raw = None
        else:
            relation_raw = relation_raw.strip()
        return cls(
            base_model=models[0] if models else None,
            additional_base_models=models[1:],
            relation_raw=relation_raw,
            relation=Relation.normalize(relation_raw),
        )


def _coerce_model_name(entry: object) -> str | None:
    """Accept plain strings and ``{name: ...}`` dict forms; reject the rest."""
    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    if isinstance(entry, dict):
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None
