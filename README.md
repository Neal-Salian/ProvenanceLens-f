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

The Phase 2 notebook was executed against five controlled scenarios.

The tests include:

* Supported `ADD` decision
* Supported `REPLACE` decision
* Supported `KEEP` decision
* Conflicting independent evidence
* Tool/retrieval failure

In conflict and failure cases, the system produces **ABSTAIN** rather than making an unsupported repair.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Rusheel86/ProvenanceLens.git
cd ProvenanceLens
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the notebook

Open:

```text
ProvenanceLens_Phase2.ipynb
```

and execute the cells sequentially.

> Add the exact notebook filename here if it differs from the repository filename.

---

## 📁 Project Structure

```text
ProvenanceLens/
│
├── ProvenanceLens_Phase2.ipynb
├── README.md
├── requirements.txt
│
├── data/
│   └── evidence/
│
├── outputs/
│   └── ...
│
└── ...
```

Update this section to match the actual repository structure.

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

Planned improvements include:

* Connect selected public Hugging Face repositories
* Store frozen evidence snapshots
* Introduce an open-weight LLM for prose claim extraction
* Manually verify expected lineage labels
* Expand evaluation with additional test cases
* Include poor/failed retrieval cases
* Preserve explicit evidence citations
* Continue using `ABSTAIN` when a repair cannot be safely supported

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
