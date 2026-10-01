"""Component ablations for the Phase G experimental study.

Every ablation here is an **evaluation-side input transformation**: the
production decision engine, its policies, its fusion weights and its
parsers are untouched.  An ablation removes, flattens or duplicates the
evidence handed to the engine and re-runs the very same code path, so a
difference in the metrics can only be attributed to the evidence
component being ablated - never to a reimplementation of the system.

Why input transforms rather than edited engine code:

* it keeps the Phase B-E behaviour bit-for-bit identical (verifiable with a
  production diff against the merge base);
* it makes every ablation cheap, deterministic and offline;
* it forces each ablation to state *what evidence it removes*, which is the
  scientific question RQ4-RQ8 actually ask.

Ablations are grouped by the research question they serve:

===========================  ===========================================
Ablation                     Question
===========================  ===========================================
``no_prose``                 How much does model-card prose contribute?
``no_config``                How much does framework config contribute?
``no_tool_configs``          How much do adapter/merge/training files?
``only_tool_configs``        Are they sufficient on their own?
``inflate_duplicates``       What does per-file deduplication buy?
``flatten_reliability``      Does tiered reliability matter vs equal tiers?
``no_relation_evidence``     How much does relation evidence matter?
``highest_priority_only``    Is a fixed source hierarchy sufficient?
``only_highest_reliability`` Does the best single item decide?
===========================  ===========================================

Every ablation is registered in :data:`ABLATIONS` with a documented
rationale, and :func:`run_ablations` evaluates all of them (plus the
untransformed ``full`` reference) on the same benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from ..reasoning import DEFAULT_POLICY, DecisionPolicy, decide_lineage
from ..schemas.evidence import EvidenceItem, EvidenceRole, Reliability, SourceType
from .dataset import load_benchmark
from .metrics import compute_metrics
from .runner import case_inputs, decide_case, score_decision
from .schema import BenchmarkCase, CaseResult, Track

__all__ = [
    "AblationSpec",
    "ABLATIONS",
    "ABLATION_NAMES",
    "apply_ablation",
    "run_ablations",
    "ablation_table",
]

_TOOL_TYPES = frozenset(
    {SourceType.ADAPTER_CONFIG, SourceType.MERGE_CONFIG, SourceType.TRAINING_CONFIG}
)
_PROSE_TYPES = frozenset({SourceType.README, SourceType.OTHER})

#: Highest priority present in the evidence, in the documented source order.
_SOURCE_ORDER: tuple[SourceType, ...] = (
    SourceType.ADAPTER_CONFIG,
    SourceType.MERGE_CONFIG,
    SourceType.TRAINING_CONFIG,
    SourceType.CONFIG,
    SourceType.README,
    SourceType.OTHER,
)

_RELIABILITY_ORDER: tuple[Reliability, ...] = (
    Reliability.VERY_HIGH,
    Reliability.HIGH,
    Reliability.MEDIUM_HIGH,
    Reliability.MEDIUM,
    Reliability.WEAK,
)


def _copy(item: EvidenceItem, **changes) -> EvidenceItem:
    """Copy an evidence item with field overrides (pydantic model)."""
    return item.model_copy(update=changes)


def _drop_types(types: frozenset[SourceType]) -> Callable[[Sequence[EvidenceItem]], list]:
    def transform(evidence: Sequence[EvidenceItem]) -> list:
        return [item for item in evidence if item.source_type not in types]

    return transform


def _only_types(types: frozenset[SourceType]) -> Callable[[Sequence[EvidenceItem]], list]:
    def transform(evidence: Sequence[EvidenceItem]) -> list:
        return [item for item in evidence if item.source_type in types]

    return transform


def _inflate_duplicates(evidence: Sequence[EvidenceItem]) -> list:
    """Pretend every record came from its own file.

    The production fusion counts *independent sources* per file and caps
    per-file contributions.  Cloning items under distinct source names
    simulates a naive implementation that trusts raw record counts, which
    is exactly the failure mode the independence grouping prevents.
    """
    inflated: list = []
    for item in evidence:
        inflated.append(item)
        if item.role is EvidenceRole.INDEPENDENT:
            for index in range(2):
                inflated.append(
                    _copy(
                        item,
                        source_name=f"{item.source_name}#naive-{index}",
                        key_path=f"{item.key_path}#naive-{index}"
                        if item.key_path else None,
                    )
                )
    return inflated


def _flatten_reliability(evidence: Sequence[EvidenceItem]) -> list:
    """Give every independent item the same reliability tier.

    Fusion weights are a function of reliability, so collapsing the tiers
    approximates an equal-weight scheme without touching the engine.
    """
    return [
        _copy(item, reliability=Reliability.MEDIUM)
        if item.role is EvidenceRole.INDEPENDENT
        else item
        for item in evidence
    ]


def _strip_relation(evidence: Sequence[EvidenceItem]) -> list:
    """Remove every relation attached to the evidence."""
    return [_copy(item, relation=None) for item in evidence]


def _highest_priority_only(evidence: Sequence[EvidenceItem]) -> list:
    """Keep only evidence from the single highest-priority source present."""
    present = {item.source_type for item in evidence}
    for source in _SOURCE_ORDER:
        if source in present:
            return [item for item in evidence if item.source_type == source]
    return list(evidence)


def _only_highest_reliability(evidence: Sequence[EvidenceItem]) -> list:
    """Keep only the single best reliability tier present."""
    present = {item.reliability for item in evidence}
    for tier in _RELIABILITY_ORDER:
        if tier in present:
            return [item for item in evidence if item.reliability == tier]
    return list(evidence)


@dataclass(frozen=True)
class AblationSpec:
    """One named, documented evidence transformation."""

    name: str
    question: str
    hypothesis: str
    transform: Callable[[Sequence[EvidenceItem]], list]
    #: Ablations that drop evidence may make a declared lineage unverifiable;
    #: ``True`` when the transformation preserves independence semantics.
    preserves_independence: bool = True

    def apply(self, evidence: Sequence[EvidenceItem]) -> list:
        return list(self.transform(list(evidence)))

    def describe(self) -> dict:
        return {
            "name": self.name,
            "question": self.question,
            "hypothesis": self.hypothesis,
            "preserves_independence": self.preserves_independence,
        }


#: The registered ablation suite.  Order is fixed for deterministic reports.
ABLATIONS: tuple[AblationSpec, ...] = (
    AblationSpec(
        name="no_prose",
        question="RQ4: how much of the decision comes from model-card prose?",
        hypothesis="Prose is a supporting signal, not a deciding one: removing it "
                   "should not create a false repair.",
        transform=_drop_types(_PROSE_TYPES),
    ),
    AblationSpec(
        name="no_config",
        question="RQ4: how much does framework config contribute?",
        hypothesis="config.json-style evidence is the main structured signal and "
                   "should matter more than prose.",
        transform=_drop_types({SourceType.CONFIG}),
    ),
    AblationSpec(
        name="no_tool_configs",
        question="RQ4: how much do adapter/merge/training files contribute?",
        hypothesis="These files carry the strongest lineage signal; removing them "
                   "should cost recall on adapter and merge cases.",
        transform=_drop_types(_TOOL_TYPES),
    ),
    AblationSpec(
        name="only_tool_configs",
        question="RQ4: are adapter/merge/training files sufficient alone?",
        hypothesis="They are necessary but not sufficient: prose and config resolve "
                   "cases whose lineage is only documented in the model card.",
        transform=_only_types(_TOOL_TYPES),
    ),
    AblationSpec(
        name="inflate_duplicates",
        question="RQ5: what does per-file deduplication buy?",
        hypothesis="Naive record counting inflates support with repeated mentions "
                   "and should produce over-confident repair attempts.",
        transform=_inflate_duplicates,
        preserves_independence=False,
    ),
    AblationSpec(
        name="flatten_reliability",
        question="RQ6: does tiered reliability matter versus equal tiers?",
        hypothesis="Tiered reliability separates tool-generated lineage from model-card "
                   "claims, so flattening it should cost precision.",
        transform=_flatten_reliability,
    ),
    AblationSpec(
        name="no_relation_evidence",
        question="RQ7: how much does relation evidence matter?",
        hypothesis="Relations are rarely provable from artifacts alone; removing them "
                   "should shift repair actions toward parent-only changes.",
        transform=_strip_relation,
    ),
    AblationSpec(
        name="highest_priority_only",
        question="RQ8: is a fixed source hierarchy sufficient?",
        hypothesis="A single source hierarchy cannot express conflicts, so accuracy "
                   "should drop relative to conflict-aware fusion.",
        transform=_highest_priority_only,
    ),
    AblationSpec(
        name="only_highest_reliability",
        question="RQ8: does the single best item decide?",
        hypothesis="Taking only the strongest item discards corroboration and "
                   "should cost precision.",
        transform=_only_highest_reliability,
    ),
)

ABLATION_NAMES: tuple[str, ...] = tuple(spec.name for spec in ABLATIONS)


def apply_ablation(
    case: BenchmarkCase, spec: AblationSpec, *, policy: DecisionPolicy = DEFAULT_POLICY
):
    """Run the unmodified engine on ablated evidence for one case."""
    if spec.name == "full":
        return decide_case(case, policy=policy)
    declared, evidence, issues = case_inputs(case)
    ablated = spec.apply(evidence)
    candidates = None
    if issues:
        from ..reasoning import aggregate_candidates

        candidates = aggregate_candidates(ablated, issues=issues)
    result = decide_lineage(
        case.repository or case.case_id, declared, ablated, policy=policy,
        candidates=candidates,
    )
    return result.decision


def _ablation_results(
    cases: Sequence[BenchmarkCase], spec: AblationSpec, policy: DecisionPolicy
) -> list[CaseResult]:
    return [
        score_decision(
            case,
            apply_ablation(case, spec, policy=policy),
            system=spec.name if spec.name != "full" else "provenancelens",
        )
        for case in cases
    ]


def run_ablations(
    cases: Sequence[BenchmarkCase] | None = None,
    *,
    policy: DecisionPolicy = DEFAULT_POLICY,
    track: Track | None = None,
    include_full: bool = True,
) -> dict:
    """Evaluate the full system and every ablation on the same benchmark.

    Returns a mapping ``{ablation name: {"results": [...], "metrics": {...}}}``
    where ``metrics`` are the *same* Phase F metrics used everywhere else, so
    ablation deltas are directly comparable to the headline numbers.
    """
    benchmark = list(cases if cases is not None else load_benchmark())
    if track is not None:
        benchmark = [case for case in benchmark if case.track is track]
    selected: list[AblationSpec] = []
    if include_full:
        selected.append(
            AblationSpec(
                name="full", question="reference run, no transformation",
                hypothesis="baseline for every ablation delta",
                transform=lambda evidence: list(evidence),
            )
        )
    selected.extend(ABLATIONS)

    out: dict = {}
    for spec in selected:
        results = _ablation_results(benchmark, spec, policy)
        out[spec.name] = {
            "description": spec.describe(),
            "results": results,
            "metrics": compute_metrics(
                results, system=spec.name if spec.name != "full" else "provenancelens"
            ),
        }
    return out


def ablation_table(ablation_runs: dict, *, track: str | None = None) -> list[dict]:
    """One flat row per ablation with the headline metrics and deltas.

    Deltas are always measured against the ``full`` run of the *same* block, so
    a per-track table compares like with like.
    """
    full_metrics = ablation_runs.get("full", {}).get("metrics")
    full_block = None
    if full_metrics is not None:
        full_block = full_metrics if track is None else full_metrics["by_track"][track]
    rows = []
    for name, run in ablation_runs.items():
        metrics = run["metrics"]
        block = metrics if track is None else metrics["by_track"][track]
        row = {
            "ablation": name,
            "n_cases": block["n_cases"],
            "action_accuracy": block["action"]["accuracy"]["value"],
            "action_correct": block["action"]["accuracy"]["numerator"],
            "macro_f1": block["action"]["macro_f1"]["value"],
            "coverage": block["coverage"]["value"],
            "attempted_repairs": block["repair_safety"]["attempted_repairs"]["numerator"],
            "false_repairs": block["repair_safety"]["false_repairs"]["numerator"],
            "false_repair_rate": block["repair_safety"]["false_repairs"]["value"],
            "parent_accuracy": block["parent"]["value"],
            "relation_accuracy": block["relation"]["accuracy"]["value"],
        }
        if full_block is not None:
            row["delta_action_accuracy"] = (
                row["action_accuracy"] - full_block["action"]["accuracy"]["value"]
            )
            row["delta_false_repairs"] = (
                row["false_repairs"] - full_block["repair_safety"]["false_repairs"]["numerator"]
            )
        rows.append(row)
    return rows

