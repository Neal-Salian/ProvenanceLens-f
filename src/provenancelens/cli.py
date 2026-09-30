"""``provenancelens`` command line: audit, demo, benchmark, study.

Four commands, one entry point::

    provenancelens audit REPOSITORY     audit one frozen repository (offline)
    provenancelens demo                 guided walkthrough on frozen evidence
    provenancelens benchmark ...        LineageRepairBench metrics and baselines
    provenancelens study ...            the Phase G experimental study

This module is a thin, documented dispatcher: it adds no decision logic.  The
existing ``python -m provenancelens.evaluation`` and
``python -m provenancelens.evaluation.phase_g_cli`` interfaces keep working
unchanged, and this CLI forwards to them.

Everything except ``collect`` is offline.  Audit reads only frozen snapshots, so
it never contacts a model hub and never needs Ollama.  ProvenanceLens never
writes to an external repository: an audit produces a recommendation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

__all__ = ["main", "build_parser"]

DEFAULT_SNAPSHOT_ROOT = Path("data/snapshots")


# --- audit --------------------------------------------------------------------

def _snapshot_index(root: Path) -> dict[str, tuple[str, Path]]:
    """repository -> (commit sha, snapshot dir) for every frozen snapshot."""
    index: dict[str, tuple[str, Path]] = {}
    if not root.is_dir():
        return index
    for repo_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        repository = repo_dir.name.replace("__", "/", 1)
        for sha_dir in sorted(p for p in repo_dir.iterdir() if p.is_dir()):
            if (sha_dir / "manifest.json").is_file():
                index[repository] = (sha_dir.name, sha_dir)
    return index


def _cmd_audit(args: argparse.Namespace) -> int:
    from .parsers import extract_repository_evidence
    from .reasoning import decide_lineage
    from .reporting import format_audit_decision
    from .snapshots import SnapshotError, load_snapshot

    root = Path(args.root) if args.root else DEFAULT_SNAPSHOT_ROOT
    index = _snapshot_index(root)
    repository = args.repository
    if repository not in index:
        known = sorted(index)
        hint = ""
        if not index:
            hint = (f"\nNo frozen snapshots were found under {root}. ProvenanceLens "
                    f"audits *frozen* evidence, so it never fetches a repository "
                    f"implicitly.\nCollect one with the Phase C collector "
                    f"(src/provenancelens/collectors/huggingface.py), then re-run.")
        elif len(known) > 8:
            hint = (f"\n{len(known)} repositories are frozen under {root}. "
                    f"Examples: " + ", ".join(known[:5]) + ", ...")
        print(f"error: no frozen snapshot for {repository!r}.{hint}", file=sys.stderr)
        return 2
    commit, snapshot_dir = index[repository]
    if args.revision and args.revision != commit:
        print(f"error: {repository} is frozen at {commit}, not {args.revision}.\n"
              f"ProvenanceLens audits a pinned revision; audit the frozen one or "
              f"collect the requested revision explicitly.", file=sys.stderr)
        return 2
    try:
        snapshot = load_snapshot(repository, commit, root=root)
    except SnapshotError as exc:
        print(f"error: the frozen snapshot for {repository}@{commit[:12]} is not "
              f"usable: {exc}\nThe snapshot files or their recorded hashes changed; "
              f"frozen evidence is immutable by design, so restore the repository "
              f"rather than editing the snapshot.", file=sys.stderr)
        return 3

    extraction = extract_repository_evidence(repository, commit, snapshot.contents)
    declared = extraction.declared_lineage
    evidence = [*extraction.declared_evidence, *extraction.independent_evidence]
    result = decide_lineage(repository, declared, evidence).decision

    if args.json:
        print(json.dumps(result.model_dump(mode="json"), indent=1))
        return 0
    print(f"FROZEN EVIDENCE  : {snapshot_dir.relative_to(root.parent)}"
          if snapshot_dir.is_relative_to(root.parent) else f"FROZEN EVIDENCE  : {snapshot_dir}")
    print(format_audit_decision(result))
    print()
    print("This is a recommendation only: ProvenanceLens never writes to an "
          "external repository.")
    return 0


# --- forwarding commands ------------------------------------------------------

def _cmd_demo(args: argparse.Namespace) -> int:
    from .demo import main as demo_main

    return demo_main(args.rest)


def _cmd_benchmark(args: argparse.Namespace) -> int:
    from .evaluation.__main__ import main as evaluation_main

    argv = [args.rest[0] if args.rest else "summary"]
    if args.track:
        argv = ["--track", args.track, *argv]
    if args.root:
        argv = ["--root", args.root, *argv]
    if args.output:
        argv = ["--output", args.output, *argv]
    try:
        return evaluation_main(argv)
    except SystemExit as exc:  # argparse inside the sub-CLI
        return int(exc.code or 0)


def _cmd_study(args: argparse.Namespace) -> int:
    from .evaluation.phase_g_cli import main as study_main

    argv = list(args.rest) or ["summary"]
    if args.root:
        argv = ["--root", args.root, *argv]
    if args.output and "run" in argv:
        argv = [arg if not arg.startswith("--output") else f"--output={args.output}"
                for arg in argv]
        if not any(arg.startswith("--output") for arg in argv):
            argv += ["--output", args.output]
    try:
        return study_main(argv)
    except SystemExit as exc:
        return int(exc.code or 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="provenancelens",
        description="Audit direct model-lineage metadata in open model "
                    "repositories. Offline by default; never writes to a repository.",
        epilog="Run 'provenancelens COMMAND --help' for command-specific options. "
               "Every 'python -m provenancelens...' invocation remains available.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    audit = sub.add_parser(
        "audit",
        help="audit one frozen repository and print the decision",
        description="Audit a repository from its FROZEN snapshot. Offline: no "
                    "network, no Ollama, no model weights.",
        epilog="Example: provenancelens audit peft-internal-testing/tiny-OPTForCausalLM-lora",
    )
    audit.add_argument("repository", help="repository id, e.g. 'org/model-name'")
    audit.add_argument("--revision", default=None,
                       help="require a specific pinned commit (fails if different)")
    audit.add_argument("--root", default=None,
                       help=f"frozen snapshot root (default: {DEFAULT_SNAPSHOT_ROOT})")
    audit.add_argument("--json", action="store_true",
                       help="emit the AuditDecision as JSON")
    audit.set_defaults(func=_cmd_audit)

    demo = sub.add_parser("demo", help="guided walkthrough on frozen evidence",
                          description="Run the production engine over curated frozen "
                                      "cases and print the decisions.")
    demo.add_argument("rest", nargs=argparse.REMAINDER,
                      help="arguments forwarded to the demo (e.g. --list, --case ID)")
    demo.set_defaults(func=_cmd_demo)

    benchmark = sub.add_parser(
        "benchmark", help="LineageRepairBench: validate, run systems, baselines",
        description="Evaluate systems against LineageRepairBench. Forwards to "
                    "'python -m provenancelens.evaluation'.",
    )
    benchmark.add_argument("rest", nargs=argparse.REMAINDER,
                           help="subcommand: validate | run | extraction | all")
    benchmark.add_argument("--track", choices=["controlled", "real"], default=None)
    benchmark.add_argument("--root", default=None)
    benchmark.add_argument("--output", default=None)
    benchmark.set_defaults(func=_cmd_benchmark)

    study = sub.add_parser(
        "study", help="the Phase G experimental study",
        description="Run the Phase G study: ablations, analyses, tables, figures. "
                    "Forwards to 'python -m provenancelens.evaluation.phase_g_cli'.",
    )
    study.add_argument("rest", nargs=argparse.REMAINDER,
                       help="subcommand: run | summary | ablate | failures | verify | llm-compare")
    study.add_argument("--output", default=None)
    study.add_argument("--root", default=None)
    study.set_defaults(func=_cmd_study)
    return parser


#: subcommands that forward their arguments to another parser
_FORWARDING = ("demo", "benchmark", "study")


def main(argv: list[str] | None = None) -> int:
    """Dispatch, forwarding unrecognised options to forwarding subcommands.

    ``argparse.REMAINDER`` does not capture options that appear *before* the
    first positional (``provenancelens demo --list`` would fail), so leftover
    arguments are collected with ``parse_known_args`` and prepended to the
    subcommand's own list.  For every other subcommand an unknown option is a
    genuine error and is reported as one.
    """
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    command = getattr(args, "command", None)
    if command in _FORWARDING and unknown:
        args.rest = [*unknown, *list(getattr(args, "rest", []) or [])]
    elif unknown:
        parser.error("unrecognized arguments: " + " ".join(unknown))
    if not command:
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
