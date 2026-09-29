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
| LangChain workflow                 | 🟡 Partial |
| Evidence fusion                    | ✅ Working  |
| Conflict detection                 | ✅ Working  |
| Confidence-based decisions         | ✅ Working  |
| KEEP / ADD / REPLACE / ABSTAIN     | ✅ Working  |
| Failure handling                   | ✅ Working  |
| Traceable evidence output          | ✅ Working  |

The current implementation uses frozen evidence bundles for reproducible testing and a rule-based prose extractor.

---

## 📦 Phase 3 Evidence Collection

Phase 3 (in progress) replaces frozen demo bundles with **real, reproducible repository evidence**. Three layers were added, each independently testable:

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

Phase 3 collection **does not** make decisions: fusion, conflict scoring, entity resolution, and KEEP/ADD/REPLACE/ABSTAIN reasoning remain Phase D.

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
│   ├── schemas/                      # evidence, lineage, collection, snapshot models
│   ├── reasoning/                    # Phase 2 fusion/decisions (Phase D)
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

The current Phase 2 implementation uses:

* Frozen demonstration evidence
* Rule-based prose extraction
* Controlled test cases

It is therefore a prototype rather than a complete production system.

---

## 🔮 Phase 3 Roadmap

Progress:

* ✅ Connect selected public Hugging Face repositories (lightweight collector)
* ✅ Store frozen evidence snapshots (repo + commit identity, read-only)
* 🟡 Manually verify expected lineage labels (real-repository smoke tests)
* ⬜ Expand evaluation with additional test cases
* ⬜ Include poor/failed retrieval cases
* ⬜ Preserve explicit evidence citations end-to-end
* ⬜ Entity resolution, evidence fusion, conflicts, and calibrated decisions (Phase D)
* ⬜ Continue using `ABSTAIN` when a repair cannot be safely supported

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
