# Reproducibility

Everything here runs **offline** on a fresh clone. No model hub account, no
network, no Ollama, no GPU.

## Requirements

| item | value |
| --- | --- |
| Python | **>= 3.10** (`requires-python` in `pyproject.toml`); developed and verified on 3.13.3 |
| core dependencies | `pydantic>=2.6`, `huggingface_hub>=0.23`, `PyYAML>=6.0`, `httpx>=0.23` |
| `dev` extra | `pytest>=8`, `matplotlib>=3.7` — tests and figures |
| `plots` extra | `matplotlib>=3.7` — figures only |
| `llm` extra | `langchain-core>=1.0`, `langchain-ollama>=0.3` — optional experiment only |

No paid inference API is ever a dependency. The deterministic core, the
benchmark and the study import none of the optional extras.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # core
pip install -e ".[dev]"     # + pytest and matplotlib
```

## Commands

| goal | command | expected |
| --- | --- | --- |
| tests | `python -m pytest -q` | `563 passed, 7 skipped` |
| demo | `python -m provenancelens.demo` | 6 walkthroughs, no network |
| audit one repository | `python -m provenancelens.cli audit peft-internal-testing/tiny-OPTForCausalLM-lora` | decision report |
| validate the benchmark | `python -m provenancelens.evaluation validate` | `n_cases: 70`, `errors: []` |
| run the benchmark | `python -m provenancelens.evaluation run` | metrics for 7 systems |
| full study | `python -m provenancelens.evaluation.phase_g_cli run --output /tmp/study` | 31 artifacts, ~2 s |
| verify committed results | `python -m provenancelens.evaluation.phase_g_cli verify-canonical` | `"ok": true` |
| regenerate committed results | `python -m provenancelens.evaluation.phase_g_cli publish` | rewrites `results/phase_g/` |

## Output structure

`run --output DIR` writes:

```
DIR/
├── phase_g_report.json      # complete analysis, machine-readable
├── phase_g_report.md        # summary with every table
├── manifest.json            # environment, config, input and output digests, timings
├── adjudication_summary.csv # per-case declared vs adjudicated (real track)
├── tables/                  # 11 tables, each .csv and .md
└── plots/                   # 7 figures (.png), when matplotlib is installed
```

`publish` writes the **canonical, committed** set to `results/phase_g/`:

```
results/phase_g/
├── results.json       # machine-readable source of truth for every documented number
├── RESULTS.md         # human-readable results, rendered FROM results.json
├── manifest.json      # versions, 44 snapshot revisions, SHA-256 of all 30 files
├── adjudication_summary.csv
├── tables/            # the same 11 tables
└── figures/           # the same 7 figures
```

`artifacts/` is scratch and git-ignored; `results/` is evidence. Both are produced
by the same renderers, so they cannot disagree.

## Determinism

* The study contains **no stochastic component**: no sampling, no shuffling, no
  model inference. There is no random seed to set, and
  `manifest.determinism.random_seed` is `null` with that explanation.
* No clock value enters any metric. Wall-clock time appears only in
  `artifacts/phase_g/manifest.json` under `timings`, which is why it is excluded
  from the canonical manifest.
* Two runs produce byte-identical trees. Verify it:

```bash
python -m provenancelens.evaluation.phase_g_cli run --output /tmp/a --quiet
python -m provenancelens.evaluation.phase_g_cli run --output /tmp/b --quiet
diff -r -q /tmp/a /tmp/b | grep -v manifest.json   # only manifest.json differs
```

* Figures are deterministic too: fixed DPI, `Agg` backend, fixed `svg.hashsalt`,
  and PNG metadata pinned to a constant so no timestamp is embedded.
* Optional extras do not change results. A minimal environment and a full
  environment produce the same report digest and byte-identical tables; only the
  `figures` block of the manifest differs.

## Frozen evidence

* Identity: `data/snapshots/<org>__<repo>/<40-char commit sha>/`, containing
  `manifest.json`, the frozen files, and `extracted_evidence.json`.
* Every file has a SHA-256 in the snapshot manifest. `load_snapshot` verifies
  hashes, UTF-8 decodability and path safety **before** any parsing, so a
  tampered snapshot fails loudly instead of silently changing results.
* All 44 revisions are listed in `results/phase_g/manifest.json` under
  `snapshot_revisions`.
* **No model weights were ever fetched.** The collector excludes weights and
  binaries by name and type before download; the whole `data/snapshots` tree is
  ~1.2 MB across 107 files.
* Frozen evidence is immutable by design: re-collecting an identical revision
  reuses it, and a differing one raises a conflict rather than overwriting.
* The legacy Phase-2 notebook is byte-identical to its original commit. Its
  SHA-256 is asserted in the test suite.

## Verifying integrity

```bash
python -m provenancelens.evaluation.phase_g_cli verify-canonical
```

re-hashes all 30 canonical files, checks that `results.json` hashes to its own
recorded digest, and confirms each manifest revision still matches the
benchmark. The test suite additionally asserts the notebook hash, the benchmark
composition (70 / 44 / 26), that documented numbers match a fresh run, and that
no production package changed during finalisation.

## Optional network acquisition

Collecting *new* repositories is the only step that needs the network, and it is
never implicit:

```bash
python -c "
from provenancelens.evaluation.acquisition import acquire_real_snapshots
report = acquire_real_snapshots(dry_run=True)   # plan only, no download
"
```

ProvenanceLens never fetches weights, never exceeds the snapshot byte budget, and
records inclusion and exclusion reasons. Re-running the published study does
**not** collect anything: it reads the frozen snapshots.

## Optional local LLM experiment

```bash
pip install -e ".[llm]"
ollama serve                 # you start the runtime
ollama list                  # only if a model is ALREADY installed
python -m provenancelens.evaluation.phase_g_cli llm-compare --model llama3.2:3b
```

ProvenanceLens never downloads or installs a model, and never starts the runtime
for you. If the model is missing, the command exits with instructions and changes
nothing. Its output is written to a **separate** artifact
(`artifacts/phase_g/llm/llm_comparator.json`) and never enters the canonical
results or the report digest, because local model output depends on the installed
model build.

## Offline acceptance checklist

Run with the network unavailable and confirm each step:

| step | command | result |
| --- | --- | --- |
| import | `python -c "import provenancelens"` | ok |
| tests | `python -m pytest -q` | 563 passed, 7 skipped |
| demo | `python -m provenancelens.demo` | 6 walkthroughs |
| audit | `python -m provenancelens.cli audit <repo>` | decision report |
| benchmark | `python -m provenancelens.evaluation validate` | 0 errors |
| study | `... phase_g_cli run --output /tmp/s` | 31 artifacts |
| tables | `ls /tmp/s/tables` | 22 files (11 × csv+md) |
| figures | `ls /tmp/s/plots` | 7 PNGs, or a recorded skip reason |
| canonical | `... phase_g_cli verify-canonical` | ok |

## Environment variables

| variable | effect |
| --- | --- |
| `PROVENANCELENS_LLM_TESTS=1` | enable the opt-in live Ollama tests |
| `PROVENANCELENS_NETWORK_TESTS=1` | enable the opt-in live collection tests |
| `HF_TOKEN` | optional, for gated repositories; only used for requests, never stored in results |

## Troubleshooting

| symptom | cause | fix |
| --- | --- | --- |
| `ModuleNotFoundError: pydantic` | core deps missing | `pip install -e .` |
| `matplotlib is required for figures` | plots extra missing | `pip install -e ".[plots]"` or `--no-plots` |
| benchmark `validate` reports errors | benchmark defect | stop; every number depends on it |
| `SnapshotError` about hashes | a frozen file changed | restore the repository; never edit a snapshot |
| `model not installed locally` | optional LLM experiment | install the model yourself or skip |
| study digest differs from `results/phase_g` | stale committed results | run `... phase_g_cli publish` and review the diff |
