# 🔍 ProvenanceLens

**Evidence-grounded model provenance and metadata repair system**

ProvenanceLens is a system designed to detect, evaluate, and repair missing or incorrect model metadata using evidence from model repositories and configuration sources.

Instead of blindly modifying metadata, ProvenanceLens collects available evidence, checks for conflicts, assigns confidence, and makes one of four decisions:

* **KEEP** — existing metadata is sufficiently supported
* **ADD** — metadata is missing but supported by evidence
* **REPLACE** — existing metadata conflicts with stronger evidence
* **ABSTAIN** — evidence is insufficient or conflicting, so no unsupported change is made

The system is designed around **traceable, evidence-based decisions** rather than guessing.

---

## 🎯 Problem

Model repositories often contain metadata describing a model's:

* Base model
* Fine-tuning relationships
* Quantization
* Architecture
* Training information
* Intended usage

This information can be incomplete, inconsistent, or distributed across multiple sources.

ProvenanceLens attempts to identify these inconsistencies and determine whether metadata should be preserved, added, replaced, or left unchanged.

---

## 🏗️ Architecture

The system separates deterministic processing from LLM-based prose extraction.

### Pipeline

```text
Repository / Metadata Evidence
            │
            ▼
     Evidence Extraction
            │
            ▼
       Claim Extraction
            │
            ▼
       Evidence Fusion
            │
            ▼
      Conflict Detection
            │
            ▼
      Confidence Scoring
            │
            ▼
   ┌────────┼─────────┐
   ▼        ▼         ▼
 KEEP      ADD     REPLACE
             \       /
              ▼     ▼
               ABSTAIN
```

Every decision is based on available evidence and confidence. When the system cannot safely support a repair, it abstains rather than guessing.

---

## ⚙️ Current Implementation

The Phase 2 prototype currently includes:

| Component                          | Status     |
| ---------------------------------- | ---------- |
| Evidence input                     | ✅ Working  |
| Deterministic JSON/config parsing  | ✅ Working  |
| Model-card relationship extraction | ✅ Working  |
| Hugging Face collection (Phase 3)  | ✅ Working  |
| Frozen evidence snapshots          | ✅ Working  |
| Conservative entity resolution     | ✅ Working  |
| Source-aware evidence fusion        | ✅ Working  |
| Structured conflict detection       | ✅ Working  |
| KEEP / ADD / REPLACE / ABSTAIN     | ✅ Working  |
| LangChain workflow (Phase 2 legacy)| 🟡 Partial |
| LLM prose extraction (Phase E)     | ✅ Working  |

The current implementation uses frozen evidence bundles for reproducible testing and a rule-based prose extractor.

---

## 📦 Phase 3 Evidence Collection

Phase 3 replaced frozen demo bundles with **real, reproducible repository evidence**. Three layers were added, each independently testable:

```text
Hugging Face repository
        │  1. collect (safety-first, size-capped)
        ▼
 CollectionResult ──► 2. freeze snapshot (repo + commit sha, read-only)
        │                      │
        │                      ▼
        └────────► 3. deterministic extraction (offline)
                             │
                             ▼
                 EvidenceExtraction
                 ├── declared lineage  (audit SUBJECT)
                 ├── declared evidence (role=declared)
                 ├── independent evidence (role=independent)
                 └── structural issues (data, not exceptions)
```

### 1. Collector (`provenancelens.collectors`)

* Only provenance-relevant **text** files: exact-root priority files (`README.md`, `config.json`, `adapter_config.json`, `tokenizer_config.json`, `generation_config.json`) plus keyword matches (`merge*`, `train*`, `adapter*`, `quantiz*`, `provenance*`).
* Model weights and binaries are excluded by name/type **before** any download; sizes come from repository metadata first, and a hard byte cap (default 1 MiB) is enforced again while streaming.
* Structured repository-level statuses (`SUCCESS`, `PARTIAL`, `NOT_FOUND`, `PRIVATE_OR_GATED`, `RATE_LIMITED`, `NETWORK_ERROR`, `INVALID_REPOSITORY`, `NO_RELEVANT_FILES`) keep per-file failures from discarding good evidence.
* Network access is confined to two injectable seams (`api`, `fetcher`) so the whole state machine is unit-tested offline; tokens are used for requests but never stored in results.

### 2. Frozen snapshots (`provenancelens.snapshots`)

* Identity is `repository + resolved commit sha` under `data/snapshots/<org__model>/<sha40>/`.
* Files are stored read-only with SHA-256 hashes; an identical re-collection is **reused**, a differing one raises a conflict instead of overwriting immutable evidence.
* `load_snapshot` is fully offline and verifies hashes, UTF-8 decodability, and path safety before parsing.

### 3. Deterministic extraction (`provenancelens.parsers`)

* **Declared vs independent is categorical:** README front-matter `base_model` is the subject of the audit (role `declared`, reliability `not_applicable`) and can never appear as proof in the independent list. Independent evidence never inherits the declared relation.
* Sources and typical reliability: `adapter_config.json` → `very_high` (relation `adapter`), merge configs → `high` (relation `merge`), training/config fields → `medium` (relation left `None` — a field names a model but does not state the relationship), README prose → `medium` (explicit phrases only).
* Local/checkpoint paths are rejected as public model IDs, but the raw value is preserved as evidence with a rejection note.
* Quantization relations are never derived from config presence, filenames, or format similarity.
* Every claim keeps its exact source file and key path; identical inputs always produce byte-identical output (no timestamps in extraction payloads).
* Malformed files become structured issues — one broken artifact never discards the rest.

New dependencies: `huggingface_hub`, `httpx`, `PyYAML` (parsing only uses `json.loads` and `yaml.safe_load` — repository content is data, never code).

Phase 3 collection **does not** make decisions: fusion, conflict scoring, entity resolution, and KEEP/ADD/REPLACE/ABSTAIN reasoning are Phase D, described next.

---

## 🧬 Phase D Evidence Reasoning and Repair Decisions

Phase D consumes frozen snapshot evidence (no network, no LLM) and produces a traceable `AuditDecision`:

```text
structured evidence
      ↓
conservative entity resolution   (exact / normalized / referent / unresolved / ambiguous / invalid)
      ↓
candidate aggregation           (one hypothesis per parent + one merge-source-set hypothesis)
      ↓
conflict detection              (structured, with the causing evidence attached)
      ↓
evidence fusion                 (reliability-, explicitness-, source- and relation-aware)
      ↓
decision                        (KEEP / ADD / REPLACE / ABSTAIN + suggested patch)
```

### Entity-resolution philosophy

Resolution answers one question only: *do these evidence strings clearly denote the same model?* It is deliberately not a model search.

| Status | Meaning | Example |
| --- | --- | --- |
| `EXACT` | already a canonical `org/name` id | `Qwen/Qwen2.5-7B-Instruct` |
| `NORMALIZED` | harmless formatting only | ` huggingface.co/org/name ` |
| `REFERENT` | the evidence itself shows the target | `Llama-2-7b-hf` with `meta-llama/Llama-2-7b-hf` in the same evidence |
| `UNRESOLVED` | a reference without an organization | `some/local/checkpoint` |
| `AMBIGUOUS` | several versions may exist | `Mistral 7B`, `Mistral-7B-v0.1` |
| `INVALID` | not a model reference | `/data/ckpt/model`, `model.safetensors` |

Never used: hub search or popularity ranking, architecture/vocabulary inference, organization-only or substring matching (`Qwen/…` ≉ `Qwen2.5-…`), or version guessing (`Mistral 7B` never becomes `mistralai/Mistral-7B-v0.1`). An unresolvable or ambiguous identifier forces **ABSTAIN** whenever resolution is required.

### Candidate aggregation and source independence

* One hypothesis per distinct resolved parent, so rival parents stay visible instead of being reduced to a silent winner; a merge is a separate hypothesis holding an ordered set of source slots (never one arbitrary parent).
* Declared evidence is structurally excluded from aggregation — the audited claim can never prove itself.
* Evidence is grouped by *source* (physical file plus control domain: `author_controlled` prose/specs, `tool_generated` adapter/training/merge artifacts, `system_write` framework files). Several fields of one training config count as **one** source; duplicates and repeated MergeKit slots cannot inflate support.
* Original `EvidenceItem` objects stay attached to every hypothesis, so each conclusion is re-derivable from the frozen evidence.

### Heuristic reliability, fusion, and `support_score`

| Tier | Typical source | Weight |
| --- | --- | --- |
| `very_high` | `adapter_config.json` parent field | 0.75 |
| `high` | merge/training configuration | 0.55 |
| `medium_high` | strong structured fields (schema-supported) | 0.45 |
| `medium` | `config.json` hints, explicit model-card prose | 0.30 |
| `weak` | naming/indirect hints | 0.12 |
| `not_applicable` | declared metadata being audited | 0 (never supports itself) |

Fusion sums per-`(file, reliability)` contributions, so one file contributes at most once per tier; the total is capped at 1.0. Evidence in the identifying tiers (`very_high`/`high`/`medium_high`) is summed, while hints only *corroborate* at a documented 0.5 discount — three weak hints can never outvote one explicit artifact. Implicit statements count half of their tier.

> **`support_score` is NOT a calibrated probability.** A score of 0.90 does **not** mean "90 % chance the repair is correct". It summarizes how strong the visible evidence is under the documented rubric. No benchmark calibration is claimed, and the score is not a research result. Because every input feature (per-item weight, explicitness, source kinds, control domains, relation completeness) is exposed, empirical calibration can be mapped in later without rewriting the pipeline.

### Conflict detection

`declared_vs_independent`, `competing_candidates`, `relation_conflict`, `multiple_merge_sources`, `version_ambiguity`, `unresolved_model_id`, `unknown_declared_relation`, `tool_failure`, `insufficient_independent_support` — each retaining the evidence items that caused it. Missing corroboration is deliberately *not* a conflict, and a weak hint below the affirmative bar never manufactures one.

### Decision policy

Thresholds are few, named, and heuristic (`DecisionPolicy` in `reasoning/fusion.py`):

| Threshold | Value | Why |
| --- | --- | --- |
| `min_support_affirmative` | 0.55 | one explicit `high` artifact: an affirmative finding exists at all |
| `min_support_keep` | 0.55 | accepting existing metadata needs real independent support |
| `min_support_add` | 0.55 | same bar: preserving and adding both need genuine evidence |
| `min_support_decisive` | 0.90 | strictly above one `very_high` artifact (0.75), so no single source can change declared metadata |
| `min_support_replace` | 0.90 | the decisive bar, plus the structural requirements below |

* **KEEP** — declared lineage is independently supported (≥ 0.55 from a parent-identifying tier) with no material contradiction. Declared metadata alone is never enough.
* **ADD** — nothing declared **and** an explicit, parent-identifying hypothesis whose relation is established (≥ 0.55). A single `adapter_config.json` record is sufficient; Phase 2's unconditional two-source rule is gone. A parent mention without a relation (`config._name_or_path`) is never an ADD.
* **REPLACE** — the highest-risk action: a genuine contradiction **and** decisive support (≥ 0.90) **and** a relation established by that evidence **and** not author-controlled prose only **and** no unresolved reference left that could denote the declared model. A relation-only contradiction (same parent, differing relation) with decisive support is also repairable, and the patch touches only the relation.
* **ABSTAIN** — no usable evidence, evidence too weak, unresolvable/ambiguous identifiers, several comparably supported incompatible candidates, a required relation that no evidence establishes, unresolved declared relations, or a conflict that cannot be settled safely. ABSTAIN is a successful, intended outcome and always carries a structured `reasoning_summary`; it never proposes a lineage or a patch.

### Multi-parent merge handling

A merge is compared **set-wise**: declared `[A, B, C]` against observed `[A, B]` is *incomplete independent evidence*, not proof that `C` is wrong, so it never triggers REPLACE. An independently observed set identical to the declared set yields KEEP. Merge proposals always keep the full set; nothing is collapsed to a single parent. A merge with fewer than two distinct, completely observed sources is not treated as a merge hypothesis.

### Parser/tool-failure semantics

Failures are represented, not obeyed: a collection or parse error adds a `tool_failure` conflict and leaves the evidence that did arrive usable, so a `VERY_HIGH` adapter record can still support ADD. Failure never decides anything by itself, and a blanket rule never forces ABSTAIN — weak remaining evidence abstains on its own merits.

### Suggested patch

ADD/REPLACE emit a `SuggestedPatch` (old/new `base_model`, old raw and new canonical relation) as **a recommendation inside the audit output only**. Nothing is pushed, no repository is modified, no PR is opened, and KEEP/ABSTAIN produce no patch. Remote writes are out of scope for this project.

### False-repair safety philosophy

> Priority: **false-repair safety** > evidence traceability > deterministic reproducibility > coverage > feature count.

Enforced by tests: declared metadata alone never proves itself; no independent evidence always abstains; weak name/organization/architecture similarity never changes lineage; unresolved or ambiguous identifiers abstain; several incompatible strong candidates abstain; one `very_high` explicit adapter config may support ADD; a weak conflict never REPLACEs; an incomplete merge source set never replaces a complete declared set; unsupported relations are never invented; ABSTAIN never carries a patch.

Determinism properties are tested as well: evidence ordering does not change a decision, duplicate evidence from one source cannot inflate support, weak unrelated evidence cannot flip a strong decision, and `support_score` always stays within `[0, 1]`.

---

## 🗣️ Phase E LLM-Assisted Prose Extraction (local, open-weight)

Phase C parses everything that is structured. Phase D reasons about it. **Phase E adds exactly one new evidence source: unstructured repository prose**, read by a local open-weight model through LangChain. The model is an *information-extraction component*, never a decision maker: the existing Phase D engine still produces every KEEP/ADD/REPLACE/ABSTAIN.

### Why an LLM at all, and only here

| Repository content | How it is read |
| --- | --- |
| README YAML front matter | YAML parser (deterministic) |
| `config.json`, `adapter_config.json` | JSON parser (deterministic) |
| MergeKit config | YAML parser (deterministic) |
| Training config | JSON/YAML parser (deterministic) |
| **Free-form model-card prose** | **LangChain + local LLM (Phase E)** |

Structured data is never sent to a model. Front matter is stripped *before* chunking, so declared metadata is never re-read by the LLM ("LLM last").

### Setup (no paid API, nothing auto-downloaded)

```bash
# 1. optional dependency for the LangChain path
pip install -e ".[llm]"

# 2. local model runtime (external application; install it yourself)
#    macOS: brew install ollama
#    then:  ollama serve

# 3. model (small enough for an 8 GB M2). ProvenanceLens never pulls models.
ollama pull llama3.2:3b

# 4. optional overrides
export PROVENANCELENS_LLM_MODEL=llama3.2:3b     # default
export PROVENANCELENS_LLM_BASE_URL=http://localhost:11434
export PROVENANCELENS_LLM_NUM_CTX=4096           # bounded context
```

The deterministic core never needs any of this. Without LangChain or Ollama the package still imports, collection/parsing/reasoning still work, and the LLM path reports `UNAVAILABLE` instead of failing.

### Pipeline components (all genuinely used)

```text
PromptTemplate(v1.0) → ChatOllama → StrOutputParser → PydanticOutputParser(ProseClaimSet)
```

* **PromptTemplate** — versioned (`PROSE_EXTRACTION_PROMPT_VERSION = "1.0"`) with a SHA-256 digest recorded in every report.
* **LCEL** — the chain above is a real `RunnableSequence`; only the model call is injectable for tests.
* **Pydantic structured output** — `ProseLineageClaim`/`ProseClaimSet`; unknown fields, non-canonical relations, and prose that is not a claim are rejected by the parser.
* **LangChain tools** — three read-only, offline snapshot lookups (`list_frozen_snapshots`, `lookup_frozen_lineage_evidence`, `read_frozen_model_card`); the Phase E workflow actually calls the model-card tool to obtain the prose it analyses. No agent is created, and no tool can execute repository code, download weights, or write metadata.

### Claim schema and meaning

| Field | Meaning |
| --- | --- |
| `claim_status` | `EXPLICIT` (direct parent clearly stated), `NO_CLAIM` (no lineage statement — a first-class valid answer), `AMBIGUOUS` (lineage-like wording, imprecise parent) |
| `candidate_parent` | exactly as it appears in the source text |
| `relation` | one of `finetune`, `adapter`, `merge`, `quantized`, or `null` when the relation is not stated |
| `evidence_span` | exact quotation from the supplied prose |
| `rationale_code` | deterministic code (e.g. `EXPLICIT_FINETUNE_PHRASE`, `PARENT_MENTION_WITHOUT_RELATION`, `NO_DIRECT_LINEAGE_CLAIM`) — never chain-of-thought |

### Validation and hallucination guards (all deterministic, fail closed)

A claim becomes evidence only if it survives every check:

1. **Span exists** in the chunk actually sent (exact substring; whitespace/case leniency only — never fuzzy matching).
2. **Parent appears in the span**, so a span and a parent cannot come from different sentences.
3. **Lineage is actually stated** — a span that merely names a model (comparison, leaderboard, tokenizer remark) is rejected.
4. **Non-lineage context rejected** — comparison/inspiration/acknowledgement wording is rejected even when it contains a relation word.
5. **Injection rejected** — a span that is an instruction aimed at the model is never treated as a claim; repository prose is fenced as untrusted data and its delimiters are neutralised.
6. **Model id validated** through the Phase D resolver; bare names stay unresolved, invalid values are rejected, and nothing is silently "repaired" into a convenient id.
7. **Relation corroborated** in the span; an unstated relation is downgraded to `null` rather than accepted because it seems plausible.

Rejected claims are recorded structurally (code + chunk index) and reported; they never become evidence and never abort the audit.

### Evidence produced by the LLM path

`EvidenceItem` with `extraction_method=LLM`, `role=INDEPENDENT`, `reliability=medium`, the verified `evidence_span`, the exact source file, and a note carrying prompt version, model, claim status, rationale code, and any relation downgrade. **LLM evidence is never more authoritative than the prose it came from**: it is author-controlled documentation, so it can corroborate but cannot outrank an adapter/training/merge configuration, and model self-reported confidence never influences `support_score`.

### Chunking and section selection (deterministic)

Headings first, then blank-line paragraphs, then a hard character split; code fences, inline code, HTML comments, and front matter are removed; every chunk keeps exact offsets back into the original file. Selection ranks lineage headings (`base model`, `training`, `merge`, `adapter`, `quantization`, ...) and lineage wording, with a bounded fallback so an unusual heading cannot hide a lineage statement. Budgets are laptop-friendly (≤1200 characters, ≤6 chunks, no parallelism).

### Modes and failure behaviour

```python
# deterministic only (default; no LLM code path involved)
audit_repository(repo, root=SNAPSHOT_ROOT)

# deterministic + validated prose claims
audit_repository_with_prose(repo, root=SNAPSHOT_ROOT, extractor=LLMProseExtractor(build_default_chat_model()))
```

LLM failures (runtime down, timeout, unparsable answer, failed validation) are recorded like any other tool failure: they add a `tool_failure`-style status, and deterministic evidence that was already sufficient still decides. A failed LLM never forces ABSTAIN, and it never blocks a safe deterministic decision.

### Optional live tests

```bash
PROVENANCELENS_LLM_TESTS=1 python3 -m pytest tests/test_phase_e_live_ollama.py
```

Skipped by default, and skipped again (never failed) when no local model is installed. The normal suite uses a canned `BaseChatModel`: the prompt, chain, parser, schema, and validation all run for real, and only local inference is replaced.

### Observed behaviour on the three frozen repositories

Documented in the test suite and reproducible offline. In the live run with `llama3.2:3b`, **no decision changed**; the guards rejected paraphrased spans, an unresolvable bare name, malformed output, and one leaderboard sentence that the small model misread as a finetune claim. `support_score` remains a heuristic evidence strength, **not** a calibrated probability, and LLM-derived evidence is not independently verified ground truth.

---

## 📊 Phase F Evaluation: LineageRepairBench

Phases B–E build the system; **Phase F measures it**. `LineageRepairBench` is a small, frozen, self-validating benchmark plus a reproducible, offline evaluation runner. It is not a new decision layer: the production engine is used unchanged.

```bash
python -m provenancelens.evaluation validate            # self-check + summary
python -m provenancelens.evaluation run --track controlled
python -m provenancelens.evaluation run --track real
python -m provenancelens.evaluation extraction           # prose-extraction quality
python -m provenancelens.evaluation all --output artifacts/evaluation
```

No network, no LLM, no paid API: the normal run re-uses the frozen snapshots and canned model answers. Generated artifacts go to `artifacts/evaluation/` (git-ignored) and are reproducible from the CLI.

### Two tracks, never mixed

| Track | Cases | Labels |
| --- | --- | --- |
| `CONTROLLED` | 26 | synthetic evidence bundles, labelled **by construction** |
| `REAL` | 3 | frozen real repository snapshots, **manually adjudicated** |

**How REAL ground truth was determined.** Never from ProvenanceLens output. Each label rests on the frozen artifact itself plus the published provenance of the model, and every case records an adjudication (adjudicator, files read, excerpt, rationale):

* `peft-internal-testing/tiny-OPTForCausalLM-lora` — `adapter_config.json` (written by PEFT at save time) records `base_model_name_or_path = hf-internal-testing/tiny-random-OPTForCausalLM` with `peft_type: LORA`. Parent **known**, relation **adapter**, declared metadata **missing** → expected `ADD`.
* `teknium/OpenHermes-2.5-Mistral-7B` — the front matter and `config.json` both name `mistralai/Mistral-7B-v0.1`, but **no artifact states the relation** (the card only says "a state of the art Mistral Fine-tune, a continuation of OpenHermes 2 model", with no canonical id). Metadata state is **undetermined**, not incorrect: no repair is expected (`KEEP` or `ABSTAIN`).
* `mergekit-community/Qwen3-1.5B-Instruct` — `mergekit_config.yml` lists two sources under `models:` plus a top-level `base_model:`; whether that key is an additional merged source or the residual base is an algorithm-semantics question the evidence does not settle. Parent set **ambiguous** (two admissible readings recorded), relation **merge** → no repair expected.

### Benchmark validation

The benchmark validates itself before any metric is computed and fails loudly on: duplicate case ids, invalid relation labels, `REPLACE` without adjudicated-incorrect metadata, `ADD` without missing metadata, `KEEP` on known-wrong metadata, repairs demanded on ambiguous truth, ambiguous truth without recorded alternatives, inconsistent declared state vs. labels, invalid expected parents, and REAL cases without manual adjudication. The validator never imports the decision engine, so it cannot manufacture a label from the system's own output.

Running the benchmark early caught a real defect in the fixtures: six cases claimed `VALID`/`INCORRECT` metadata while declaring none, so the engine saw "nothing declared" and answered `ADD`. Both the fixtures and a new validation rule were fixed; production behaviour was not touched.

### Metrics (denominators always explicit)

* **Parent identification** — exact-set match over cases with `KNOWN` parent truth; multi-parent truth compared order-insensitively.
* **Relation classification** — accuracy plus macro precision/recall/F1 over `finetune|adapter|merge|quantized|none` (`none` = "no relation established", a real outcome, not folded into a relation).
* **Action prediction** — accuracy plus macro precision/recall/F1 for `KEEP/ADD/REPLACE/ABSTAIN`; ambiguous cases accept any action in their `acceptable_actions`.
* **Repair safety** — abstention is never counted as correct.

> **False Repair Rate** = *incorrect attempted repairs* / *total attempted repairs*, where an attempted repair is an `ADD` or `REPLACE` whose proposed lineage contradicts **known** adjudicated truth. Attempts on non-knowable truth are reported separately as `unverifiable_repairs` — neither credited nor blamed. Zero denominators yield `null`, never `0.0`.

### Selective prediction

```
coverage           = non-ABSTAIN predictions / scored predictions
selective accuracy = correct predictions among non-ABSTAIN predictions
abstention rate    = ABSTAIN predictions / scored predictions
```

`python -m provenancelens.evaluation run` sweeps the raw `support_score` over 0.00–1.00 plus every observed value and reports, per operating point: threshold, coverage, selective accuracy, attempted repairs, false repairs and false-repair rate (`selective_metrics.csv`). This is a *threshold sweep*, not a calibration curve.

### Baselines

| Baseline | Behaviour |
| --- | --- |
| `declared_metadata` | trusts the declaration, never infers |
| `config_only` | production engine restricted to framework config evidence |
| `prose_only` | production engine restricted to model-card prose evidence |
| `majority_count` | picks the parent with the most evidence records; **ties abstain** |
| `rule_priority` | fixed source hierarchy (adapter > merge > training > config > prose), no fusion or conflict logic |
| `always_keep` | trivial reference, never the main comparator |
| `llm_full_context` | optional interface only — needs live local inference, so never a required dependency |

None is deliberately weakened, and each is scored with the same fields as the full system.

### Extraction quality, measured separately

11 labelled prose fixtures run through the real prompt/chain/parser/validation path (only inference is stubbed), yielding claim precision/recall/F1 and rejection counts by reason. Extraction errors are **not** attributed to downstream decisions: a rejected claim costs recall but is correct fail-closed behaviour, and an abstention does not imply the extractor was wrong.

### Measured results (this repository, this benchmark version)

Numbers below come from the committed benchmark; re-running the CLI reproduces them exactly. Per-track metrics are in `metrics.json`; `false_repair_rate` denominators are shown because several systems attempt few or no repairs.

| System | Action acc. | Parent acc. | Relation acc. | Coverage | Attempts | False repairs | False repair rate | Abstention |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `provenancelens` | 1.000 (29/29) | 0.688 (11/16) | 0.800 (12/15) | 0.414 | 7 | 0 | 0.000 (7 attempts) | 0.586 |
| `rule_priority` | 0.448 (13/29) | 0.875 (14/16) | 1.000 (15/15) | 0.966 | 20 | 1 | 0.050 (20 attempts) | 0.034 |
| `majority_count` | 0.345 (10/29) | 0.812 (13/16) | 0.667 (10/15) | 0.793 | 18 | 0 | 0.000 (18 attempts) | 0.207 |
| `config_only` | 0.586 (17/29) | 0.000 (0/16) | 0.000 (0/15) | 0.000 | 0 | 0 | n/a (0 attempts) | 1.000 |
| `prose_only` | 0.586 (17/29) | 0.000 (0/16) | 0.000 (0/15) | 0.000 | 0 | 0 | n/a (0 attempts) | 1.000 |
| `declared_metadata` | 0.586 (17/29) | 0.375 (6/16) | 0.333 (5/15) | 0.414 | 0 | 0 | n/a (0 attempts) | 0.586 |
| `always_keep` | 0.586 (17/29) | 0.375 (6/16) | 0.333 (5/15) | 0.414 | 0 | 0 | n/a (0 attempts) | 0.586 |

Per track for the full system:

| Track | Cases | Action acc. | Parent acc. | Attempts | False repairs |
| --- | --- | --- | --- | --- | --- |
| `controlled` | 26 | 1.000 (26/26) | 0.714 (10/14) | 6 | 0 |
| `real` | 3 | 1.000 (3/3) | 0.500 (1/2) | 1 | 0 |

Selective accuracy when answering: parent 11/11, relation 12/12. Action macro-F1 1.000.

Prose extraction over the labelled fixtures: precision 1.000 (6/6), recall 1.000 (6/6), rejection reasons matched 5/5.

What the numbers say (and do not say):

* **Repair safety vs coverage is the whole story.** ProvenanceLens attempts 7 repairs and none is wrong, but answers only 41.4 % of cases. `rule_priority` answers 96.6 %, scores *higher* on parent (0.875) and relation (1.000) accuracy, and still records a false repair — plus 10 of its 20 attempts are on truth that is not knowable (e.g. acting on a bare `Mistral 7B` reference), so its repairs cannot even be verified.
* **All strict parent/relation misses of the full system are abstentions**, not wrong answers: when it answers, parent accuracy is 11/11 and relation accuracy 12/12.
* **Action accuracy 1.000 on CONTROLLED is a specification check.** Those labels encode the documented policy; it confirms the implementation still matches its specification and says nothing about generality.
* `config_only` and `prose_only` abstain everywhere: honest, and also useless alone — neither evidence subset can certify lineage.
* `declared_metadata` / `always_keep` never repair, so their parent accuracy (0.375) is simply the share of cases where the declaration happens to be right.


### Benchmark limitations

* The CONTROLLED track is a **specification check**, not evidence of generality: its labels encode the documented policy, so a perfect score there means "the implementation still matches its specification" and nothing more.
* The REAL track has **three** adjudicated cases — far too few for statistically meaningful claims. Denominators are printed for every metric for that reason.
* Two of the three real cases are deliberately ambiguous/undetermined, so `parent_accuracy` there is dominated by cases where no answer was expected.
* Labels reflect what the stored evidence supports, not external truth about these models; the OpenHermes case would change if a training manifest were added to the snapshot.
* No calibration is reported (see below), and no baseline was tuned against the benchmark after labels were fixed.

### `support_score` is not a probability

The raw support score is a heuristic evidence strength (a capped sum of documented per-artifact contributions). Phase F therefore **does not** report ECE, Brier score, or reliability diagrams for it: doing so would present a non-probability as a calibrated one. Instead the evaluation package provides a `CalibratedScore` schema and mathematically standard ECE/Brier implementations that **refuse** uncalibrated inputs, plus a status object explaining which conditions are missing (a fitted mapping on a held-out split, ≥ 50 cases, a disjoint evaluation split). With 29 cases and no held-out split, probability calibration is deliberately **deferred** rather than faked.

### No research claims

ProvenanceLens makes no claim of state of the art, novelty, or empirical superiority: the benchmark is small, self-authored, and mostly synthetic. What it does show, on its own terms, is the intended trade-off — high repair safety at limited coverage — against simpler strategies that repair more often and less safely.

---

## 🧠 Decision Logic

ProvenanceLens uses four possible outcomes.

### KEEP

The existing metadata agrees with sufficiently strong evidence.

### ADD

The metadata is missing, but available evidence supports adding the claim.

### REPLACE

The existing metadata conflicts with stronger independent evidence.

### ABSTAIN

The system cannot make a safe decision because evidence is missing, conflicting, or retrieval failed.

This is an important safety mechanism: **lack of evidence does not become a reason to guess.**

---

## 🧪 Testing

Run the package test suite (offline — no network access):

```bash
python3 -m pytest -q
```

The Phase 2 notebook was executed against five controlled scenarios.

The tests include:

* Supported `ADD` decision
* Supported `REPLACE` decision
* Supported `KEEP` decision
* Conflicting independent evidence
* Tool/retrieval failure

In conflict and failure cases, the system produces **ABSTAIN** rather than making an unsupported repair.

Phase 3 additionally covers: collector selection/limits/statuses (mocked), snapshot immutability/path-safety/integrity, and front-matter/adapter/training/merge extraction with the declared-versus-independent invariant.

Phase D additionally covers: entity resolution, all controlled decision cases, false-repair safety invariants, determinism properties, and offline reasoning over the three frozen real repositories.

Phase F additionally covers: benchmark schema and self-validation, controlled and real tracks, metric semantics (strict vs coverage-conditioned, false-repair accounting, zero denominators, all-abstain and no-abstain systems), selective threshold sweeps, calibration guardrails, every baseline, runner determinism, CLI reproducibility in a clean subprocess, and frozen-snapshot integrity.

Phase E additionally covers: the prose claim schema and prompt contract, the real LangChain chain with a canned model (explicit/ambiguous/no-claim claims, multi-source merges, hallucinated spans, guessed parents/versions/relations, prompt injection, malformed and fenced output), chunking and section selection, the LangChain tools, Phase D integration and decision stability, and guarded imports without LangChain.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Rusheel86/ProvenanceLens.git
cd ProvenanceLens
```

### 2. Install the package

```bash
pip install -e ".[dev]"
```

### 3. Run the tests

```bash
python3 -m pytest -q
```

### 4. Run the notebook (historical Phase 2 prototype)

Open:

```text
ProvenanceLens_Phase2 (1).ipynb
```

and execute the cells sequentially.

---

## 📁 Project Structure

```text
ProvenanceLens/
│
├── ProvenanceLens_Phase2 (1).ipynb   # historical Phase 2 notebook (frozen)
├── README.md
├── CURRENT_STATE.md
├── pyproject.toml
│
├── data/
│   └── snapshots/                    # frozen evidence snapshots (created on demand)
│
├── src/provenancelens/
│   ├── collectors/                   # Hugging Face repository collection
│   ├── snapshots/                    # snapshot store (save/load/verify)
│   ├── parsers/                      # deterministic extraction
│   ├── prose/                        # Phase E: prompt, chunking, validation, extractor
│   ├── llm_runtime.py                # local model config + read-only availability probe
│   ├── tools.py                      # read-only LangChain snapshot tools
│   ├── evaluation/                   # Phase F: LineageRepairBench, metrics, baselines, CLI
│   ├── resolution/                   # conservative model-id resolution
│   ├── reasoning/                    # Phase D candidates/fusion/conflicts/decision
│   │   └── legacy.py                 # Phase 2 engine (regression baseline, untouched)
│   ├── pipeline.py                   # snapshot -> evidence -> AuditDecision
│   ├── schemas/                      # evidence, lineage, collection, snapshot, audit models
│   ├── langchain_integration/        # Phase 2 workflow (guarded imports)
│   └── reporting/
│
└── tests/                            # pytest suite (offline)
```

---

## 🔎 Example

Given existing metadata:

```json
{
  "base_model": "Model-A"
}
```

and evidence indicating:

```text
Independent evidence:
base_model = Model-B
confidence = high
```

ProvenanceLens can produce:

```json
{
  "decision": "REPLACE",
  "field": "base_model",
  "old_value": "Model-A",
  "new_value": "Model-B",
  "confidence": "high",
  "evidence": [...]
}
```

If the evidence is contradictory:

```json
{
  "decision": "ABSTAIN",
  "reason": "Conflicting independent evidence"
}
```

---

## 🛡️ Design Principles

### Evidence over assumptions

The system does not invent metadata when evidence is unavailable.

### Reproducibility

Phase 2 uses frozen evidence bundles so that experiments can be reproduced consistently.

### Traceability

Decisions retain the evidence used to reach them.

### Safe failure

When evidence is missing or conflicting, ProvenanceLens chooses `ABSTAIN`.

---

## ⚠️ Current Limitations

* `support_score` is a **heuristic evidence strength**, not a calibrated probability; no benchmark-calibrated confidence is claimed.
* Repair decisions on real repositories are **system conclusions from current evidence**, not independently verified truth; only manual adjudication can establish that repository metadata is actually wrong.
* Entity resolution never searches the hub, so bare model names without an organization conservatively abstain.
* Prose extraction has two paths: deterministic rules plus an optional local LLM; a small local model still produces paraphrased or misread claims, so validation rejects them and coverage is conservative rather than high.
* Suggested patches are recommendations only; the tool never writes to external repositories.
* Evaluation (Phase F) is a small self-authored benchmark: 26 controlled cases and 3 adjudicated real cases. It documents the safety/coverage trade-off; it is not a research result and supports no superiority claims.

---

## 🔮 Phase 3 Roadmap

Progress:

* ✅ Connect selected public Hugging Face repositories (lightweight collector)
* ✅ Store frozen evidence snapshots (repo + commit identity, read-only)
* ✅ Entity resolution, evidence fusion, conflicts, and KEEP/ADD/REPLACE/ABSTAIN (Phase D)
* 🟡 Expand evaluation with additional test cases
* 🟡 Manually adjudicate real-repository outcomes (decisions are heuristic, not ground truth)
* ⬜ Include poor/failed retrieval cases at scale
* ⬜ Preserve explicit evidence citations end-to-end
* ✅ Open-weight LLM prose extraction, local-first and fail-closed (Phase E)
* ✅ LineageRepairBench evaluation, baselines and repair-safety metrics (Phase F)
* ⬜ Keep using `ABSTAIN` whenever a repair cannot be safely supported

---

## 👥 Team

| Team Member    | Contribution                                          |
| -------------- | ----------------------------------------------------- |
| Neal Salian    | Repository evidence collection and structured parsing |
| Rusheel Sharma | LangChain workflow, prompt and output schema          |
| Veer Shetty    | Evidence scoring, tests, evaluation and demonstration |

---

## 📚 Project Context

ProvenanceLens was developed as part of the **Lab 9 PSIS – Activity 2** Phase 2 submission.

**Team:** Neal Salian (I062), Rusheel Sharma (I069), Veer Shetty (I071)
