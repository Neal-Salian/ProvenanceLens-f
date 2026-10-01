# Quickstart — 5 to 10 minutes

You need Python 3.10 or newer and nothing else. No network, no model hub
account, no Ollama, no GPU. Every command below runs **offline** against
evidence that is already frozen in this repository.

```bash
git clone https://github.com/Rusheel86/ProvenanceLens.git
cd ProvenanceLens
python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .                                       # core only: pydantic, PyYAML, httpx, huggingface_hub
```

## 1. Run the tests (about 40 s)

```bash
pip install -e ".[dev]"        # adds pytest and matplotlib
python -m pytest -q
```

Expected: **563 passed, 7 skipped**. The skips are the opt-in live tests
(`PROVENANCELENS_LLM_TESTS=1` for a local Ollama model, and
`PROVENANCELENS_NETWORK_TESTS=1` for live Hugging Face collection); nothing in
the default suite touches the network.

## 2. See what the system does (about 10 s)

```bash
python -m provenancelens.demo                 # curated walkthrough
python -m provenancelens.demo --list          # one line per case
python -m provenancelens.cli audit peft-internal-testing/tiny-OPTForCausalLM-lora
```

`demo` runs the production engine over frozen repositories and prints the
declared metadata, the strongest evidence, conflicts, the support score and the
decision — for a real adapter (`ADD`), a real merge (`KEEP`), a controlled
merge (`ADD`), a controlled wrong-parent case (`REPLACE`), a conflict
(`ABSTAIN`) and a real quantized derivative that the system declines to repair
(`ABSTAIN`). Every case is labelled `REAL` or `CONTROLLED`.

`audit` prints the same information for one repository, and works for any of the
44 frozen repositories.

## 3. Validate the benchmark (about 5 s)

```bash
python -m provenancelens.evaluation validate
```

Expected: `n_cases: 70` (26 CONTROLLED + 44 REAL), `errors: []`. Warnings are
expected and documented — see `docs/LIMITATIONS.md`.

## 4. Reproduce the research results (about 30 s)

```bash
python -m provenancelens.evaluation.phase_g_cli run --output /tmp/study
```

This writes the full study: metrics, nine ablations, failure analysis, evidence
contribution, risk–coverage, eleven tables and seven figures, plus a manifest
of input and output digests. Two runs produce byte-identical files.

To check the committed results instead of regenerating them:

```bash
python -m provenancelens.evaluation.phase_g_cli verify-canonical
python -m provenancelens.evaluation.phase_g_cli summary
```

## 5. Read the numbers

| I want to… | go to |
| --- | --- |
| see the headline results | [`results/phase_g/RESULTS.md`](../results/phase_g/RESULTS.md) |
| understand the method | [`docs/METHODOLOGY.md`](METHODOLOGY.md) |
| understand the code | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
| see what is *not* claimed | [`docs/CLAIMS.md`](CLAIMS.md) and [`docs/LIMITATIONS.md`](LIMITATIONS.md) |
| judge the study's weaknesses | [`docs/THREATS_TO_VALIDITY.md`](THREATS_TO_VALIDITY.md) |
| reproduce byte-for-byte | [`docs/REPRODUCIBILITY.md`](REPRODUCIBILITY.md) |
| read the whole project story | [`README.md`](../README.md) |

## Optional: figures

Tables and JSON need nothing extra. Figures need matplotlib:

```bash
pip install -e ".[plots]"
```

The study runs either way; when matplotlib is absent the figures are skipped,
the reason is recorded in the manifest, and every number still appears in the
tables. `results/phase_g/manifest.json` records exactly which figures were
written.

## Optional: local LLM prose extraction (never required)

```bash
pip install -e ".[llm]"
ollama serve                      # you start this; ProvenanceLens never does
ollama list                       # only if a model is ALREADY installed
python -m provenancelens.evaluation.phase_g_cli llm-compare --model llama3.2:3b
```

ProvenanceLens **never downloads a model**. If the model is absent the command
exits with a message telling you to install it yourself and changes nothing
else. This experiment is not part of the deterministic study and its output is
not in `results/`.

## If something fails

| Symptom | What it means |
| --- | --- |
| `error: no frozen snapshot for '<repo>'` | you asked to audit a repository this repository has not frozen; `audit` lists the frozen ones it can see |
| `SnapshotError` about hashes | a frozen file changed; frozen evidence is immutable by design, so restore it rather than editing the snapshot |
| `matplotlib is required for figures` | install the `plots` extra, or run with `--no-plots` |
| `model '<name>' is not installed locally` | the optional LLM experiment; install the model yourself, or ignore it |
| benchmark `validate` reports errors | stop: a benchmark defect makes every number untrustworthy. See `docs/REPRODUCIBILITY.md` |

## Next steps

* Deep dive on the method: [`docs/METHODOLOGY.md`](METHODOLOGY.md)
* Full measured results with denominators and intervals: [`results/phase_g/RESULTS.md`](../results/phase_g/RESULTS.md)
* Paper-style summary of contributions: [`docs/PAPER_NOTES.md`](PAPER_NOTES.md)
