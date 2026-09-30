# Methodology

Definitions first, so every number in `results/phase_g/` can be checked against
the rule that produced it.

## 1. Research problem

Open model repositories declare *direct* lineage metadata — `base_model` and
`base_model_relation` — in whatever form their author chose. That declaration is
frequently **missing** (adapters and quantized derivatives often omit it),
**incomplete** (a parent without a relation), **ambiguous** (a merge that lists
several composed inputs) or **incorrect**. Downstream tools consume it, so a
wrong or absent value propagates.

The question studied here is narrow and concrete:

> Given the evidence available in a repository, when is a change to the declared
> direct lineage metadata sufficiently supported to recommend, and when must the
> system decline?

This is deliberately *not* "infer provenance". ProvenanceLens audits an author's
own declaration; it never claims to know a model's real training history.

## 2. What "direct lineage" means here

**Direct** lineage is the single-step relation from a repository to the model it
was derived from. ProvenanceLens handles exactly four canonical relations:

| relation | meaning | typically evidenced by |
| --- | --- | --- |
| `finetune` | weights were fine-tuned from the parent | training/config metadata |
| `adapter` | a LoRA/adapter trained on top of the parent | `adapter_config.json` |
| `merge` | weights produced by merging models | `mergekit_config.yml`, merge configs |
| `quantized` | a numerically reduced derivative of the parent | an explicit quantization statement |

Transitive ancestry (grandparents), training-data lineage, dataset lineage and
"derived from" prose of any other kind are **out of scope**. A relation is never
inferred from a name resemblance, a shared organization, a matching architecture
or the presence of a weight file.

## 3. Evidence hierarchy

Evidence is ordered by *how it was produced*, not by how confident it sounds.

| tier | source | why it sits there |
| --- | --- | --- |
| `very_high` | `adapter_config.json` | written by the tool that created the artifact; a machine-checkable field |
| `high` | merge configuration | same argument: tool-generated, and a parseable input list |
| `medium_high` | training configuration | tool-generated, but the field names a model without asserting a relationship |
| `medium` | `config.json`, README prose with an explicit phrase | author-written, and prose must be matched by an explicit rule |
| `not_applicable` | declared metadata (`base_model` front matter) | the audit *subject*; it can never support a change to itself |

Two rules follow and are enforced in code:

* **Declared metadata is never evidence for itself.** A repository that declares
  `base_model: X` never gets support for "the parent is X" from that same field.
* **Independent evidence never inherits the declared relation.** If the card says
  `base_model: X` and an unrelated file mentions X, the relation is still
  unknown.

## 4. Independence assumptions

Support is not a raw count of mentions. Each independent item contributes

```
weight = item_reliability × independence_factor
```

and contributions are **capped per source file**. A claim repeated in ten files
is not ten independent confirmations; a single file cannot manufacture support
by repeating itself. This is what the `inflate_duplicates` ablation probes by
pretending every record came from its own file.

## 5. Decision policy

```
declared lineage  +  fused evidence  +  conflicts  ->  decision
```

* **KEEP** — the declaration is supported (or nothing contradicts it).
* **ADD** — nothing direct is declared, and evidence supports a specific parent
  *and* a provable relation.
* **REPLACE** — the declaration is contradicted by decisive evidence.
* **ABSTAIN** — everything else: no independent evidence, unresolved conflict,
  unprovable relation, ambiguous multi-parent set, or support below threshold.

A repair is recommended only when the *relation* is evidenced, not merely the
parent. The `no_relation_evidence` ablation shows what that costs: coverage
falls from 0.300 to 0.014.

## 6. Why false repairs matter, and why abstention is allowed

A false repair is worse than a missing one. A tool that silently rewrites
`base_model` to a plausible-looking but wrong model propagates a fabricated
claim into every downstream consumer, and the fabrication is *invisible* — the
metadata looks well-formed. Abstention, by contrast, is visible and cheap: the
user is told nothing could be established.

So the objective is asymmetric: **minimise false repairs first, maximise coverage
second**. Every metric in this project is reported so that a change in one cannot
hide a change in the other, and the headline repair-safety number is always shown
with its numerator and denominator.

## 7. Benchmark design — LineageRepairBench

Two tracks that are never mixed, because they answer different questions.

### CONTROLLED (26 cases)

Constructed cases that encode the documented policy: a correct finetune, an
adapter with missing metadata, a wrong parent, competing candidates, an
ambiguous identifier, a tool failure, weak evidence, duplicated single-source
evidence, multi-source noise, and so on.

Their labels *are* the specification, so a perfect score means "the
implementation still matches its specification" and **nothing about generality**.
They are a regression guard, not evidence.

### REAL (44 cases)

Public Hugging Face repositories, each frozen at a pinned commit, each
adjudicated by hand from its artifacts. These are the only cases that say
anything about behaviour on real repositories — and they are still
self-adjudicated by the project authors, which is a real limitation (see
`THREATS_TO_VALIDITY.md`).

### Selecting the real repositories

Selection is a frozen plan, not a search for interesting examples
(`evaluation/acquisition.py`, recorded in `data/acquisition/real_selection.json`):

* six strata with fixed quotas — PEFT adapters 8, mergekit merges 8, LoRA
  adapters 6, GGUF 6, AWQ 5, instruction finetunes 8;
* candidates ordered by `(downloads desc, id asc)`, so the plan is reproducible;
* exclusions are recorded with reasons, never silent (gated, private, no
  provenance-relevant artifact, above the size budget, already in the benchmark);
* **all 41 selected repositories were kept**, including the ambiguous and
  unknowable ones. Dropping a case after seeing its adjudication would make the
  benchmark a selection on the outcome.

The three repositories frozen before Phase G are retained and labelled
`pre_phase_g`.

### Adjudication

Truth is decided by a stated precedence, written per case in
`evaluation/adjudication/real_cases.yaml` with the evidence quoted:

1. a **tool-generated lineage field** in a frozen artifact (strongest);
2. a **card statement containing a canonical repository id**;
3. **declared metadata** — the audit subject, therefore never truth;
4. otherwise the truth is `ambiguous` or `unknown`, and no repair is expected.

Name or family resemblance was never used. The declared state is recorded as
`valid`, `missing`, `incomplete` (parent declared, relation not), `incorrect` or
`undetermined`, and validation rejects any label that contradicts what the
repository actually declares.

Distribution of the 44 real cases: 4 KEEP, 12 ADD, 28 no-repair-expectation;
18 knowable / 2 ambiguous / 24 unknowable parent truth. Across all 70 cases,
**38 have a parent truth that is not knowable** — deliberately, because "we
cannot know" is the honest answer for most real repositories.

## 8. Baselines

Six deterministic comparators, each a faithful stand-in for a plausible
strategy, each evaluated through the same runner so the numbers are comparable:

| baseline | what it represents |
| --- | --- |
| `declared_metadata` | trust the repository, never infer |
| `config_only` | the engine restricted to framework config evidence |
| `prose_only` | the engine restricted to prose evidence |
| `majority_count` | take the candidate with the most evidence records; abstain on ties |
| `rule_priority` | a fixed source hierarchy, no conflict or fusion logic |
| `always_keep` | trivial reference |

No baseline was tuned after the labels were fixed.

## 9. Ablations

Nine **evidence transformations** applied to the *unmodified* engine, each with
its question and its pre-registered hypothesis in code
(`evaluation/ablations.py`):

| ablation | question |
| --- | --- |
| `no_prose` / `no_config` / `no_tool_configs` | how much does each evidence class contribute? |
| `only_tool_configs` | are tool configs sufficient alone? |
| `inflate_duplicates` | what does per-file deduplication buy? |
| `flatten_reliability` | does tiered reliability matter versus equal tiers? |
| `no_relation_evidence` | how much does relation evidence matter? |
| `highest_priority_only` | is a fixed source hierarchy sufficient? |
| `only_highest_reliability` | does the single best item decide? |

Verdicts are **descriptive**, not significance tests: these are small paired
samples, and the report says so. Hypotheses that the measurement contradicted
were kept and reported (`inflate_duplicates`), not quietly revised.

## 10. Selective prediction

The support threshold is swept to trace the risk–coverage trade-off: at each
threshold, how many cases are accepted, how accurate are the accepted ones, and
how many false repairs were attempted. Reported per operating point, with a
Wilson interval on selective accuracy.

## 11. False Repair Rate — exact definition

> **False Repair Rate = incorrect attempted repairs / total attempted repairs.**

* An *attempted repair* is a decision of `ADD` or `REPLACE`.
* An attempt is *incorrect* when its proposed lineage contradicts **adjudicated
  truth that is KNOWN**.
* An attempt against truth that is **not knowable** is counted as
  **unverifiable** — neither credited nor blamed, and never folded into either
  bucket.
* Abstention is never counted as a correct repair.

This definition is unchanged from Phase F; the denominator is attempted
repairs, *not* verified cases. Every reported FRR carries its numerator and
denominator, e.g. `0/12` combined and `0/6` on the real track.

Related definitions:

* **Coverage** = non-abstaining decisions / scored cases.
* **Action accuracy** = decisions matching the adjudicated expected action /
  scored cases. Cases whose expected action is ambiguous accept any action in
  their `acceptable_actions` set and are still scored, and are reported
  separately.
* **Parent exact match** / **relation accuracy** are scored only on cases with
  KNOWN truth; multi-parent truth is compared as a set.

## 12. Calibration decision

`support_score` is a heuristic evidence strength: a capped sum of documented
per-artifact contributions. It has no frequency interpretation, so **ECE, Brier
score and reliability diagrams are not reported anywhere in this project** —
doing so would present a non-probability as a calibrated one. The code provides
standard implementations that *refuse* uncalibrated inputs, plus a status object
naming what is missing: a mapping fitted on a held-out calibration split of at
least 50 cases, and a disjoint evaluation split. Calibration remains
**deferred**, and `pyproject.toml`/docs never describe the score as a percentage.

## 13. Local LLM evaluation

The optional experiment asks a narrow question: can a small local open-weight
model recover the coverage the deterministic rules leave on the table, and does
it do so without introducing an unsafe repair?

Design constraints, all enforced:

* **opt-in only** — never in the default study, the test suite or the report
  digest;
* **local only, no downloads** — the run refuses unless the model is already
  installed, and never starts a runtime for the operator;
* **claims must pass the Phase E validator** before becoming evidence;
* **targets are chosen from ground truth and declared metadata**, never from the
  system's own decisions;
* **results live in a separate artifact** with its own caveat, because local
  model output is environment-dependent.

Measured with `llama3.2:3b` on the six frozen cards where lineage is documented
but no structured artifact states it: **20 claims reported, 0 accepted, 0 repair
attempts, 0 false repairs**; rejections were 15 `span_not_found`, 15
`malformed_output`, 4 `lineage_not_stated`, 1 `parent_not_in_source`. On
`webAI-Official/TwIL-LM3` the model produced the *correct* parent but quoted a
span that did not contain it, so validation rejected it. The bottleneck at that
model size is grounding and output fidelity, not knowledge — a negative result
for this model size and these prompts, not evidence that local models are
useless.

## 14. Reproducibility methodology

* **Frozen everything.** 44 repositories at pinned commits with SHA-256 per
  file; `load_snapshot` verifies them before use.
* **Deterministic by construction.** No sampling, no shuffling, no model
  inference, no clock in any metric value. Identical inputs give identical
  outputs, verified by running the study twice and comparing bytes.
* **One writer.** The committed `results/phase_g/` set is produced by the same
  renderers as the scratch `artifacts/` output, so they cannot diverge.
* **Machine-readable first.** Every documented number is rendered from
  `results/phase_g/results.json`; a test fails if a document disagrees with a
  fresh run.
* **Honest manifests.** The canonical manifest excludes timings, the evaluating
  commit and machine details *because* those would break byte-determinism; they
  live in `artifacts/phase_g/manifest.json` instead.
* **Integrity is testable.** `study verify-canonical` re-hashes every committed
  artifact; the test suite asserts the notebook hash, the snapshot revisions and
  that no production package changed during finalization.

## 15. What this methodology cannot tell you

Read `docs/THREATS_TO_VALIDITY.md` before quoting any number. In short: 70
self-authored cases from one ecosystem, one adjudicator, truth that is unknowable
for more than half of them, and a zero false-repair count that bounds nothing
beyond the cases that were tried.
