"""Offline demonstration: audit frozen repositories and print the decisions.

The demo is the fastest way to *see* what ProvenanceLens does.  It runs the
production decision engine over evidence that is already frozen in
``data/snapshots`` - no network, no Hugging Face, no Ollama, no model weights -
and prints, for each case:

* the repository and the exact pinned revision;
* the declared lineage (the metadata under audit);
* the strongest independent evidence, with its file and key path;
* detected conflicts;
* the support score (a heuristic evidence strength, **not** a probability);
* the decision - KEEP / ADD / REPLACE / ABSTAIN;
* the proposed parent and relation when one is proposed;
* and, when abstaining, which condition stopped the repair.

Nothing here is scripted or hand-written: every line is produced by running the
same engine the benchmark evaluates.  Cases are always labelled ``REAL``
(frozen public repository) or ``CONTROLLED`` (constructed edge case), because a
controlled case is a specification check and not evidence about the world.

Usage::

    python -m provenancelens.demo                 # curated walkthrough
    python -m provenancelens.demo --list          # every demo case, one line
    python -m provenancelens.demo --case REAL-Qwen/Qwen2.5-7B-Instruct-AWQ
"""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .evaluation.dataset import load_benchmark
from .evaluation.runner import case_inputs, decide_case
from .evaluation.schema import BenchmarkCase, Track
from .reasoning.fusion import ITEM_WEIGHTS
from .schemas.evidence import EvidenceItem, EvidenceRole

__all__ = ["DEMO_CASES", "demo_cases", "render_case", "main"]

#: The curated walkthrough.  Chosen to cover every decision, every relation the
#: system can propose, and both a safe repair and a refusal.  ``REPLACE`` has no
#: real frozen example - no real repository in the benchmark had *incorrect*
#: declared metadata that the evidence could safely correct - so it is shown as
#: a CONTROLLED case and labelled as such rather than faked.
DEMO_CASES: tuple[tuple[str, str], ...] = (
    ("REAL-peft-internal-testing/tiny-OPTForCausalLM-lora",
     "ADD: a real adapter whose declared metadata was missing"),
    ("REAL-mergekit-community/Qwen3-1.5B-Instruct",
     "KEEP: a real merge whose declared metadata already matches the evidence"),
    ("CONTROLLED-14-add-merge-missing-metadata",
     "ADD (merge): a controlled merge whose configuration states the parents"),
    ("CONTROLLED-04-replace-wrong-parent-decisive",
     "REPLACE: a controlled case where declared metadata is demonstrably wrong"),
    ("CONTROLLED-06-abstain-competing-strong-candidates",
     "ABSTAIN: two equally strong candidates, so no safe choice exists"),
    ("REAL-Qwen/Qwen2.5-7B-Instruct-AWQ",
     "ABSTAIN: a real quantized derivative whose card states lineage but no "
     "artifact does - the system's main coverage gap"),
)


def demo_cases(benchmark: Sequence[BenchmarkCase] | None = None) -> list[BenchmarkCase]:
    """Resolve :data:`DEMO_CASES` against the benchmark, skipping absent ones."""
    cases = list(benchmark if benchmark is not None else load_benchmark())
    by_id = {case.case_id: case for case in cases}
    missing = [case_id for case_id, _ in DEMO_CASES if case_id not in by_id]
    if missing:  # pragma: no cover - guards against a silent demo regression
        raise KeyError(f"demo cases missing from the benchmark: {missing}")
    return [by_id[case_id] for case_id, _ in DEMO_CASES]


def _declared_lineage_lines(case: BenchmarkCase) -> list[str]:
    parents = []
    if case.declared_base_model:
        parents.append(case.declared_base_model)
    parents.extend(case.declared_additional_base_models)
    relation = case.declared_relation_raw or "(not declared)"
    if not parents:
        return ["  parent          : (not declared)",
                f"  relation        : {relation}"]
    lines = [f"  parent          : {parents[0]}"]
    lines.extend(f"  also declared   : {extra}" for extra in parents[1:])
    lines.append(f"  relation        : {relation}")
    return lines


def _evidence_lines(evidence: Sequence[EvidenceItem], limit: int = 4) -> list[str]:
    independent = [item for item in evidence if item.role is EvidenceRole.INDEPENDENT]
    ordered = sorted(
        independent,
        # ordered by the production item weight so the demo shows evidence in
        # exactly the order the engine ranks it (read-only: no scoring here)
        key=lambda item: (
            -ITEM_WEIGHTS.get(item.reliability, 0.0),
            item.source_name or "",
            item.key_path or "",
        ),
    )
    lines = []
    for item in ordered[:limit]:
        relation = item.relation.value if item.relation else "-"
        location = f"{item.source_name}:{item.key_path}" if item.key_path else item.source_name
        lines.append(
            f"  [{item.reliability.value:>13}] {item.source_type.value:<15} "
            f"parent={item.candidate_parent or '-'} relation={relation}"
        )
        lines.append(f"      from {location}")
    if len(independent) > limit:
        lines.append(f"  ... and {len(independent) - limit} weaker item(s)")
    if not independent:
        lines.append("  (no independent evidence: only declared metadata exists)")
    return lines


def render_case(case: BenchmarkCase) -> str:
    """Render one full audit walkthrough as text (no chain-of-thought)."""
    decision = decide_case(case)
    _, evidence, _ = case_inputs(case)
    track = "REAL" if case.track is Track.REAL else "CONTROLLED"
    lines: list[str] = []
    add = lines.append

    add("=" * 78)
    add(f"{track}  {case.case_id}")
    add("=" * 78)
    add(f"  repository       : {case.repository or case.title}")
    if case.snapshot_commit:
        add(f"  revision (pinned): {case.snapshot_commit}")
        add(f"  frozen files     : {len(case.snapshot_files)}")
    add("")
    add("Declared metadata under audit")
    lines.extend(_declared_lineage_lines(case))
    add("")
    add("Strongest independent evidence (declared metadata is never evidence)")
    lines.extend(_evidence_lines(evidence))
    add("")
    add(f"  conflicts        : {len(decision.conflicts)}")
    for conflict in decision.conflicts[:3]:
        add(f"    - {getattr(conflict, 'kind', 'conflict')}: "
            f"{getattr(conflict, 'detail', conflict)}")
    add(f"  support score    : {decision.support_score:.2f} "
        f"(heuristic evidence strength, not a probability)")
    add("")
    add(f"  DECISION         : {decision.decision.value}")
    proposed = decision.proposed_lineage
    if decision.decision.value == "ABSTAIN":
        add(f"  why              : {decision.reasoning_summary}")
    elif proposed.parents:
        relations = sorted({e.relation.value for e in proposed.entries if e.relation})
        add(f"  proposed parent  : {', '.join(proposed.parents)}")
        add(f"  proposed relation: {', '.join(relations) if relations else '(none)'}")
        patch = decision.recommended_patch
        if patch is not None:
            add(f"  recommended patch: base_model {patch.old_base_model!r} -> "
                f"{patch.new_base_model!r}")
            if patch.new_relation is not None:
                add(f"                     relation -> {patch.new_relation.value}")
            add("  (a recommendation only: ProvenanceLens never writes to a repository)")
    add(f"  rationale        : {decision.reasoning_summary}")
    add("")
    return "\n".join(lines)


def _one_line(case: BenchmarkCase) -> str:
    decision = decide_case(case)
    track = "REAL" if case.track is Track.REAL else "CONTROLLED"
    return (f"{track:<10} {decision.decision.value:<9} "
            f"support={decision.support_score:.2f}  {case.case_id}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m provenancelens.demo",
        description="Offline demonstration of ProvenanceLens on frozen evidence "
                    "(no network, no Ollama).",
    )
    parser.add_argument("--list", action="store_true",
                        help="print one line per demo case and exit")
    parser.add_argument("--case", action="append", default=[], metavar="CASE_ID",
                        help="show a specific benchmark case (repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    benchmark = load_benchmark()
    by_id = {case.case_id: case for case in benchmark}
    if args.case:
        unknown = [case_id for case_id in args.case if case_id not in by_id]
        if unknown:
            parser.error(
                f"unknown case id(s): {', '.join(unknown)}. "
                f"Use --list to see the demo cases, or see `python -m "
                f"provenancelens.evaluation validate` for the full benchmark."
            )
        cases = [by_id[case_id] for case_id in args.case]
    else:
        cases = demo_cases(benchmark)

    if args.json:
        payload = []
        for case in cases:
            decision = decide_case(case)
            payload.append({
                "case_id": case.case_id,
                "track": case.track.value,
                "repository": case.repository,
                "revision": case.snapshot_commit,
                "declared_base_model": case.declared_base_model,
                "declared_relation_raw": case.declared_relation_raw,
                "decision": decision.decision.value,
                "support_score": decision.support_score,
                "proposed_parents": list(decision.proposed_lineage.parents),
                "conflicts": len(decision.conflicts),
                "rationale": decision.reasoning_summary,
            })
        print(json.dumps(payload, indent=1))
        return 0

    if args.list:
        for case in cases:
            print(_one_line(case))
        return 0

    print(__doc__.split("\n\n")[0].strip())
    print()
    for case in cases:
        purpose = next((why for case_id, why in DEMO_CASES if case_id == case.case_id), "")
        if purpose:
            print(f"--> {purpose}")
        print(render_case(case))
    print("Every number above came from the production decision engine reading "
          "frozen evidence.")
    print("No network, no Ollama and no model weights were used.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

