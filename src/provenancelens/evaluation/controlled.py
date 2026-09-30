"""LineageRepairBench CONTROLLED track: frozen synthetic cases.

Every case is built from an explicit evidence bundle and labelled **by
construction**: the ground truth is what a careful auditor would conclude from
that evidence, written down independently of ProvenanceLens. Nothing here
calls the decision engine (see :mod:`provenancelens.evaluation.validation`),
and where the conservative policy may plausibly differ from intuition the
label records *why* that expectation was chosen.

The track deliberately covers the situations that matter for repair safety:
strong contradiction, single-source evidence, correlated fields, ambiguity,
tool failures, merge sets, and prose that is not lineage.
"""

from __future__ import annotations

from ..schemas.audit import Decision
from ..schemas.evidence import (
    EvidenceItem,
    EvidenceRole,
    Explicitness,
    ExtractionMethod,
    Reliability,
    SourceType,
)
from ..schemas.lineage import Relation
from .schema import (
    Adjudication,
    BenchmarkCase,
    GroundTruth,
    LabelProvenance,
    MetadataState,
    Track,
    TruthStatus,
)

__all__ = ["CONTROLLED_CASES", "build_controlled_benchmark", "CONTROLLED_ADJUDICATOR"]

CONTROLLED_ADJUDICATOR = "Phase F controlled benchmark (synthetic construction)"

A = "org/model-a"
B = "org/model-b"
C = "org/model-c"


def _adjudication() -> Adjudication:
    return Adjudication(
        provenance=LabelProvenance.SYNTHETIC_CONSTRUCTION,
        adjudicator=CONTROLLED_ADJUDICATOR,
        notes="label follows from the constructed evidence bundle",
    )


def _ev(
    source_type: SourceType,
    source_name: str,
    parent: str,
    relation: Relation | None = None,
    reliability: Reliability = Reliability.HIGH,
    *,
    key_path: str | None = None,
    explicitness: Explicitness = Explicitness.EXPLICIT,
) -> EvidenceItem:
    return EvidenceItem(
        source_type=source_type,
        role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        reliability=reliability,
        source_name=source_name,
        candidate_parent=parent,
        relation=relation,
        key_path=key_path,
        explicitness=explicitness,
    )


def _training(parent: str, relation: Relation | None = None, *, name: str = "train.yaml",
              key_path: str = "model_name_or_path") -> EvidenceItem:
    return _ev(SourceType.TRAINING_CONFIG, name, parent, relation,
               Reliability.HIGH, key_path=key_path)


def _adapter(parent: str, *, name: str = "adapter_config.json") -> EvidenceItem:
    return _ev(SourceType.ADAPTER_CONFIG, name, parent, Relation.ADAPTER,
               Reliability.VERY_HIGH, key_path="base_model_name_or_path")


def _merge(items: list[str], *, name: str = "mergekit_config.yml") -> list[EvidenceItem]:
    return [
        _ev(SourceType.MERGE_CONFIG, name, parent, Relation.MERGE,
            Reliability.HIGH, key_path=f"models[{index}].model")
        for index, parent in enumerate(items)
    ]


def _prose(parent: str | None, relation: Relation | None, span: str | None, *,
           reliability: Reliability = Reliability.MEDIUM,
           name: str = "README.md",
           implicitness: Explicitness = Explicitness.EXPLICIT) -> EvidenceItem:
    return EvidenceItem(
        source_type=SourceType.README,
        role=EvidenceRole.INDEPENDENT,
        extraction_method=ExtractionMethod.RULE_BASED,
        reliability=reliability,
        source_name=name,
        candidate_parent=parent,
        relation=relation,
        evidence_span=span,
        key_path="prose[chunk 0]",
        explicitness=implicitness,
    )


def _config(parent: str, *, name: str = "config.json") -> EvidenceItem:
    return _ev(SourceType.CONFIG, name, parent, None, Reliability.MEDIUM,
               key_path="_name_or_path")


_ERROR_ISSUE = {"source_name": "train_eval.yaml", "message": "invalid YAML: parse error",
                "severity": "error"}
_PARSE_ISSUE = {"source_name": "adapter_extra.json", "message": "unsupported shape",
                "severity": "error"}


def _case(
    case_id: str,
    title: str,
    *,
    evidence: list[EvidenceItem],
    truth: GroundTruth,
    expected_action: Decision,
    acceptable: tuple[Decision, ...] = (),
    declared_base_model: str | None = None,
    declared_relation_raw: str | None = None,
    declared_additional: tuple[str, ...] = (),
    issues: tuple[dict, ...] = (),
    repairable: bool = True,
    tags: tuple[str, ...] = (),
) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case_id,
        track=Track.CONTROLLED,
        title=title,
        evidence=tuple(evidence),
        issues=issues,
        declared_base_model=declared_base_model,
        declared_relation_raw=declared_relation_raw,
        declared_additional_base_models=declared_additional,
        truth=truth,
        expected_action=expected_action,
        acceptable_actions=acceptable or (expected_action,),
        adjudication=_adjudication(),
        repairable=repairable,
        tags=tags,
    )


def _known(parents: tuple[str, ...] | None, relation: Relation | None, state: MetadataState,
           rationale: str) -> GroundTruth:
    return GroundTruth(
        parents=parents,
        parents_status=TruthStatus.KNOWN if parents is not None else TruthStatus.UNKNOWN,
        relation=relation,
        relation_status=TruthStatus.KNOWN if relation is not None else TruthStatus.UNKNOWN,
        metadata_state=state,
        rationale=rationale,
    )


def _undetermined(rationale: str, *, relation_status: TruthStatus = TruthStatus.UNKNOWN,
                  parents: tuple[str, ...] | None = None,
                  parents_status: TruthStatus = TruthStatus.UNKNOWN,
                  alternatives: tuple[tuple[str, ...], ...] = (),
                  relation: Relation | None = None) -> GroundTruth:
    return GroundTruth(
        parents=parents,
        parents_status=parents_status,
        relation=relation,
        relation_status=relation_status,
        metadata_state=MetadataState.UNDETERMINED,
        parent_set_alternatives=alternatives,
        rationale=rationale,
    )


CONTROLLED_CASES: list[BenchmarkCase] = [
    # --- KEEP -------------------------------------------------------------
    _case(
        "CONTROLLED-01-keep-finetune",
        "Declared finetune corroborated by a training config and the model card",
        evidence=[
            _training(A, Relation.FINETUNE),
            _prose(A, Relation.FINETUNE, f"This model was fine-tuned from {A}."),
        ],
        truth=_known((A,), Relation.FINETUNE, MetadataState.VALID,
                     "two independent artifacts name the declared parent and relation"),
        expected_action=Decision.KEEP,
        tags=("keep", "single-parent"),
    ),
    _case(
        "CONTROLLED-02-keep-adapter-single-very-high",
        "Declared adapter corroborated by one explicit VERY_HIGH artifact",
        evidence=[_adapter(A)],
        truth=_known((A,), Relation.ADAPTER, MetadataState.VALID,
                     "adapter_config records the base model the adapter was trained on"),
        expected_action=Decision.KEEP,
        tags=("keep", "single-source"),
    ),
    _case(
        "CONTROLLED-13-keep-merge-exact",
        "Declared merge set equals the independently observed merge sources",
        evidence=_merge([A, B]),
        truth=_known((A, B), Relation.MERGE, MetadataState.VALID,
                     "merge configuration lists exactly the declared source set"),
        expected_action=Decision.KEEP,
        tags=("keep", "merge", "set-semantics"),
    ),
    _case(
        "CONTROLLED-18-keep-with-noisy-irrelevant-evidence",
        "Strong agreement survives several irrelevant weak hints",
        evidence=[
            _training(A, Relation.FINETUNE),
            _prose(B, Relation.FINETUNE, f"Fine-tuned from {B}.", reliability=Reliability.WEAK,
                   name="NOTES.md"),
            _prose(C, Relation.FINETUNE, f"Fine-tuned from {C}.", reliability=Reliability.WEAK,
                   name="EVAL.md"),
        ],
        truth=_known((A,), Relation.FINETUNE, MetadataState.VALID,
                     "declared parent is corroborated; weak hints are below the conflict bar"),
        expected_action=Decision.KEEP,
        tags=("keep", "noise"),
    ),
    _case(
        "CONTROLLED-25-keep-merge-subset-no-narrowing",
        "Observed merge sources are a subset of the declared set",
        evidence=_merge([A, B]),
        truth=_undetermined(
            "the third declared source has no independent corroboration; absence of "
            "corroboration is not evidence of error",
            relation=Relation.MERGE, relation_status=TruthStatus.KNOWN,
            parents=(A, B, C), parents_status=TruthStatus.AMBIGUOUS,
            alternatives=((A, B, C), (A, B)),
        ),
        expected_action=Decision.KEEP,
        acceptable=(Decision.KEEP, Decision.ABSTAIN),
        declared_base_model=A, declared_relation_raw="merge", declared_additional=(B, C),
        tags=("keep", "merge", "ambiguous"),
    ),

    # --- ADD --------------------------------------------------------------
    _case(
        "CONTROLLED-03-add-adapter-very-high",
        "No declared lineage, one explicit VERY_HIGH adapter parent",
        evidence=[_adapter(A)],
        truth=_known((A,), Relation.ADAPTER, MetadataState.MISSING,
                     "metadata is absent and adapter_config states the parent and relation"),
        expected_action=Decision.ADD,
        tags=("add", "single-source"),
    ),
    _case(
        "CONTROLLED-12-add-despite-tool-failure",
        "Retrieval/parse failure of an unrelated artifact does not block a safe ADD",
        evidence=[_adapter(A)],
        issues=(_ERROR_ISSUE,),
        truth=_known((A,), Relation.ADAPTER, MetadataState.MISSING,
                     "the failing artifact is unrelated; adapter_config is unaffected"),
        expected_action=Decision.ADD,
        tags=("add", "tool-failure"),
    ),
    _case(
        "CONTROLLED-14-add-merge-missing-metadata",
        "No declared lineage, explicit merge configuration with two sources",
        evidence=_merge([A, B]),
        truth=_known((A, B), Relation.MERGE, MetadataState.MISSING,
                     "merge configuration states both direct sources"),
        expected_action=Decision.ADD,
        tags=("add", "merge"),
    ),
    _case(
        "CONTROLLED-17-add-duplicate-single-source",
        "Repeating one artifact must not change the decision",
        evidence=[_adapter(A), _adapter(A, name="adapter_config.json"),
                  _adapter(A, name="adapter_config.json")],
        truth=_known((A,), Relation.ADAPTER, MetadataState.MISSING,
                     "three records of one file are one source, not three"),
        expected_action=Decision.ADD,
        tags=("add", "duplicates"),
    ),

    # --- REPLACE ----------------------------------------------------------
    _case(
        "CONTROLLED-04-replace-wrong-parent-decisive",
        "Declared parent contradicted by decisive independent evidence",
        evidence=[
            _adapter(B),
            _training(B, Relation.FINETUNE, key_path="base_model_or_path"),
        ],
        truth=_known((B,), Relation.ADAPTER, MetadataState.INCORRECT,
                     "two tool-generated artifacts name a different parent than declared"),
        expected_action=Decision.REPLACE,
        tags=("replace",),
    ),
    _case(
        "CONTROLLED-26-replace-wrong-parent-three-sources",
        "Declared parent contradicted by three independent artifacts",
        evidence=[
            _adapter(B),
            _training(B, Relation.ADAPTER, key_path="base_model_or_path"),
            _prose(B, Relation.ADAPTER, f"This adapter was trained on top of {B}."),
        ],
        truth=_known((B,), Relation.ADAPTER, MetadataState.INCORRECT,
                     "adapter config, training config and card prose all name B"),
        expected_action=Decision.REPLACE,
        tags=("replace", "multi-source"),
    ),

    # --- ABSTAIN ----------------------------------------------------------
    _case(
        "CONTROLLED-05-abstain-no-evidence",
        "Declared lineage with no independent evidence at all",
        evidence=[],
        truth=_undetermined("nothing independent supports or contradicts the declaration"),
        expected_action=Decision.ABSTAIN,
        declared_base_model=A, declared_relation_raw="finetune",
        tags=("abstain", "no-evidence"),
    ),
    _case(
        "CONTROLLED-06-abstain-competing-strong-candidates",
        "Two comparably supported parents and nothing declared",
        evidence=[_adapter(A), _adapter(B, name="adapter_config_b.json")],
        truth=_undetermined(
            "both parents have explicit support; choosing either would be a guess",
            parents_status=TruthStatus.AMBIGUOUS, alternatives=((A,), (B,)),
        ),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "competing"),
    ),
    _case(
        "CONTROLLED-07-abstain-ambiguous-identifier",
        "Bare model name without namespace or version",
        evidence=[_training("Mistral 7B")],
        truth=_undetermined(
            "several Mistral versions exist; the exact parent cannot be identified "
            "without querying a hub",
            parents_status=TruthStatus.UNKNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "ambiguity"),
    ),
    _case(
        "CONTROLLED-08-abstain-unknown-declared-relation",
        "Declared relation is not a supported canonical relation",
        evidence=[_training(A, Relation.FINETUNE)],
        truth=_undetermined(
            "base_model_relation 'blend' is not a supported relation; it must be "
            "preserved, never reinterpreted automatically",
            relation_status=TruthStatus.UNKNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        acceptable=(Decision.KEEP, Decision.ABSTAIN),
        declared_base_model=A, declared_relation_raw="blend",
        tags=("abstain", "unknown-relation"),
    ),
    _case(
        "CONTROLLED-09-abstain-relation-conflict",
        "Parent agrees but the declared relation contradicts weak evidence",
        evidence=[_adapter(A)],
        truth=_undetermined(
            "parent is corroborated but the relation is contradicted by a single "
            "artifact, which is not decisive",
            parents=(A,), parents_status=TruthStatus.KNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        acceptable=(Decision.KEEP, Decision.ABSTAIN),
        declared_base_model=A, declared_relation_raw="finetune",
        tags=("abstain", "relation-conflict"),
    ),
    _case(
        "CONTROLLED-10-abstain-config-hint-only",
        "Only a framework-written config hint names a parent",
        evidence=[_config(A)],
        truth=_undetermined(
            "_name_or_path records what a checkpoint was initialised from, not lineage "
            "intent, and no relation is stated",
            parents_status=TruthStatus.UNKNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "weak-evidence"),
    ),
    _case(
        "CONTROLLED-11-abstain-relation-never-stated",
        "Declared parent corroborated, relation unstated everywhere",
        evidence=[
            _training(A),
            _prose(A, None, f"We initialise from {A} and train on public data."),
        ],
        truth=_undetermined(
            "parent identity agrees but no evidence states the relationship, so a "
            "complete lineage cannot be certified",
            parents=(A,), parents_status=TruthStatus.KNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        acceptable=(Decision.KEEP, Decision.ABSTAIN),
        declared_base_model=A,
        tags=("abstain", "missing-relation"),
    ),
    _case(
        "CONTROLLED-15-abstain-failure-with-weak-evidence",
        "Retrieval failure plus only weak remaining evidence",
        evidence=[_prose(A, Relation.FINETUNE, f"This model was fine-tuned from {A}.")],
        issues=(_ERROR_ISSUE, _PARSE_ISSUE),
        truth=_known((A,), Relation.FINETUNE, MetadataState.MISSING,
                     "only one author-written sentence survives; a safe ADD needs more"),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "tool-failure"),
    ),
    _case(
        "CONTROLLED-16-abstain-correlated-training-fields",
        "Three fields of one training config are one source, not three",
        evidence=[
            _training(A, key_path="model_name_or_path"),
            _training(A, key_path="base_model"),
            _training(A, key_path="pretrained_model_name_or_path"),
        ],
        truth=_undetermined(
            "all three fields come from the same file and none states a relation",
            parents_status=TruthStatus.UNKNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "source-independence"),
    ),
    _case(
        "CONTROLLED-19-abstain-prose-mention-without-lineage",
        "Model card mentions another model but asserts no lineage",
        evidence=[_prose(B, None, f"We compare against {B} in the evaluation table.")],
        truth=_undetermined("a comparison is not a lineage statement"),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "prose"),
    ),
    _case(
        "CONTROLLED-20-abstain-prose-inspiration",
        "Architecture inspiration is not ancestry",
        evidence=[_prose(C, None, f"Our architecture is inspired by {C}.")],
        truth=_undetermined("inspiration is not a direct parent claim"),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "prose"),
    ),
    _case(
        "CONTROLLED-21-abstain-prose-acknowledgement",
        "Credits to another project are not lineage",
        evidence=[_prose(B, None, f"Thanks to the {B} team for inspiration.")],
        truth=_undetermined("an acknowledgement is not a direct parent claim"),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "prose"),
    ),
    _case(
        "CONTROLLED-22-abstain-prose-implicit-ambiguity",
        "LLM-flagged ambiguous prose claim with an unresolvable name",
        evidence=[_prose("Mistral 7B", None, "Built on Mistral 7B.",
                         reliability=Reliability.MEDIUM,
                         implicitness=Explicitness.IMPLICIT)],
        truth=_undetermined(
            "the prose names a base family but no version; identity is not resolvable",
            parents_status=TruthStatus.UNKNOWN,
        ),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "prose", "llm"),
    ),
    _case(
        "CONTROLLED-23-abstain-single-prose-claim",
        "One explicit prose sentence naming parent and relation",
        evidence=[_prose(A, Relation.FINETUNE, f"This model was fine-tuned from {A}.")],
        truth=_known((A,), Relation.FINETUNE, MetadataState.MISSING,
                     "the claim is explicit, but a single author-controlled sentence is "
                     "not sufficient authority for an automated ADD"),
        expected_action=Decision.ABSTAIN,
        tags=("abstain", "prose"),
    ),
    _case(
        "CONTROLLED-24-abstain-single-strong-source-contradiction",
        "One VERY_HIGH artifact contradicts a declared merge set",
        evidence=[_adapter(C)],
        truth=_undetermined(
            "a single source cannot decisively overrule a declared multi-parent merge",
            parents_status=TruthStatus.AMBIGUOUS, alternatives=((C,), (A, B)),
        ),
        expected_action=Decision.ABSTAIN,
        acceptable=(Decision.ABSTAIN,),
        declared_base_model=A, declared_relation_raw="merge", declared_additional=(B,),
        tags=("abstain", "merge", "contradiction"),
    ),
]


def build_controlled_benchmark() -> list[BenchmarkCase]:
    """Return a copy of the frozen CONTROLLED track."""
    return [case.model_copy(deep=True) for case in CONTROLLED_CASES]
