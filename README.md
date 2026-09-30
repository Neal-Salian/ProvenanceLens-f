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
| LLM prose extraction (Phase E)     | ⬜ Not started |

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
* Prose extraction is still rule-based (no LLM yet — that is Phase E).
* Suggested patches are recommendations only; the tool never writes to external repositories.
* Evaluation so far is three frozen real repositories plus controlled cases — a prototype-scale evaluation, not a research result.

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
* ⬜ Open-weight LLM prose extraction (Phase E)
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
