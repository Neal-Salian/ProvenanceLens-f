"""Bundle-level extraction: declared subject vs independent evidence.

Implements the core architectural rule of Phase 3: declared metadata is
extracted separately and can NEVER appear in the independent-evidence list.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..schemas.evidence import EvidenceItem
from ..schemas.lineage import DeclaredLineage
from .configs import extract_config_evidence
from .metadata import extract_declared_metadata
from .prose import extract_prose_claims


def _repository_of(bundle: Mapping[str, object]) -> str | None:
    model_id = bundle.get("model_id")
    return model_id if isinstance(model_id, str) else None


def _revision_of(bundle: Mapping[str, object]) -> str | None:
    revision = bundle.get("revision")
    return revision if isinstance(revision, str) else None


def extract_declared(bundle: object) -> tuple[DeclaredLineage, EvidenceItem | None]:
    """Extract the declared metadata (audit subject) from an evidence bundle."""
    if not isinstance(bundle, Mapping):
        return DeclaredLineage(), None
    return extract_declared_metadata(
        bundle.get("metadata"),
        repository=_repository_of(bundle),
        revision=_revision_of(bundle),
    )


def extract_independent_evidence(bundle: object) -> list[EvidenceItem]:
    """Extract INDEPENDENT evidence (configs + README prose) from a bundle.

    Declared metadata is deliberately excluded — it is the subject of the
    audit, not proof for the audit. Returns an empty list for malformed
    bundles instead of raising.
    """
    if not isinstance(bundle, Mapping):
        return []
    repository = _repository_of(bundle)
    revision = _revision_of(bundle)
    items: list[EvidenceItem] = []
    items.extend(
        extract_config_evidence(
            bundle.get("config"),
            source_name="config.json",
            repository=repository,
            revision=revision,
        )
    )
    items.extend(
        extract_prose_claims(
            bundle.get("readme"),
            repository=repository,
            revision=revision,
        )
    )
    return items
