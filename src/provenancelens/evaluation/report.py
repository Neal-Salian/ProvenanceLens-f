"""Phase G report generation: tables, plots and the reproducibility manifest.

Writes every artifact under ``artifacts/phase_g/`` and is deterministic:
running it twice on the same commit produces byte-identical files.  Wall
clock timings are reported separately in the manifest's ``timings`` block and
are excluded from :func:`report_digest`, because a duration is not a result.

Artifacts produced
------------------

* ``phase_g_report.json`` - the complete analysis (minus raw per-case dumps)
* ``phase_g_report.md``   - human-readable summary with every table
* ``tables/*.csv``        - one CSV per table (stable column order)
* ``tables/*.md``         - the same tables as GitHub-flavoured markdown
* ``plots/*.png``         - seven figures (risk/coverage, systems, ablations,
                           strata, failures, evidence, confusion)
* ``adjudication_summary.csv`` - per-case reviewer view of the real track
* ``manifest.json``       - environment, config, input/output digests, timings
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import platform
import sys
from pathlib import Path
from typing import Any, Sequence

__all__ = [
    "ARTIFACT_DIRNAME",
    "render_markdown_table",
    "write_tables",
    "write_plots",
    "build_manifest",
    "report_digest",
    "write_phase_g_report",
]

ARTIFACT_DIRNAME = "phase_g"

_FLOAT_FMT = "{:.4f}"


def _round(value: Any, digits: int = 6) -> Any:
    return round(value, digits) if isinstance(value, float) else value


def _ci(row: dict, key: str = "ci95") -> str:
    ci = row.get(key) or {}
    low, high = ci.get("low"), ci.get("high")
    if low is None or high is None:
        return "-"
    return f"[{low:.3f}, {high:.3f}]"


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return _FLOAT_FMT.format(value)
    return str(value)


def _flatten(prefix: str, value: Any) -> list[tuple[str, Any]]:
    """Flatten nested metric dicts into ``a.b`` -> value rows."""
    rows: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key in sorted(value):
            child = value[key]
            if isinstance(child, dict) and "value" not in child:
                rows.extend(_flatten(f"{prefix}{key}.", child))
            else:
                rows.append((f"{prefix}{key}", child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(_flatten(f"{prefix}{index}.", item))
    else:
        rows.append((prefix.rstrip("."), value))
    return rows


def render_markdown_table(rows: Sequence[dict], columns: Sequence[str] | None = None) -> str:
    """Deterministic GitHub-flavoured markdown table."""
    if not rows:
        return "_no rows_\n"
    cols = list(columns) if columns else list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |",
           "| " + " | ".join("---" for _ in cols) + " |"]
    for row in rows:
        out.append("| " + " | ".join(_fmt(row.get(col)) for col in cols) + " |")
    return "\n".join(out) + "\n"


def _csv_bytes(rows: Sequence[dict], columns: Sequence[str] | None = None) -> bytes:
    cols = list(columns) if columns else list(rows[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: _fmt(row.get(col)) for col in cols})
    return buffer.getvalue().encode("utf-8")


def write_tables(report: dict, directory: Path) -> dict[str, str]:
    """Write every table as ``.csv`` and ``.md``; return name -> relative path."""
    directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    def emit(name: str, rows: Sequence[dict], columns: Sequence[str] | None = None) -> None:
        csv_path = directory / f"{name}.csv"
        csv_path.write_bytes(_csv_bytes(rows, columns))
        md_path = directory / f"{name}.md"
        md_path.write_text(render_markdown_table(rows, columns), encoding="utf-8")
        written[f"{name}.csv"] = str(csv_path.relative_to(directory.parent.parent))
        written[f"{name}.md"] = str(md_path.relative_to(directory.parent.parent))

    main = report["systems"]["provenancelens"]["headline"]
    emit("headline_metrics", [
        {**row,
         "ci95_low": _round(row.get("ci95", {}).get("low")),
         "ci95_high": _round(row.get("ci95", {}).get("high"))}
        for row in main
    ], ["metric", "numerator", "denominator", "value", "ci95_low", "ci95_high",
        "definition"])

    if "headline_real" in report["systems"]["provenancelens"]:
        emit("headline_real", [
        {**row,
         "ci95_low": _round(row.get("ci95", {}).get("low")),
         "ci95_high": _round(row.get("ci95", {}).get("high"))}
            for row in report["systems"]["provenancelens"]["headline_real"]
        ], ["metric", "numerator", "denominator", "value", "ci95_low", "ci95_high",
            "definition"])

    emit("system_comparison", report["comparisons"])

    if "ablations" in report:
        emit("ablation_results", [
            {k: v for k, v in row.items()
             if k not in ("delta_action_accuracy", "delta_false_repairs", "hypothesis")}
            for row in report["ablations"]["results"]
        ], ["ablation", "question", "verdict", "n_cases", "action_accuracy",
            "action_correct", "macro_f1", "coverage", "attempted_repairs",
            "false_repairs", "false_repair_rate", "parent_accuracy",
            "relation_accuracy"])
        if report["ablations"].get("results_real"):
            emit("ablation_results_real", [
                row for row in report["ablations"]["results_real"]
            ], ["ablation", "verdict", "n_cases", "action_accuracy", "coverage",
                "attempted_repairs", "false_repairs", "false_repair_rate"])

    emit("stratified_results", [
        {**row,
         "action_accuracy": row["action_accuracy"]["value"],
         "action_ci95_low": _round(row["action_accuracy"]["low"]),
         "action_ci95_high": _round(row["action_accuracy"]["high"]),
         "coverage": row["coverage"]["value"],
         "false_repair_rate": row["false_repair_rate"]["value"]}
        for row in report["stratified_results"]
    ], ["stratum", "n_cases", "action_accuracy", "action_ci95_low",
        "action_ci95_high", "coverage", "attempted_repairs", "false_repairs",
        "false_repair_rate"])

    emit("failure_taxonomy", report["failure_analysis"]["taxonomy"],
         ["category", "n_cases", "description"] +
         [key for key in report["failure_analysis"]["taxonomy"][0]
          if key.startswith("n_")])
    emit("failures", [
        {**row, "conflicts": "|".join(row["conflicts"])}
        for row in report["failure_analysis"]["failures"]
    ], ["case_id", "track", "category", "expected_action", "predicted_action",
        "support_score", "truth_metadata_state", "truth_parents_status",
        "repair_attempted", "false_repair", "conflicts", "reasoning_summary"])

    usage = report["evidence_usage"]
    sources = sorted(set(usage["presence"]) | set(usage["decisive"]))
    emit("evidence_usage", [
        {
            "source": source,
            "cases_present": usage["presence"].get(source, {}).get("n_cases", 0),
            "presence_share": usage["presence"].get(source, {}).get("share"),
            "decisive_items": usage["decisive"].get(source, {}).get("n_items", 0),
        }
        for source in sources
    ], ["source", "cases_present", "presence_share", "decisive_items"])

    emit("risk_coverage_curve", [
        {
            "threshold": row["threshold"],
            "coverage": row["coverage"]["value"],
            "selective_accuracy": row["selective_accuracy"]["value"],
            "selective_accuracy_ci95_low": _round(row["selective_accuracy"]["low"]),
            "selective_accuracy_ci95_high": _round(row["selective_accuracy"]["high"]),
            "attempted_repairs": row["attempted_repairs"],
            "false_repairs": row["false_repairs"],
            "false_repair_rate": row["false_repair_rate"]["value"],
            "abstentions": row["abstentions"],
        }
        for row in report["selective_risk_curve"]
    ], ["threshold", "coverage", "selective_accuracy",
        "selective_accuracy_ci95_low", "selective_accuracy_ci95_high",
        "attempted_repairs", "false_repairs", "false_repair_rate", "abstentions"])
    return written


# --- plots --------------------------------------------------------------------

def write_plots(report: dict, directory: Path) -> dict[str, str]:
    """Render the figure set with a fixed, deterministic matplotlib setup."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 120,
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.hashsalt": "provenancelens-phase-g",
    })
    directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    metadata = {"Software": "provenancelens-phase-g"}  # no timestamp -> reproducible

    def save(fig, name: str) -> None:
        path = directory / f"{name}.png"
        fig.savefig(path, format="png", bbox_inches="tight", metadata=metadata)
        plt.close(fig)
        written[f"{name}.png"] = str(path.relative_to(directory.parent.parent))

    # 1. systems
    rows = report["comparisons"]
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    names = [row["system"] for row in rows][::-1]
    values = [row["action_accuracy"] for row in rows][::-1]
    false_repairs = [row["false_repairs"] for row in rows][::-1]
    colors = ["#b2182b" if f else "#2166ac" for f in false_repairs]
    ax.barh(names, values, color=colors)
    for index, value in enumerate(values):
        ax.text(value + 0.01, index, f"{value:.3f}", va="center", fontsize=8)
    ax.set_xlabel("action accuracy")
    ax.set_xlim(0, 1.05)
    ax.set_title("Action accuracy by system (red = any false repair)")
    save(fig, "action_accuracy_by_system")

    # 2. risk / coverage
    curve = report["selective_risk_curve"]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    xs = [row["coverage"]["value"] for row in curve]
    ys = [row["selective_accuracy"]["value"] for row in curve]
    lows = [row["selective_accuracy"]["low"] for row in curve]
    highs = [row["selective_accuracy"]["high"] for row in curve]
    ax.plot(xs, ys, "-o", color="#2166ac", markersize=4, label="selective accuracy")
    ax.fill_between(xs, lows, highs, color="#2166ac", alpha=0.18,
                    label="Wilson 95% CI")
    ax.plot(xs, xs, "--", color="#999999", linewidth=1, label="y = x (no added value)")
    ax.set_xlabel("coverage (non-abstain share)")
    ax.set_ylabel("selective accuracy")
    ax.set_title("Risk-coverage: accuracy as abstention is relaxed")
    ax.legend(fontsize=7, loc="lower right")
    save(fig, "risk_coverage_curve")

    # 3. ablations
    if "ablations" in report:
        rows = [row for row in report["ablations"]["results"] if row["ablation"] != "full"]
        fig, ax = plt.subplots(figsize=(6.6, 3.6))
        names = [row["ablation"] for row in rows][::-1]
        deltas = [row["delta_action_accuracy"] for row in rows][::-1]
        ax.barh(names, deltas, color=["#b2182b" if d < -0.02 else "#999999" for d in deltas])
        for index, delta in enumerate(deltas):
            ax.text(delta - 0.005 if delta < 0 else delta + 0.005, index,
                    f"{delta:+.3f}", va="center", ha="right" if delta < 0 else "left",
                    fontsize=8)
        ax.axvline(0.0, color="#333333", linewidth=0.8)
        ax.set_xlabel("change in action accuracy vs full system")
        ax.set_title("Ablation effect on action accuracy (n=70)")
        save(fig, "ablation_delta_action_accuracy")

    # 4. strata
    rows = report["stratified_results"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    names = [row["stratum"] for row in rows]
    values = [row["action_accuracy"]["value"] for row in rows]
    lows = [row["action_accuracy"]["low"] for row in rows]
    highs = [row["action_accuracy"]["high"] for row in rows]
    ax.bar(names, values, color="#4393c3")
    ax.errorbar(range(len(rows)), values,
                yerr=[[v - lo for v, lo in zip(values, lows)],
                      [hi - v for v, hi in zip(values, highs)]],
                fmt="none", ecolor="#333333", capsize=3)
    ax.set_ylabel("action accuracy")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_title("Action accuracy per stratum (Wilson 95% CI)")
    save(fig, "stratum_accuracy")

    # 5. failures
    taxonomy = [row for row in report["failure_analysis"]["taxonomy"]
                if row["n_cases"]]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.barh([row["category"] for row in taxonomy][::-1],
            [row["n_cases"] for row in taxonomy][::-1], color="#e08214")
    ax.set_xlabel("cases")
    ax.set_title(f"Failure taxonomy (n={report['failure_analysis']['n_failures']} failures)")
    save(fig, "failure_taxonomy")

    # 6. evidence usage
    usage = report["evidence_usage"]
    sources = sorted(set(usage["presence"]) | set(usage["decisive"]))
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    positions = range(len(sources))
    ax.bar([p - 0.2 for p in positions],
           [usage["presence"].get(s, {}).get("n_cases", 0) for s in sources],
           width=0.4, color="#2166ac", label="cases with this source present")
    ax.bar([p + 0.2 for p in positions],
           [usage["decisive"].get(s, {}).get("n_items", 0) for s in sources],
           width=0.4, color="#f4a582", label="decisive items (candidate in truth)")
    ax.set_xticks(list(positions))
    ax.set_xticklabels(sources, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("count")
    ax.legend(fontsize=7)
    ax.set_title("Evidence sources: presence vs decisiveness")
    save(fig, "evidence_usage")

    # 7. action confusion
    matrix = report["action_confusion"]
    labels = [label for label in sorted(matrix)]
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    data = [[matrix.get(row, {}).get(col, 0) for col in labels] for row in labels]
    ax.imshow(data, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            ax.text(j, i, str(value), ha="center", va="center", fontsize=9,
                    color="white" if value > 12 else "black")
    ax.set_xlabel("predicted")
    ax.set_ylabel("expected")
    ax.set_title("Action confusion (expected vs predicted)")
    save(fig, "action_confusion")
    return written


# --- manifest -----------------------------------------------------------------

def _git_dir(start: Path) -> Path | None:
    """Locate the ``.git`` directory by reading the filesystem only.

    The package never executes external commands (Phase E invariant), so the
    commit is resolved from ``.git/HEAD`` and the refs instead of shelling out
    to ``git``.  Returns ``None`` outside a checkout, which is reported as
    ``null`` rather than guessed.
    """
    for candidate in (start, *start.parents):
        dot_git = candidate / ".git"
        if dot_git.is_file():  # worktree or submodule: ".git" is a pointer file
            try:
                target = dot_git.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            if target.startswith("gitdir:"):
                path = Path(target.split(":", 1)[1].strip())
                return path if path.is_absolute() else (candidate / path)
            return None
        if dot_git.is_dir():
            return dot_git
    return None


def _git_metadata(start: Path) -> dict[str, str | None]:
    """Commit and branch read straight from the git directory."""
    git_dir = _git_dir(start)
    if git_dir is None:
        return {"commit": None, "branch": None}
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return {"commit": None, "branch": None}
    if not head.startswith("ref:"):
        return {"commit": head, "branch": None}
    ref = head.split(":", 1)[1].strip()
    sha: str | None = None
    ref_path = git_dir / ref
    try:
        if ref_path.is_file():
            sha = ref_path.read_text(encoding="utf-8").strip()
        else:  # packed refs
            packed = git_dir / "packed-refs"
            if packed.is_file():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) == 2 and parts[1] == ref:
                        sha = parts[0]
                        break
    except OSError:
        sha = None
    return {"commit": sha, "branch": ref.rsplit("/", 1)[-1]}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(
    report: dict,
    *,
    artifacts: dict[str, Path],
    snapshot_root: Path,
    elapsed_seconds: float,
    config: dict,
) -> dict:
    """Environment, inputs, outputs and timings for one Phase G run."""
    inputs: dict[str, str] = {}
    for path in sorted(snapshot_root.rglob("extracted_evidence.json")):
        inputs[str(path.relative_to(snapshot_root))] = _digest(path)
    outputs = {name: _digest(path) for name, path in sorted(artifacts.items())}
    git = _git_metadata(Path.cwd())
    try:
        import matplotlib

        matplotlib_version = matplotlib.__version__
    except Exception:  # pragma: no cover - matplotlib is optional for tables
        matplotlib_version = None
    return {
        "benchmark_version": report["benchmark"]["benchmark_version"],
        "n_cases": report["benchmark"]["n_cases"],
        "environment": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "packages": {
                "provenancelens": _package_version(),
                "pydantic": _dist_version("pydantic"),
                "matplotlib": matplotlib_version,
            },
            "network_used": False,
            "llm_used": False,
            "optional_extras_installed": False,
        },
        "repository": {
            "git_commit": git["commit"],
            "git_branch": git["branch"],
            "source": "read from .git/HEAD without executing git (Phase E invariant)",
        },
        "config": config,
        "inputs": inputs,
        "outputs": outputs,
        "timings": {
            "elapsed_seconds": round(elapsed_seconds, 3),
            "definition": "wall clock for the whole Phase G run; reported separately "
                          "and excluded from the report digest because a duration "
                          "is not a result",
        },
    }


def _package_version() -> str | None:
    from .. import __version__

    return __version__


def _dist_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:  # pragma: no cover
        return None


def report_digest(report: dict) -> str:
    """SHA-256 over the deterministic part of the report.

    Timings, environment strings and paths are excluded so two runs of the
    same commit on the same machine (or another machine) agree.
    """
    payload = {key: value for key, value in report.items()
               if key not in ("per_case", "environment", "timings")}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- markdown summary ---------------------------------------------------------

def _summary_markdown(report: dict, manifest: dict) -> str:
    lines: list[str] = []
    add = lines.append
    bench = report["benchmark"]
    add("# Phase G experimental study")
    add("")
    add(f"- Benchmark: {bench['n_cases']} cases "
        f"({bench['by_track'].get('controlled')} controlled, "
        f"{bench['by_track'].get('real')} real), version {bench['benchmark_version']}")
    add(f"- Report digest: `{report_digest(report)}`")
    add(f"- Commit: `{manifest['repository']['git_commit']}` "
        f"(branch `{manifest['repository']['git_branch']}`)")
    add("- Offline, deterministic, no LLM and no network.")
    add("")
    add("## Calibration status")
    add("")
    add("`support_score` is a heuristic evidence strength, not a probability, so "
        "ECE/Brier and reliability diagrams are deliberately **not** reported.")
    add("")
    add("## Headline metrics (all cases)")
    add("")
    add(render_markdown_table([
        {**row, "ci95": _ci(row)}
        for row in report["systems"]["provenancelens"]["headline"]
    ], ["metric", "numerator", "denominator", "value", "ci95"]))
    add("## Headline metrics (real track only)")
    add("")
    add(render_markdown_table([
        {**row, "ci95": _ci(row)}
        for row in report["systems"]["provenancelens"]["headline_real"]
    ], ["metric", "numerator", "denominator", "value", "ci95"]))
    add("## System comparison")
    add("")
    add(render_markdown_table(report["comparisons"]))
    if "ablations" in report:
        add("## Ablations")
        add("")
        add(render_markdown_table([
            {**row, "delta_action_accuracy": row["delta_action_accuracy"]}
            for row in report["ablations"]["results"]
        ], ["ablation", "action_accuracy", "delta_action_accuracy", "macro_f1",
            "coverage", "attempted_repairs", "false_repairs", "verdict"]))
        add("Pre-registered hypotheses:")
        add("")
        for spec in report["ablations"]["suite"]:
            add(f"- `{spec['name']}` - {spec['question']} {spec['hypothesis']}")
        add("")
    add("## Per-stratum results")
    add("")
    add(render_markdown_table([
        {**row, "action_accuracy": row["action_accuracy"]["value"],
         "ci95": f"[{row['action_accuracy']['low']}, {row['action_accuracy']['high']}]",
         "coverage": row["coverage"]["value"]}
        for row in report["stratified_results"]
    ], ["stratum", "n_cases", "action_accuracy", "ci95", "coverage",
        "attempted_repairs", "false_repairs"]))
    add("## Failure taxonomy")
    add("")
    add(render_markdown_table(report["failure_analysis"]["taxonomy"],
                             ["category", "n_cases", "description"]))
    add("## Evidence usage")
    add("")
    add(render_markdown_table([
        {"source": source,
         "cases_present": report["evidence_usage"]["presence"].get(source, {}).get("n_cases", 0),
         "presence_share": report["evidence_usage"]["presence"].get(source, {}).get("share"),
         "decisive_items": report["evidence_usage"]["decisive"].get(source, {}).get("n_items", 0)}
        for source in sorted(set(report["evidence_usage"]["presence"])
                             | set(report["evidence_usage"]["decisive"]))
    ], ["source", "cases_present", "presence_share", "decisive_items"]))
    add(report["evidence_usage"]["definition"])
    add("")
    add("## Figures")
    add("")
    for name in ("action_accuracy_by_system", "risk_coverage_curve",
                 "ablation_delta_action_accuracy", "stratum_accuracy",
                 "failure_taxonomy", "evidence_usage", "action_confusion"):
        add(f"- `plots/{name}.png`")
    add("")
    return "\n".join(lines)


def write_phase_g_report(
    report: dict,
    output_dir: Path,
    *,
    manifest: dict,
    snapshot_root: Path,
    config: dict,
    adjudication_rows: Sequence[dict] | None = None,
) -> dict[str, Path]:
    """Write every artifact; return ``name -> path`` for the manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {}

    body = {key: value for key, value in report.items() if key != "per_case"}
    report_json = output_dir / "phase_g_report.json"
    report_json.write_text(
        json.dumps({**body, "report_digest": report_digest(report)},
                   indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts["phase_g_report.json"] = report_json
    artifacts["phase_g_report.md"] = _write(
        output_dir / "phase_g_report.md", _summary_markdown(report, manifest)
    )
    for name, _ in write_tables(report, output_dir / "tables").items():
        artifacts[f"tables/{name}"] = output_dir / "tables" / name
    for name, _ in write_plots(report, output_dir / "plots").items():
        artifacts[f"plots/{name}"] = output_dir / "plots" / name
    if adjudication_rows:
        artifacts["adjudication_summary.csv"] = _write(
            output_dir / "adjudication_summary.csv",
            _csv_bytes(adjudication_rows).decode("utf-8"),
        )
    manifest = {**manifest, "outputs": {name: _digest(path)
                                       for name, path in sorted(artifacts.items())}}
    artifacts["manifest.json"] = _write(
        output_dir / "manifest.json",
        json.dumps(manifest, indent=1, sort_keys=True) + "\n",
    )
    return artifacts


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
