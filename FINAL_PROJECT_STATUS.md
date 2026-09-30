# Final project status — ProvenanceLens

**Date:** 2026-10-01 · **Branch:** `feat/phase3-h` · **Phases A–H complete**

## Objective

Audit the *direct model-lineage metadata* an open model repository declares about
itself (`base_model`, `base_model_relation`) and decide whether that declaration
should be **kept, completed, replaced, or left alone** — repairing only when the
evidence supports it, and abstaining otherwise.

## Phases

| phase | delivered |
| --- | --- |
| **A** | audit of the original Phase-2 notebook (preserved byte-identical) |
| **B** | structured Python package: schemas, deterministic parsers, regression tests |
| **C** | safety-first Hugging Face collection; frozen, hash-verified, offline-reproducible snapshots |
| **D** | conservative resolution, evidence independence, fusion, conflict detection, KEEP/ADD/REPLACE/ABSTAIN |
| **E** | optional local open-weight prose extraction with grounding validation, hallucination rejection and fail-closed behaviour |
| **F** | LineageRepairBench: CONTROLLED + REAL tracks, metrics, baselines, selective evaluation, calibration guardrails |
| **G** | the experimental study: 44 adjudicated real repositories, nine ablations, failure/evidence/risk-coverage analyses, tables, figures, optional LLM comparator |
| **H** | finalisation: documentation set, offline demo, reproducible canonical results, packaging and CLI quality, integrity tests |

## Architecture in one paragraph

Collect provenance-relevant text (never weights) → freeze it at a pinned commit
with SHA-256 per file → parse deterministically into evidence items split
categorically into *declared* (the audit subject) and *independent* (evidence
about it) → resolve identifiers conservatively → aggregate candidates per parent
and relation → fuse with reliability and independence weighting, capped per file →
detect conflicts → apply the decision policy. An optional local LLM may only add
prose claims that pass grounding validation; failures are reported outcomes, never
crashes. Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Benchmark

| | count |
| --- | --- |
| CONTROLLED | 26 |
| REAL (adjudicated public repositories) | 44 |
| **total** | **70** |

38 of the 70 parent truths are **not knowable** by adjudication, and 32 cases have
no independent evidence at all.

## Headline measured results

| metric | combined | real track |
| --- | --- | --- |
| action accuracy | 62/70 = 0.886 | 36/44 = 0.818 |
| parent exact match | 19/32 = 0.594 | 9/18 = 0.500 |
| relation accuracy | 21/31 = 0.677 | 10/18 = 0.556 |
| coverage | 21/70 = 0.300 | 10/44 = 0.227 |
| repair attempts | 12 | 6 |
| **false repairs** | **0/12** | **0/6** |
| unverifiable repairs | 0/12 | 0/6 |
| abstention rate | 49/70 = 0.700 | 34/44 = 0.773 |

All 7 errors were abstentions. Weakest stratum: `quantized_awq` 0/5. Source:
[`results/phase_g/RESULTS.md`](results/phase_g/RESULTS.md); supported and
unsupported claims: [`docs/CLAIMS.md`](docs/CLAIMS.md).

## Test and reproducibility status

| item | status |
| --- | --- |
| test suite | **563 passed, 7 skipped** offline (skips are opt-in live tests) |
| study determinism | two runs byte-identical; no stochastic component |
| environment independence | minimal install (no matplotlib, no LangChain) gives identical metrics |
| canonical results | `results/phase_g/` verified by `study verify-canonical` and by tests |
| network | not required for the package, tests, benchmark, demo, study or canonical results |
| production packages | byte-identical to the Phase F merge — finalisation changed no behaviour |
| legacy notebook | unmodified, SHA-256 asserted in tests |
| frozen snapshots | 44 verified by `load_snapshot`, 107 files, 0 weight files, ~1.2 MB |
| secrets | none in tracked files; only public upstream placeholders in frozen artifacts |
| packaging | `pip install -e .` works; optional `plots`, `llm`, `dev` extras; no paid APIs |

## Known limitations (the short list)

* 70 self-authored cases; 44 real repositories, one adjudicator, one ecosystem.
* `support_score` is not a probability; probability calibration stays deferred.
* `quantized_awq` 0/5, deliberately not "fixed" — that would be fitting the benchmark.
* Prose and framework config changed no decision on this benchmark.
* The duplicate-inflation hypothesis was not confirmed and is reported as measured.
* Local LLM (`llama3.2:3b`): 20 claims, 0 accepted, 0 false repairs.
* **0/12 false repairs is an observed count, not a guarantee** (95% CI to 0.242).

Full treatment: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md),
[`docs/THREATS_TO_VALIDITY.md`](docs/THREATS_TO_VALIDITY.md).

## Important commands

```bash
python -m pytest -q                                      # full suite
python -m provenancelens.demo                            # offline walkthrough
python -m provenancelens.cli audit <repository>          # audit one frozen repo
python -m provenancelens.evaluation validate             # benchmark self-check
python -m provenancelens.evaluation.phase_g_cli run --output /tmp/study
python -m provenancelens.evaluation.phase_g_cli verify-canonical
python -m provenancelens.evaluation.phase_g_cli publish  # regenerate results/
```

## Repository readiness

Ready for a final presentation and submission. A reviewer with 5–10 minutes should
follow [`docs/QUICKSTART.md`](docs/QUICKSTART.md); a reviewer assessing the
research should start at [`results/phase_g/RESULTS.md`](results/phase_g/RESULTS.md)
and then read [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) and
[`docs/THREATS_TO_VALIDITY.md`](docs/THREATS_TO_VALIDITY.md).

Nothing in this repository requires a network, a model hub account, a GPU, or a
local LLM to install, test, demonstrate, or reproduce the research results.
