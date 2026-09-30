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


# ---- Repository-level (Phase 3) extraction -------------------------------

from pathlib import PurePosixPath  # noqa: E402

from ..schemas.evidence import SourceType  # noqa: E402
from ..schemas.extraction import EvidenceExtraction, ExtractionIssue  # noqa: E402
from .adapter import extract_adapter_evidence  # noqa: E402
from .frontmatter import extract_declared_from_readme, split_front_matter  # noqa: E402
from .merge import extract_merge_evidence  # noqa: E402
from .structured import load_json_text  # noqa: E402
from .training import extract_training_evidence  # noqa: E402

# Priority configs routed through the generic structured-config extractor.
_CONFIG_NAMES = frozenset({"config.json", "tokenizer_config.json", "generation_config.json"})
_JSON_LIKE = frozenset({".json", ".yaml", ".yml"})
_TEXT_LIKE = frozenset({".md", ".txt"})


def _merge_declared(target: DeclaredLineage, incoming: DeclaredLineage) -> DeclaredLineage:
    """Union of declared base models (order-preserving, de-duplicated)."""
    if not incoming.base_models and incoming.relation_raw is None:
        return target
    models = list(target.base_models)
    for model in incoming.base_models:
        if model not in models:
            models.append(model)
    return DeclaredLineage(
        base_model=models[0] if models else None,
        additional_base_models=models[1:],
        relation_raw=target.relation_raw or incoming.relation_raw,
        relation=target.relation or incoming.relation,
    )


def extract_repository_evidence(
    repository: str,
    resolved_commit_sha: str | None,
    contents: Mapping[str, object],
    *,
    requested_revision: str | None = None,
) -> EvidenceExtraction:
    """Route every collected file to its parser; separate declared vs independent.

    Deterministic: files are processed in sorted order and no timestamps are
    recorded, so identical snapshot inputs always produce identical output.
    """
    revision = resolved_commit_sha or requested_revision
    declared = DeclaredLineage()
    declared_items: list[EvidenceItem] = []
    independent: list[EvidenceItem] = []
    issues: list[ExtractionIssue] = []

    for filename in sorted(contents):
        text = contents[filename]
        if not isinstance(text, str):
            issues.append(ExtractionIssue(
                source_name=filename, message="file content is not text",
                severity="warning",
            ))
            continue
        name = PurePosixPath(filename).name.lower()
        suffix = PurePosixPath(filename).suffix.lower()

        if name == "readme.md":
            lineage, items, warns = extract_declared_from_readme(
                text, source_name=filename,
                repository=repository, revision=revision,
            )
            issues.extend(warns)
            declared = _merge_declared(declared, lineage)
            declared_items.extend(items)
            body, _ = split_front_matter(text)
            independent.extend(extract_prose_claims(
                body, source_type=SourceType.README, source_name=filename,
                repository=repository, revision=revision,
            ))
        elif name == "adapter_config.json":
            items, warns = extract_adapter_evidence(
                text, source_name=filename,
                repository=repository, revision=revision,
            )
            independent.extend(items)
            issues.extend(warns)
        elif name in _CONFIG_NAMES:
            data, issue = load_json_text(text, source_name=filename)
            if issue is not None:
                issues.append(issue)
            elif data is not None:
                independent.extend(extract_config_evidence(
                    data, source_name=filename, source_type=SourceType.CONFIG,
                    repository=repository, revision=revision,
                ))
        elif suffix in _JSON_LIKE and "merge" in name:
            items, warns = extract_merge_evidence(
                text, source_name=filename,
                repository=repository, revision=revision,
            )
            independent.extend(items)
            issues.extend(warns)
        elif suffix in (".yaml", ".yml"):
            items, warns = extract_training_evidence(
                text, source_name=filename, fmt="yaml",
                source_type=SourceType.TRAINING_CONFIG,
                repository=repository, revision=revision,
            )
            independent.extend(items)
            issues.extend(warns)
        elif suffix == ".json":
            items, warns = extract_training_evidence(
                text, source_name=filename, fmt="json",
                source_type=SourceType.TRAINING_CONFIG,
                repository=repository, revision=revision,
            )
            independent.extend(items)
            issues.extend(warns)
        elif suffix in _TEXT_LIKE:
            independent.extend(extract_prose_claims(
                text, source_type=SourceType.OTHER, source_name=filename,
                repository=repository, revision=revision,
            ))
        else:
            issues.append(ExtractionIssue(
                source_name=filename,
                message=f"unsupported file type '{suffix or name}'",
                severity="warning",
            ))

    return EvidenceExtraction(
        repository=repository,
        resolved_commit_sha=resolved_commit_sha,
        declared_lineage=declared,
        declared_evidence=declared_items,
        independent_evidence=independent,
        issues=issues,
    )
