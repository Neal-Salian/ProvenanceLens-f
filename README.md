# 🔍 ProvenanceLens

**Evidence-calibrated repair of direct model-lineage metadata in open model repositories.**

ProvenanceLens audits the lineage metadata a model repository declares about itself
— `base_model` and `base_model_relation` — and decides whether that declaration
should be kept, completed, replaced, or left alone. It gathers evidence from the
repository's own artifacts, resolves identifiers conservatively, detects conflicts,
and refuses to recommend a change it cannot support. It never writes to an
external repository: every repair is a recommendation for a human to accept.

Four outcomes, and the fourth is the point:

| decision | meaning |
| --- | --- |
| **KEEP** | the declared lineage is supported; change nothing |
| **ADD** | nothing direct is declared, but evidence supports a specific parent and relation |
| **REPLACE** | the declaration is contradicted by decisive evidence |
| **ABSTAIN** | evidence is insufficient, unresolvable or conflicting — no change is recommended |

---

## 🎯 The Problem

Open model repositories declare *direct* lineage: the model they were derived
from, and how. Those declarations are frequently:

* **missing** — adapters and quantized derivatives often omit `base_model` entirely;
* **incomplete** — a parent is declared but `base_model_relation` is empty;
* **ambiguous** — a merge lists several composed inputs, and "the parents" is a
  semantic question;
* **wrong** — a name that does not match what the artifacts say.

Downstream tools consume these fields. A plausible-looking but wrong parent is
worse than an empty one, because the fabrication looks well-formed and propagates
silently.

ProvenanceLens does not try to infer a model's true training history. It audits
an author's own declaration against the evidence in that author's repository.

## 🔄 What ProvenanceLens Does

```text
Hugging Face repository
        │  collect: text files only, weights excluded, size-capped
        ▼
Frozen evidence bundle ── repository + commit sha + SHA-256 per file
        │
        ├──► structured parsers (front matter, adapter, merge, training, config)
        │
        └──► model-card prose ──► optional local LLM ──► grounding validation
                    (rejected claims are discarded, never downgraded)
        │
        ▼
   EvidenceItems  — split into declared (the audit subject) and independent
        │           (evidence about it; declared metadata can never support itself)
        ▼
   identifier resolution ──► candidate aggregation ──► evidence fusion
        │                     (per parent + relation)     (reliability × independence,
        │                                                 capped per file)
        ▼
   conflict detection ──► decision policy
        │
        ▼
   KEEP / ADD / REPLACE / ABSTAIN  +  SuggestedPatch (a recommendation only)
```

Full detail, including which parts are deterministic and which are optional:
**[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

## 🛑 Why Abstention Matters

A false repair is worse than a missing one. When ProvenanceLens guesses a parent
wrong, it writes a claim that looks authoritative into a field other tools trust;
nothing in the metadata reveals that it was guessed. Abstention is cheap and
visible.

So the objective is deliberately asymmetric: **minimise false repairs first,
maximise coverage second.** `support_score` reports how strong the evidence is,
and it is explicitly *not* a probability — it is a capped sum of documented
per-artifact contributions. Consequently the project reports **no** ECE, Brier
score or reliability diagram, and no metric treats the score as a calibrated
confidence. See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) §12.

## 🔗 Supported Relations

| relation | meaning |
| --- | --- |
| `finetune` | weights fine-tuned from the parent |
| `adapter` | a LoRA/adapter trained on top of the parent |
| `merge` | weights produced by merging models |
| `quantized` | a numerically reduced derivative of the parent |

Anything else — distillation, transitive ancestry, dataset lineage — is out of
scope and untested.

## 🔍 Evidence Sources

| source | treated as | may assert a relation? |
| --- | --- | --- |
| `adapter_config.json` | tool-generated, `very_high` | `adapter` |
| merge configuration | tool-generated, `high` | `merge` |
| training configuration | tool-generated, `medium_high` | no — a field names a model, it does not assert a relationship |
| `config.json` / `generation_config.json` | author/tool written, `medium` | no |
| README prose (explicit phrases) | author written, `medium` | only from an explicit statement |
| README front matter `base_model` | **declared — the audit subject** | never, as evidence for itself |

Quoted mentions do not add up: contributions are capped per source file, so a
claim repeated in ten files is not ten independent confirmations.

## 🚀 Quick Start

Python 3.10+ and nothing else. No network, no model hub account, no Ollama, no GPU.

```bash
git clone https://github.com/Rusheel86/ProvenanceLens.git
cd ProvenanceLens
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python -m pytest -q                  # 563 passed, 7 skipped
python -m provenancelens.demo        # see the system work, offline
```

A 5–10 minute guided path, including every command in this README:
**[`docs/QUICKSTART.md`](docs/QUICKSTART.md)**.

## 🔎 Running an Audit

```bash
python -m provenancelens.cli audit peft-internal-testing/tiny-OPTForCausalLM-lora
python -m provenancelens.demo                    # six curated cases, labelled REAL/CONTROLLED
python -m provenancelens.demo --list
```

The audit reads a **frozen** snapshot: repository, pinned revision, declared
lineage, strongest evidence with file and key path, conflicts, support score,
decision, proposed patch, and — when abstaining — which condition stopped the
repair. Works for all 44 frozen repositories.

## 📊 Running LineageRepairBench

```bash
python -m provenancelens.evaluation validate      # self-check: 70 cases, 0 errors
python -m provenancelens.evaluation run           # the system + 6 baselines
python -m provenancelens.evaluation extraction    # prose-extraction quality
python -m provenancelens.cli benchmark validate   # same thing, shorter
```

## 🔬 Reproducing the Research (Phase G)

```bash
python -m provenancelens.evaluation.phase_g_cli run --output /tmp/study   # full study, ~2 s
python -m provenancelens.evaluation.phase_g_cli verify-canonical          # check committed results
python -m provenancelens.evaluation.phase_g_cli publish                   # regenerate results/phase_g
```

Nine ablations, a failure taxonomy, an evidence-contribution analysis, a
risk–coverage sweep, eleven tables and seven figures. Two runs produce
**byte-identical** artifacts. Details: [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## 📈 Current Evaluation

Measured on the 70-case LineageRepairBench (26 CONTROLLED + 44 REAL). Every
number below is generated from `results/phase_g/results.json`; denominators and
95% intervals are in [`results/phase_g/RESULTS.md`](results/phase_g/RESULTS.md).

| metric | combined | real track |
| --- | --- | --- |
| action accuracy | 62/70 = 0.886 | 36/44 = 0.818 |
| coverage (non-abstaining) | 21/70 = 0.300 | 10/44 = 0.227 |
| repair attempts | 12 | 6 |
| **false repairs** | **0/12** | **0/6** |
| unverifiable repairs | 0/12 | 0/6 |
| abstention rate | 49/70 = 0.700 | 34/44 = 0.773 |

* All **7** errors were **abstentions** — no incorrect affirmative repair and no
  incorrect `KEEP` was observed.
* Baselines: `config_only` / `prose_only` abstain everywhere (0.614);
  `rule_priority` repairs most often (23 attempts, coverage 0.929) and is the only
  baseline with a false repair.
* Ablations: removing tool-generated lineage fields takes repairs from 12 to 0;
  removing relation evidence collapses coverage to 0.014; flattening reliability
  tiers takes coverage to 0.029. **Model-card prose and framework config changed
  no decision at all** on this benchmark — a reported negative result.
* Weakest stratum: `quantized_awq`, **0/5** — for every AWQ derivative the
  relation is documented only in the model card, with no structured artifact
  stating it, so the system abstains.
* Optional local LLM (`llama3.2:3b`): 20 claims extracted, **0 accepted**, 0
  false repairs. The bottleneck was grounding — on one case the model produced
  the correct parent but quoted a span that did not contain it.

Stated conservatively: this documents how *this* system behaved on *these* 70
self-adjudicated cases. It is not a state-of-the-art claim, and **0/12 does not
mean false repairs are impossible.** Supported and unsupported claims are listed
separately in [`docs/CLAIMS.md`](docs/CLAIMS.md).

## 📁 Repository Structure

```text
src/provenancelens/
├── collectors/     Phase C  safe Hugging Face collection (the only networked component)
├── snapshots/      Phase C  immutable, hash-verified frozen evidence
├── parsers/        Phase C  deterministic extraction into EvidenceItems
├── resolution/     Phase D  conservative identifier resolution
├── reasoning/      Phase D  candidates, fusion, conflicts, decision policy
├── prose/          Phase E  chunking, validation, optional local-LLM extraction
├── llm_runtime.py  Phase E  local model availability (never downloads)
├── reporting/      Phase D  human-readable and JSON audit rendering
├── evaluation/     Phase F/G  LineageRepairBench, metrics, ablations, study
├── demo.py         Phase H  offline demonstration
└── cli.py          Phase H  audit / demo / benchmark / study

data/
├── snapshots/                  44 frozen repositories at pinned commits (~1.2 MB)
└── acquisition/real_selection.json   how the real track was sampled

results/phase_g/                the committed, regenerable research evidence
docs/                           architecture, methodology, limitations, claims, …
```

## 🧪 Testing

```bash
python -m pytest -q          # 563 passed, 7 skipped
```

Skips are opt-in live tests only: `PROVENANCELENS_LLM_TESTS=1` for a local Ollama
model, `PROVENANCELENS_NETWORK_TESTS=1` for live collection. The suite also
asserts the notebook hash, the benchmark composition, that documented numbers
match a fresh run, that the canonical results verify, and that no production
package changed during finalisation.

## 🧠 Optional Local LLM

Prose extraction has a deterministic path that needs nothing installed, and an
optional local-LLM path:

```bash
pip install -e ".[llm]"
ollama serve                       # you start the runtime
python -m provenancelens.evaluation.phase_g_cli llm-compare --model llama3.2:3b
```

ProvenanceLens **never downloads a model** and never starts a runtime for you; if
the model is absent, the command explains what to install and changes nothing.
The experiment is opt-in, is excluded from the deterministic study and from the
report digest, and its claims must pass grounding validation before becoming
evidence. No paid inference API is a dependency of anything.

## ⚠️ Limitations

The short version — the full treatment, with numbers, is
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md):

* 70 self-authored cases; 44 real repositories, one adjudicator, no inter-rater
  agreement. **38 of 70 truths are not knowable** by adjudication.
* Selection is stratified for evidence diversity, **not** a census of Hugging Face.
* CONTROLLED labels encode the policy, so 26/26 is a specification check, not
  evidence of generality.
* `support_score` is not a probability; probability calibration stays **deferred**.
* `quantized_awq` is a measured weakness (0/5) and was deliberately **not**
  "fixed" during finalisation, because tuning it on these cases would be fitting
  the benchmark.
* Prose and framework config changed no decision here; on this benchmark the
  system is an artifact-evidence system, not a documentation-reading one.
* The duplicate-inflation hypothesis was **not confirmed** and is reported as such.
* **Zero observed false repairs is not a guarantee** — 0/12 has a 95% interval
  reaching 0.242.
* One hosting ecosystem, four relations, one snapshot per repository.

Threats to validity are analysed in
[`docs/THREATS_TO_VALIDITY.md`](docs/THREATS_TO_VALIDITY.md).

## 🔁 Reproducibility

44 repositories frozen at pinned commits with SHA-256 per file; `load_snapshot`
verifies them before parsing. The study imports with the network stack absent,
contains no stochastic component, and produces byte-identical artifacts across
runs and across environments (a minimal install and a full install give the same
metrics). Canonical results live in `results/phase_g/` with a manifest of 30 file
digests and all 44 revisions, and `study verify-canonical` re-checks them.

Procedure, dependency groups and the offline acceptance checklist:
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## 📚 Research Documentation

| document | what it answers |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | how the system is built, component by component |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | definitions: lineage, evidence hierarchy, independence, policy, metrics, benchmark design |
| [`results/phase_g/RESULTS.md`](results/phase_g/RESULTS.md) | the measured results, generated from `results.json` |
| [`docs/CLAIMS.md`](docs/CLAIMS.md) | which claims are supported and which are not |
| [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) | measured limitations, including the negative results |
| [`docs/THREATS_TO_VALIDITY.md`](docs/THREATS_TO_VALIDITY.md) | internal, external, construct and conclusion threats |
| [`docs/QUICKSTART.md`](docs/QUICKSTART.md) | the 5–10 minute reviewer path |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | exact reproduction procedure |
| [`docs/PAPER_NOTES.md`](docs/PAPER_NOTES.md) | organised summary for a write-up, with conservative novelty wording |
| [`FINAL_PROJECT_STATUS.md`](FINAL_PROJECT_STATUS.md) | phases A–H, final state, readiness |
| [`CHANGELOG.md`](CHANGELOG.md) | milestone history |

---

# 🧱 Implementation reference

The rest of this document is the per-phase implementation record. It is kept
here for depth; a new reader can stop at the line above.

---

## 🏗️ Architecture

The system separates deterministic processing from optional LLM-based prose
extraction. Full component-by-component detail, with a Mermaid data-flow diagram
and the code-reading order, is in **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

The phases below describe how that architecture was built.

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

| Component                            | Phase | Status |
| ------------------------------------ | ----- | ------ |
| Structured package, schemas, parsers | B     | ✅ Working |
| Hugging Face collection (safety-first)| C     | ✅ Working |
| Frozen, hash-verified evidence       | C     | ✅ Working |
| Deterministic extraction + regression| C     | ✅ Working |
| Conservative entity resolution       | D     | ✅ Working |
| Evidence independence + fusion       | D     | ✅ Working |
| Structured conflict detection        | D     | ✅ Working |
| KEEP / ADD / REPLACE / ABSTAIN       | D     | ✅ Working |
| LangChain + optional local Ollama prose extraction | E | ✅ Working |
| Grounding / hallucination rejection  | E     | ✅ Working |
| LineageRepairBench (CONTROLLED + REAL)| F     | ✅ Working |
| Metrics, baselines, selective sweep, calibration guardrails | F | ✅ Working |
| Experimental study: ablations, analyses, tables, figures | G | ✅ Working |
| Documentation, demo, reproducibility, release readiness | H | ✅ Working |
| Legacy Phase-2 notebook              | A     | 🟡 Preserved unmodified, superseded |

The implementation uses frozen evidence bundles for reproducible testing, a
deterministic prose extractor that always runs, and an optional local LLM that can
only add validated evidence.

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
* The REAL track had **three** adjudicated cases at this point — far too few for statistically meaningful claims, which is why denominators are printed for every metric. Phase G expands it to 44 and adds Wilson intervals.
* Two of the three real cases are deliberately ambiguous/undetermined, so `parent_accuracy` there is dominated by cases where no answer was expected.
* **Superseded by Phase G:** the real track now has 44 adjudicated repositories (24 with genuinely unknowable truth), so the small-sample caveats above are measured per metric with Wilson intervals rather than asserted. See [Phase G](#-phase-g-experimental-study).
* Labels reflect what the stored evidence supports, not external truth about these models; the OpenHermes case would change if a training manifest were added to the snapshot.
* No calibration is reported (see below), and no baseline was tuned against the benchmark after labels were fixed.

### `support_score` is not a probability

The raw support score is a heuristic evidence strength (a capped sum of documented per-artifact contributions). Phase F therefore **does not** report ECE, Brier score, or reliability diagrams for it: doing so would present a non-probability as a calibrated one. Instead the evaluation package provides a `CalibratedScore` schema and mathematically standard ECE/Brier implementations that **refuse** uncalibrated inputs, plus a status object explaining which conditions are missing (a fitted mapping on a held-out split, ≥ 50 cases, a disjoint evaluation split). With 70 cases (Phase G) and no held-out split, probability calibration is deliberately **deferred** rather than faked.

### No research claims

ProvenanceLens makes no claim of state of the art, novelty, or empirical superiority: the benchmark is small, self-authored, and mostly synthetic. What it does show, on its own terms, is the intended trade-off — high repair safety at limited coverage — against simpler strategies that repair more often and less safely.

---

## 🔬 Phase G Experimental Study

Phase G turned the benchmark into a **study**: it expanded the real track from 3 to
**44 adjudicated repositories**, ran nine component ablations, and answered the
failure and evidence questions directly. Everything is offline, deterministic and
evaluation-only — the production engine is used unchanged, and a test asserts that
no production package has changed since the Phase F merge.

```bash
python -m provenancelens.evaluation phase-g run          # full study + all artifacts
python -m provenancelens.evaluation phase-g summary      # headline table only
python -m provenancelens.evaluation phase-g ablate       # ablation suite
python -m provenancelens.evaluation phase-g failures     # failure taxonomy
python -m provenancelens.evaluation phase-g verify       # re-run twice, compare digests
python -m provenancelens.evaluation phase-g publish      # regenerate results/phase_g
```

**Where the numbers live.** `artifacts/phase_g/` is git-ignored scratch output.
The **canonical, committed evidence** is `results/phase_g/`: `results.json` (the
machine-readable source of truth), `RESULTS.md` (rendered from it, never typed by
hand), eleven tables, seven figures and a manifest with 30 file digests plus all
44 pinned revisions. `python -m provenancelens.evaluation.phase_g_cli
verify-canonical` re-checks it, and the test suite fails if a documented number
disagrees with a fresh run. Two runs on one commit produce **byte-identical**
artifacts.

The tables in this README section are a convenience copy; when they and
`results/phase_g/RESULTS.md` ever disagree, the latter is correct.

### The real track: 44 adjudicated repositories

Selection is a frozen, documented plan (`evaluation/acquisition.py`): six strata with fixed quotas — PEFT adapters 8, mergekit merges 8, LoRA adapters 6, GGUF 6, AWQ 5, instruction finetunes 8 — candidates ordered by (downloads desc, id asc), exclusions recorded rather than silently dropped, and the three pre-Phase-G repositories left untouched. 41 new repositories were frozen; every one is kept, including the ambiguous and unknowable ones, because dropping them would be outcome-dependent sampling. `data/acquisition/real_selection.json` is the audit trail, and the analysis reads its strata from there rather than deriving strata from results.

Ground truth lives in `evaluation/adjudication/real_cases.yaml`, written for human review with a stated precedence:

1. **tool-generated lineage field** in a frozen artifact (the strongest evidence);
2. **card statement with a canonical repository id**, quoted in the record;
3. **declared metadata**, which is the *audit subject* and therefore never truth;
4. otherwise the truth is `ambiguous` or `unknown`, and no repair is expected.

Name or family resemblance was never used to infer lineage. The distribution is deliberately honest: 4 KEEP, 12 ADD, 28 no-repair-expectation; 18 knowable / 2 ambiguous / 24 unknown parent truth.

Two schema changes came out of adjudication rather than from the metrics:

* `MetadataState.INCOMPLETE` — the parent is declared but the relation is not (6 cases). Real and common; the Phase F vocabulary could not express it, and its validator now forbids labelling it `missing`.
* `ADD` is the safe repair for `missing` **and** `incomplete`, and validation rejects a label that contradicts what the repository actually declares.

### Headline results (n = 70: 26 controlled + 44 real)

| metric | all | real only | 95% CI (real) |
| --- | --- | --- | --- |
| action accuracy | 62/70 = 0.886 | 36/44 = 0.818 | [0.680, 0.905] |
| parent exact match | 19/32 = 0.594 | 9/18 = 0.500 | [0.290, 0.710] |
| relation accuracy | 21/31 = 0.677 | 10/18 = 0.556 | [0.337, 0.754] |
| coverage | 21/70 = 0.300 | 10/44 = 0.227 | [0.128, 0.370] |
| repair attempt rate | 12/70 = 0.171 | 6/44 = 0.136 | [0.064, 0.267] |
| **false repair rate** | **0/12 = 0.000** | **0/6 = 0.000** | [0.000, 0.390] |
| unverifiable repairs | 0/12 | 0/6 | — |
| abstention rate | 49/70 = 0.700 | 34/44 = 0.773 | [0.630, 0.872] |

Every headline number carries a Wilson 95% interval, because several denominators are small enough that a bare point estimate would be misleading. The false-repair denominator is exactly the Phase F definition (incorrect attempted repairs ÷ attempted repairs), and unverifiable attempts are reported separately rather than folded into either bucket.

**All 8 errors are abstentions.** Not one repair was attempted incorrectly, and not one non-abstention was wrong on the real track. Every mismatch is a case where the system declined to act and a repair would have been admissible — the price of the safety policy, paid in coverage.

### Where it fails

| category | cases |
| --- | --- |
| correct | 63 |
| unverifiable lineage (abstained; no independent evidence exists) | 6 |
| insufficient support (abstained; evidence below the policy threshold) | 1 |

Per-stratum action accuracy shows exactly where: `quantized_awq` is **0/5** — for every AWQ derivative the parent is declared, the card states the relation, and no structured artifact states it either, so the engine abstains. `peft_adapters` is 8/8 with 5 accepted repairs. Coverage is 0 for every real stratum except PEFT adapters.

### Ablations (evidence transforms, engine unmodified)

Each row runs the *same* engine on filtered, flattened, inflated or stripped evidence, so a delta is attributable to the ablated component alone.

| ablation | action accuracy | Δ | coverage | attempted repairs | false repairs |
| --- | --- | --- | --- | --- | --- |
| full | 0.886 | — | 0.300 | 12 | 0 |
| `no_prose` | 0.886 | +0.000 | 0.300 | 12 | 0 |
| `no_config` | 0.886 | +0.000 | 0.300 | 12 | 0 |
| `only_tool_configs` | 0.886 | +0.000 | 0.300 | 12 | 0 |
| `inflate_duplicates` | 0.857 | −0.029 | 0.329 | 14 | 0 |
| `highest_priority_only` | 0.857 | −0.029 | 0.271 | 10 | 0 |
| `only_highest_reliability` | 0.857 | −0.029 | 0.271 | 10 | 0 |
| `flatten_reliability` | 0.643 | −0.243 | 0.029 | 1 | 0 |
| `no_relation_evidence` | 0.629 | −0.257 | 0.014 | 0 | 0 |
| `no_tool_configs` | 0.614 | −0.271 | 0.000 | 0 | 0 |

Four findings, one of them negative and reported as measured:

1. **Tool-generated lineage is the only admissible repair trigger.** Removing adapter/merge/training configs stops *every* repair (12 → 0) and costs 27 points of accuracy.
2. **Relation evidence is the primary safety mechanism.** Strip relations and coverage collapses from 0.300 to 0.014: the engine almost never proposes a parent whose relation it cannot evidence.
3. **Reliability tiering carries the tool/prose distinction.** Flattening tiers collapses coverage to 0.029; precision and macro-F1 drop hardest (−0.35 F1).
4. **Prose and framework config changed nothing on this benchmark** (`no_prose`, `no_config`, `only_tool_configs` are all exactly neutral). Negative result, stated as such: on 70 cases no decision was changed by prose. The pre-registered hypothesis for `inflate_duplicates` (naive counting creates over-confident repairs) was **not** confirmed: duplication raised coverage slightly and still produced zero false repairs at this sample size.

### Evidence usage: frequency is not attribution

| source | cases with it | decisive items |
| --- | --- | --- |
| adapter_config | 18 | 18 |
| training_config | 8 | 5 |
| readme | 10 | 5 |
| merge_config | 4 | 9 |
| config | 5 | 4 |

32 of 70 cases have **no independent evidence at all** — only declared metadata, which the engine refuses to treat as evidence about itself. Presence and decisiveness are reported separately precisely because a source can be common but irrelevant, or rare but decisive.

### Risk–coverage

Relaxing the support threshold from 0.7 to 0.0 moves coverage 0.229 → 0.300 with selective accuracy 16/16 → 21/21 and still **zero** false repairs. The risk-coverage curve is deliberately boring: the system never buys accuracy with risk inside the observed range, and where it loses accuracy (the 8 abstentions) it loses it by declining to act.

### Optional local-LLM comparator (opt-in, never part of the default run)

`python -m provenancelens.evaluation phase-g llm-compare --model llama3.2:3b` runs one small experiment: the Phase E local extractor reads the model cards of the six cases where documented lineage exists but structured evidence does not. It refuses to run unless the model is **already installed locally** (it never pulls a model, never starts a runtime for you), claims pass the Phase E validator before becoming evidence, and the result is written to a separate artifact with its own caveat, never into the deterministic digest.

Measured with `llama3.2:3b` on those six cards: **20 claims reported, 0 accepted, 0 repairs attempted, 0 false repairs.** Rejection codes: `span_not_found` ×15, `malformed_output` ×15, `lineage_not_stated` ×4, `parent_not_in_source` ×1. The interesting part is *why* it failed: on `webAI-Official/TwIL-LM3` the model produced the correct parent `HuggingFaceTB/SmolLM3-3B` but quoted a span that did not contain it, and the validator rejected it. The bottleneck is grounding and format compliance, not knowledge. The safety property held — a 3B model's misreadings became zero evidence rather than wrong lineage, at the cost of zero recovered coverage.

### What Phase G does not claim

No superiority, novelty or state-of-the-art claim. The real track is self-adjudicated by the authors, so it documents the trade-off and the failure modes of *this* system on *these* repositories; it is not an independent evaluation, and 24 of 44 truths are genuinely unknowable rather than resolved. `support_score` remains a non-probability, so no ECE, Brier score or reliability diagram is reported anywhere in this section.

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

Phase G additionally covers: study determinism (byte-identical artifacts, report digest, CLI verify), offline execution with the network stack blocked, `INCOMPLETE` metadata-state validation rules, acquisition-stratum integrity, single-assignment failure taxonomy, evidence presence versus decisiveness, Wilson intervals, ablation deltas and verdicts, and manifest digests — plus the real guarantee that no production package changed since the Phase F merge.

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
├── ProvenanceLens_Phase2 (1).ipynb   # historical Phase 2 notebook (byte-identical, superseded)
├── README.md                         # this file
├── CURRENT_STATE.md                  # Phase A audit (historical)
├── FINAL_PROJECT_STATUS.md           # phases A–H, final state, readiness
├── CHANGELOG.md                      # milestone history
├── pyproject.toml
│
├── data/
│   ├── snapshots/                    # 44 frozen repositories at pinned commits (~1.2 MB)
│   └── acquisition/real_selection.json   # how the real track was sampled
│
├── docs/                             # architecture, methodology, limitations, claims, …
│
├── results/phase_g/                  # the committed, regenerable research evidence
│
├── src/provenancelens/
│   ├── collectors/                   # Hugging Face repository collection (network)
│   ├── snapshots/                    # snapshot store (save/load/verify)
│   ├── parsers/                      # deterministic extraction
│   ├── prose/                        # Phase E: prompt, chunking, validation, extractor
│   ├── llm_runtime.py                # local model config + read-only availability probe
│   ├── tools.py                      # read-only LangChain snapshot tools
│   ├── evaluation/                   # Phases F/G: LineageRepairBench, ablations, study, CLI
│   ├── resolution/                   # conservative model-id resolution
│   ├── reasoning/                    # Phase D candidates/fusion/conflicts/decision
│   │   └── legacy.py                 # Phase 2 engine (regression baseline, untouched)
│   ├── pipeline.py                   # snapshot -> evidence -> AuditDecision
│   ├── schemas/                      # evidence, lineage, collection, snapshot, audit models
│   ├── langchain_integration/        # Phase 2 workflow (guarded imports)
│   ├── reporting/                    # human-readable and JSON audit rendering
│   ├── demo.py                       # Phase H: offline demonstration
│   └── cli.py                        # Phase H: audit / demo / benchmark / study
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
* Evaluation (Phases F/G) is a self-authored benchmark: 26 controlled cases and 44 manually adjudicated real repositories. Ground truth was adjudicated by the same authors, so it documents the trade-off and the failure modes of *this* system on *these* repositories; it is not an independent evaluation and supports no superiority claims.
* Coverage is genuinely low on the real track (0.227) and every error is an abstention. Quantized derivatives whose relation is documented only in prose (`quantized_awq`, 0/5) are the clearest gap: recovering them safely needs evidence the repositories do not contain in structured form.
* Prose and framework-config evidence changed no decision on this benchmark (`no_prose` and `no_config` are exactly neutral at n=70). The system is currently an artifact-evidence system, not a documentation-reading one.
* A 3B local model reading the same model cards produced 20 claims and 0 accepted ones: the Phase E validator rejects ungrounded spans, so local LLM extraction is safe but contributes no coverage at that model size.

---

## 🔮 Status and Future Work

Phases A–H are complete; the evaluated system is frozen. See
[`FINAL_PROJECT_STATUS.md`](FINAL_PROJECT_STATUS.md) and
[`CHANGELOG.md`](CHANGELOG.md).

Delivered:

* ✅ Structured package with schemas, parsers and regression tests (Phase B)
* ✅ Safe Hugging Face collection with frozen, hash-verified, offline-reproducible
  snapshots (Phase C)
* ✅ Conservative resolution, evidence independence, fusion, conflict detection and
  KEEP/ADD/REPLACE/ABSTAIN (Phase D)
* ✅ Optional local open-weight prose extraction, fail-closed, never downloading a
  model (Phase E)
* ✅ LineageRepairBench with CONTROLLED and REAL tracks, baselines, selective
  evaluation and calibration guardrails (Phase F)
* ✅ Experimental study: 44 adjudicated real repositories, nine ablations,
  risk-coverage, failure and evidence analysis (Phase G)
* ✅ Documentation, offline demo, reproducible canonical results, release
  readiness (Phase H)

Next, driven by the measured limitations rather than by the score:

* ⬜ Structured quantization statements, to address the `quantized_awq` 0/5 gap
* ⬜ A larger real track with multiple adjudicators and reported agreement
* ⬜ Span-verified / constrained generation for grounded local extraction
* ⬜ A held-out split, so a probability mapping can finally be justified
* ⬜ Additional hosting ecosystems and relation classes (distillation, transitive)
* ⬜ Poor/failed retrieval cases at scale
* ⬜ End-to-end evidence citations surfaced in the audit report
* ⬜ Keep abstaining whenever a repair cannot be safely supported — the most
  important item on this list

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
