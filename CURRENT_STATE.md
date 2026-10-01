# CURRENT_STATE — ProvenanceLens Phase A Audit

Date: 2026-09-29
Branch: `feat/phase3` (active, clean, up to date with `origin/feat/phase3`)
Remotes: `origin` = Neal-Salian/ProvenanceLens-f (fork), `upstream` = Rusheel86/ProvenanceLens
Environment: macOS (Apple M2, 8 GB RAM), Python 3.13.3, no GPU used.

---

## 1. Current repository structure

```text
ProvenanceLens-f/
├── .git/
├── LICENSE                        (MIT)
├── README.md                      (Phase 2 era, partially inaccurate)
├── ProvenanceLens_Phase2 (1).ipynb   (the entire Phase 2 implementation)
├── CURRENT_STATE.md               (this file)
└── (nothing else — no src/, tests/, data/, outputs/, requirements.txt, .gitignore)
```

Git history (3 commits): `Initial commit` → `colab run` → `Create README.md`.
Only 3 tracked files. Working tree clean, no ignored files, **no `.gitignore`**.

---

## 2. How the existing implementation works

The whole system lives in `ProvenanceLens_Phase2 (1).ipynb` (12 cells: 5 markdown, 7 code).
It was authored for Google Colab (metadata shows Colab kernel, Python 3.11, T4 GPU).

### Cell-by-cell

| Cell | Type | Content |
|---|---|---|
| 0 | md | Title, team, scope statement (frozen sample evidence) |
| 1 | md | Architecture one-liner: bundle → structured parsing → prose claims → scoring → 4 decisions |
| 2 | code | Imports; guarded `try/except` import of pydantic + `langchain_core` → sets `LANGCHAIN_AVAILABLE` |
| 3 | code | `LineageDecision` Pydantic model; `claim_prompt` (PromptTemplate); `decision_parser` (JsonOutputParser); `RELATION_PATTERNS` regex table |
| 4 | md | Note that samples are synthetic |
| 5 | code | `SAMPLES`: 5 frozen evidence bundles (see scenarios below) |
| 6 | code | `extract_evidence()`, `decide_lineage()`, `audit()` (LCEL chain of two `RunnableLambda`s, or plain fallback) |
| 7 | md | "Test results" |
| 8 | code | Runs all 5 scenarios, prints result table |
| 9 | md | Structured output header |
| 10 | code | Prints JSON of the REPLACE case |
| 11 | md | Phase 3 remaining work notes |

### Data model (implicit, plain dicts — no Pydantic for evidence)

Evidence bundle keys: `model_id`, `metadata {base_model, base_model_relation}`, `config {_name_or_path}`, `readme`, `tool_errors`.
Claims (dicts): `{parent, relation, source, weight}` with weights: metadata=0, README=2, config.json=3.

### Extraction (`extract_evidence`, notebook cell 6)

- Declared `metadata.base_model` → claim with weight 0 (excluded from "independent" evidence).
- `config._name_or_path` if it contains `/` → independent claim, weight 3, relation = *declared* relation or `"fine-tune"`.
- README prose → regex scan over `RELATION_PATTERNS` (fine-tune / adapter / merge / quantized), first match per pattern, weight 2.
  Patterns require an `org/name` shape: `[\w.-]+/[\w.-]+`.

### Scoring + decision (`decide_lineage`, notebook cell 6)

1. No independent claims → **ABSTAIN**, confidence 0.10, errors reported as conflicting evidence.
2. Sum weights per candidate parent. Ranked list.
3. If 2+ candidates and (top − runner < 2) → **ABSTAIN**, confidence 0.45.
4. Else if fewer than 2 *distinct supporting sources* for the winner → **ABSTAIN**, confidence 0.55.
5. Else winner accepted: `KEEP` if declared == winner, `ADD` if no declared, `REPLACE` otherwise;
   confidence = `min(0.95, 0.65 + 0.05 * top_score)`.
6. Supporting/conflicting evidence rendered as **strings**; declared mismatch appended to conflicts;
   `tool_errors` appended to conflicts.

### LangChain usage (actual vs declared)

- `PromptTemplate` (`claim_prompt`) and `JsonOutputParser` (`decision_parser`) are **constructed but never invoked**.
- The real "chain" is `RunnableLambda(extract_evidence) | RunnableLambda(decide_lineage)` — valid LCEL syntax, but LangChain adds no behavior.
- Prose extraction is **pure regex**; no LLM is ever called. No paid API used anywhere (also no free LLM used).
- Graceful degradation works: with LangChain absent, results are identical (verified).

### The five Phase 2 scenarios (verified by execution)

| # | model_id | Expected | Observed | confidence |
|---|---|---|---|---|
| 1 | demo/missing-lineage-model | ADD | **ADD** → meta-llama/Llama-3.2-1B | 0.90 |
| 2 | demo/conflicting-lineage-model | REPLACE | **REPLACE** → meta-llama/Llama-3.2-1B | 0.90 |
| 3 | demo/correct-lineage-model | KEEP | **KEEP** → meta-llama/Llama-3.2-1B | 0.90 |
| 4 | demo/ambiguous-lineage-model | ABSTAIN | **ABSTAIN** (config=Qwen vs README=Llama) | 0.45 |
| 5 | demo/tool-failure-model | ABSTAIN | **ABSTAIN** (README/config retrieval errors) | 0.10 |

Execution results were reproduced **twice locally** (with and without LangChain installed) and match the
outputs stored in the notebook exactly. → The prototype is deterministic and the 5 scenarios are a
reliable regression baseline.

---

## 3. What is fully working

- Deterministic `extract_evidence` + `decide_lineage` logic (pure Python, no I/O).
- All five scenarios produce the intended KEEP / ADD / REPLACE / ABSTAIN results.
- Tool-failure → ABSTAIN path.
- Ambiguous/conflicting-evidence → ABSTAIN path.
- Guarded imports (runs with or without LangChain).
- Structured JSON output for a single decision (as plain dict).

## 4. What is partially working

- **LangChain**: classes exist but the prompt/parser are dead code; no model invocation; no tools.
- **README "Testing" section**: describes manual notebook execution; there is no test suite.
- **README project structure / requirements.txt**: referenced but do not exist.
- **Conflict handling**: conflicts are flat strings inside the output, not structured objects.

## 5. What is missing (everything Phase 3 requires)

- Python package / modules; CLI (`python -m provenancelens audit org/model`).
- `huggingface_hub` collector (dependency is installed but unused by the project).
- Frozen snapshot store (manifest, revision, timestamps, URLs).
- Pydantic schemas for evidence / claims / audit results.
- Real parsers: README YAML front matter, `adapter_config.json`, MergeKit YAML, training configs.
- Entity resolution / conservative model-ID resolution with ambiguity → ABSTAIN.
- Reliability hierarchy (very_high … weak) and reliability-weighted fusion.
- Structured conflict objects (declared-vs-independent, version, relation, multi-source, LLM-vs-config).
- Real prose claim extraction (LLM-last, local/Ollama, optional, never crashing).
- Human-readable audit report + suggested metadata patch.
- pytest suite; evaluation metrics; LineageRepairBench scaffold; baselines.
- Phase 3 notebook; optional Streamlit UI.
- `.gitignore`, `requirements.txt` / `pyproject.toml`.

---

## 6. Phase 2 code worth preserving (explicitly)

1. **The five SAMPLES bundles** → become regression tests verbatim (scenario 1–5 above).
2. **`RELATION_PATTERNS` regexes** → seed `parsers/prose.py` rule-based fallback extractor
   (keep behavior for scenario tests; Phase 3 adds strictness: full HF-ID validation, no false `org/path` matches).
3. **`extract_evidence` / `decide_lineage` control flow** → preserve as the behavioral baseline in
   `reasoning/` refactored into reliability-weighted fusion + explicit thresholds; regression tests must
   keep the 5 outcomes identical.
4. **`LineageDecision` Pydantic model** → extended into `schemas/audit.py` (Action enum, evidence lists,
   conflicts, support_score, patch).
5. **Guarded LangChain import + graceful fallback** → keep the "no LLM / no LangChain ⇒ deterministic path,
   conservative decision" invariant.
6. **Result table + JSON dump cells** → become the Phase 3 demo notebook's report section.

## 7. Technical debt / problems discovered

1. Notebook filename `ProvenanceLens_Phase2 (1).ipynb` is a Colab download artifact (space + "(1)").
2. No `requirements.txt` (README instructs `pip install -r requirements.txt`) and no `pyproject.toml`.
3. No `.gitignore` — generated caches/outputs would be committed accidentally.
4. README claims a project structure (`data/evidence`, `outputs/`) that does not exist; test claims exceed reality.
5. LangChain prompt/parser are dead code — coursework requirement (PromptTemplate, tools, LCEL, output parser)
   is only cosmetically met today.
6. `confidence` values are ad-hoc (0.65 + 0.05·score) — must be renamed/reframed as `support_score`
   (heuristic, not calibrated probability), per research-defensibility rule.
7. Relation vocabulary mismatch: notebook uses `fine-tune`; Phase 3 spec uses `finetune`
   (need canonical enum + normalization of variants like `fine-tune`, `fine_tune`, `ft`).
8. `config._name_or_path` is assigned the *declared* relation (`relation or "fine-tune"`) — circular:
   declared metadata contaminates "independent" evidence. Phase 3 must infer relation from the source itself.
9. `_name_or_path` is often a local path or the model's own id → needs validation + reliability downgrade,
   not blanket weight 3.
10. Hard rule "≥2 distinct sources or ABSTAIN" conflicts with Phase 3 reliability design where a single
    `adapter_config.json` is VERY_HIGH and may justify ADD alone. Needs redesign while keeping
    scenario outcomes identical.
11. Evidence is untraceable strings — no source_type/revision/URL/span/extraction_method/reliability fields.
12. Regex can match any `foo/bar` (e.g. dataset names, file paths) — spec explicitly forbids treating every
    slash-string as a model ID.
13. `tool_errors` do not affect the decision directly; a failed retrieval alongside ≥2 claims would still
    produce a repair — must be modeled as audit state with abstain pressure.
14. Ambiguity detection is score-margin only; no version-ambiguity, relation-conflict, or
    multi-merge-source detection.
15. Single `re.search` per pattern → only first README mention captured; no `NO_CLAIM` concept.
16. No separation of live vs snapshot mode; no reproducibility metadata (commit SHA, retrieval time).

---

## 8. Proposed Phase 3 structure

Only modules with real functionality; names per spec §7.

```text
ProvenanceLens-f/
├── pyproject.toml                # package + deps + console entry
├── requirements.txt              # README compatibility
├── .gitignore
├── README.md                     # rewritten to match reality
├── CURRENT_STATE.md
├── LICENSE
├── src/provenancelens/
│   ├── __init__.py
│   ├── schemas/
│   │   ├── evidence.py           # EvidenceItem, Reliability, Explicitness, Relation, ExtractionMethod
│   │   ├── claims.py             # LineageClaim, NO_CLAIM, ProseExtractionResult
│   │   ├── audit.py              # Action enum, CurrentLineage, Conflict, AuditResult, SuggestedPatch
│   │   └── snapshot.py           # SnapshotManifest, CollectedFile, CollectorStatus
│   ├── collectors/
│   │   └── huggingface.py        # lightweight file collection, error states (no weights download)
│   ├── snapshots/
│   │   └── store.py              # save/load frozen snapshots (live & snapshot modes)
│   ├── parsers/
│   │   ├── metadata.py           # README YAML front matter: base_model, base_model_relation
│   │   ├── configs.py            # config.json, training configs (model_name_or_path, ...)
│   │   ├── adapter.py            # adapter_config.json → base_model_name_or_path
│   │   ├── merge.py              # MergeKit YAML → models/sources/slices (multi-parent)
│   │   └── prose.py              # rule-based regex fallback (ported RELATION_PATTERNS + NO_CLAIM)
│   ├── resolution/
│   │   └── model_ids.py          # conservative id resolution, version-ambiguity detection
│   ├── reasoning/
│   │   ├── candidates.py         # claims → CandidateParent aggregation
│   │   ├── fusion.py             # reliability-weighted support (heuristic, interpretable)
│   │   ├── conflicts.py          # structured Conflict objects
│   │   ├── confidence.py         # support_score (calibration-ready, not a probability)
│   │   └── decision.py           # KEEP/ADD/REPLACE/ABSTAIN rules incl. abstain pressure
│   ├── langchain_integration/
│   │   ├── prompts.py            # PromptTemplate (strict claim extraction, NO_CLAIM)
│   │   ├── tools.py              # HuggingFaceRepositoryTool, PaperTextTool (meaningful tools)
│   │   ├── chains.py             # LCEL chain: prompt | model? | parser
│   │   └── output_parsers.py     # Pydantic/JSON structured output parser
│   ├── reporting/
│   │   ├── report.py             # machine JSON + human-readable audit report
│   │   └── patch.py              # suggested metadata patch (never auto-pushed)
│   ├── pipeline.py               # audit_model(repo_id, mode=live|snapshot) orchestration
│   └── cli.py                    # python -m provenancelens audit org/model
├── tests/
│   ├── test_phase2_regression.py # the 5 scenarios, verbatim
│   ├── test_parsers.py           # metadata/adapter/merge/training configs + malformed input
│   ├── test_resolution.py        # ambiguity → ABSTAIN
│   ├── test_fusion.py            # weak-vs-strong evidence, multi-parent merge
│   ├── test_conflicts.py
│   ├── test_decision.py          # all invariants (no evidence→ABSTAIN, etc.)
│   ├── test_collector.py         # network failure / missing files / invalid JSON (mocked)
│   └── test_reporting.py
├── data/
│   ├── snapshots/                # frozen org__model/<revision>/manifest.json + files
│   └── benchmark/                # LineageRepairBench scaffold (schema only, labeled "scaffold")
├── notebooks/
│   ├── ProvenanceLens_Phase2.ipynb        # preserved, renamed from "(1)" artifact
│   └── ProvenanceLens_Phase3_Demo.ipynb   # imports the package
└── outputs/                      # generated reports (gitignored)
```

Notes:
- `langchain_integration/` instead of `langchain/` to avoid any import-shadowing confusion (spec allows deviation).
- No `collectors/papers.py` / `history.py` until they contain real functionality (documented as optional future work).
- Optional Streamlit UI only after the pipeline is correct (Phase G, last).

## 9. Exact implementation sequence (with commits)

Phase A (this document) — no code changes to Phase 2.
**Commit:** `docs: audit existing phase 2 prototype and plan phase 3`

Phase B — REFACTOR
1. Add `pyproject.toml`, `requirements.txt`, `.gitignore`.
2. Create `src/provenancelens/` skeleton + `schemas/` Pydantic models.
3. Port Phase 2 logic into `parsers/prose.py` + `reasoning/` (behavior-preserving).
4. pytest: `test_phase2_regression.py` with the 5 scenarios → same outputs.
**Commits:** `chore: add packaging and gitignore`, `refactor: extract phase 2 logic into reusable modules`,
`test: preserve phase 2 decision scenarios`

Phase C — REAL HF DATA
5. `collectors/huggingface.py` (small files only; structured error states).
6. `snapshots/store.py` (manifest: repo, revision, timestamp, files, URLs; live & snapshot modes).
7. Real parsers: metadata YAML front matter, adapter, merge, training configs (+ malformed-input tests).
8. Smoke-test against a few real public repos → freeze snapshots under `data/snapshots/`.
**Commits:** `feat: add hugging face repository collector`, `feat: add frozen evidence snapshots`,
`feat: add deterministic lineage parsers`

Phase D — EVIDENCE REASONING
9. `resolution/model_ids.py` (conservative; version ambiguity → ABSTAIN).
10. `reasoning/candidates.py` + `fusion.py` (reliability hierarchy, multi-parent merges).
11. `reasoning/conflicts.py` (structured conflicts).
12. `reasoning/confidence.py` + `decision.py` (support_score; all spec invariants as tests).
**Commits:** `feat: add conservative model id resolution`, `feat: add evidence fusion and candidate aggregation`,
`feat: add lineage conflict detection`, `feat: implement evidence-backed repair decisions`

Phase E — LANGCHAIN
13. PromptTemplate (strict, NO_CLAIM), Pydantic output parser, meaningful tools, LCEL chain in
    `langchain_integration/`; optional Ollama/local model with lazy import; absence ⇒ deterministic path,
    conservative decision, never crash.
**Commit:** `feat: integrate langchain prose extraction`

Phase F — EVALUATION
14. `reporting/` (JSON + human report + patch), benchmark schema scaffold, metrics
    (parent accuracy, relation/repair macro-F1, false-repair rate, coverage, selective accuracy),
    simple baselines, threshold/coverage data.
**Commits:** `feat: add audit reports and metadata patch output`,
`feat: add lineage repair evaluation metrics`, `docs: scaffold lineagerepairbench`

Phase G — DEMO
15. `pipeline.py` + `cli.py`; `notebooks/ProvenanceLens_Phase3_Demo.ipynb` (imports package);
    verified real-repo examples (KEEP/ADD/REPLACE/ABSTAIN where honest); README rewrite to match reality;
    optional Streamlit UI last.
**Commits:** `feat: add audit cli and pipeline`, `feat: add phase 3 demo notebook`,
`docs: document phase 3 workflow`

Testing gate: `pytest` green at the end of every phase; no secrets; no weight downloads;
push only to `origin feat/phase3`.
