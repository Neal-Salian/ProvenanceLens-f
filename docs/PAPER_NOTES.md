# Paper notes

Not a paper — an organised summary of existing evidence, for whoever writes one.
Every number here is quoted from `results/phase_g/RESULTS.md` with its
denominator; nothing is extrapolated, and novelty wording is deliberately
conservative.

## Working title

**ProvenanceLens: Evidence-Calibrated Repair of Direct Model-Lineage Metadata in
Open Model Repositories**

## Problem

Open model repositories declare direct lineage — `base_model` and
`base_model_relation` — but the declaration is often missing (adapters and
quantized derivatives), incomplete (a parent with no relation), ambiguous (a
merge over several composed inputs) or incorrect. Downstream tooling consumes
these fields, so an absent or wrong value propagates silently.

The operation under study is narrow: given the evidence present in a repository,
**when should the declared lineage be changed, and when must the system decline?**
ProvenanceLens audits an author's own declaration; it does not attempt to infer a
model's true training history, and it never writes to a repository.

## Research questions

* **RQ1** How accurately can a lineage-repair system select among
  KEEP/ADD/REPLACE/ABSTAIN against adjudicated labels?
* **RQ2** What is the safety–coverage trade-off: how often does it attempt a
  repair, and how often is an attempt wrong?
* **RQ3** How does accuracy vary with the support threshold (selective
  prediction)?
* **RQ4–RQ8** Which evidence components matter: model-card prose, framework
  config, tool-generated lineage fields, per-file independence, reliability
  tiering, relation gating, fixed source hierarchies?
* **RQ9** Where does it fail, and is failure a wrong repair or a refusal?
* **RQ10** Does behaviour differ by evidence stratum (adapter, merge, quantized,
  instruction finetune)?
* **RQ11** Can a small local open-weight model recover the coverage the
  deterministic rules leave, without introducing unsafe repairs?

## Method

1. **Collect** provenance-relevant text files with weights and binaries excluded
   before download, and a hard byte cap.
2. **Freeze** each repository at a pinned commit with SHA-256 per file; loading
   verifies integrity offline.
3. **Parse deterministically** into `EvidenceItem`s split categorically into
   *declared* (the audit subject) and *independent* (evidence about it).
4. **Resolve** identifiers conservatively — never a hub query; a bare name does
   not become a public model id.
5. **Aggregate and fuse** by candidate parent and relation, weighting each item by
   reliability and an independence factor, with per-file contribution caps.
6. **Detect conflicts** as structured data.
7. **Decide** KEEP/ADD/REPLACE/ABSTAIN, requiring evidenced support *and* a
   provable relation for any repair; output an `AuditDecision` with a
   `SuggestedPatch` (a recommendation only).
8. **Optionally** read model-card prose with a local LLM, keeping only claims
   that pass grounding validation.

`support_score` is a capped sum of documented per-artifact contributions — a
heuristic strength, never a probability.

## LineageRepairBench

| track | n | role |
| --- | --- | --- |
| CONTROLLED | 26 | constructed edge cases; labels encode the policy, so a perfect score is a specification check |
| REAL | 44 | public repositories, each frozen at a pinned commit and hand-adjudicated from its artifacts |
| total | 70 | tracks never mixed |

**Real-track selection** is a frozen stratified plan (PEFT 8, mergekit 8, LoRA 6,
GGUF 6, AWQ 5, instruction finetunes 8) ordered by downloads then id, with
recorded exclusions and **no post-adjudication dropping** — all 41 newly
selected repositories were kept, including the unknowable ones.

**Adjudication precedence**: tool-generated lineage field > card statement with
a canonical repository id > declared metadata (never truth) > ambiguous/unknown.
Name resemblance was never used. Real-track distribution: 4 KEEP, 12 ADD, 28
no-repair-expectation; 18 knowable / 2 ambiguous / 24 unknowable parent truth.
Across all 70 cases, 38 truths are not knowable.

**Baselines** (six, deterministic, untuned): `declared_metadata`, `config_only`,
`prose_only`, `majority_count`, `rule_priority`, `always_keep`.

**Ablations**: nine evidence transformations run through the *unmodified* engine,
each with a pre-registered hypothesis in code.

## Experimental setup

* Offline, deterministic, no LLM in the main study; frozen snapshots only.
* Metrics: action accuracy, parent exact match (set comparison, KNOWN truth
  only), relation accuracy, coverage, abstention, repair-attempt rate, **False
  Repair Rate = incorrect attempted repairs / attempted repairs**, unverifiable
  repairs reported separately, macro-F1, and a selective threshold sweep.
* Wilson 95% intervals on headline proportions (no SciPy dependency).
* No significance testing: small paired samples, so ablation verdicts are
  descriptive.

## Main findings

1. **Action accuracy 62/70 = 0.886** (REAL 36/44 = 0.818; CONTROLLED 26/26).
2. **Repair safety: 12 attempts, 0 observed false repairs (0/12; REAL 0/6)**,
   0 unverifiable.
3. **All 7 errors were abstentions** — no wrong affirmative repair, no wrong
   `KEEP`.
4. **Coverage is the price: 21/70 = 0.300** (REAL 10/44 = 0.227), abstention
   49/70 = 0.700.
5. **Threshold relaxation did not change accuracy** in the observed range
   (21/21 at coverage 0.300; 0 false repairs at all 21 sweep points).
6. **`quantized_awq` scored 0/5** — the clearest measured weakness.

## Ablations

| ablation | Δ action accuracy | effect |
| --- | --- | --- |
| `no_tool_configs` | −0.271 | repairs 12 → 0; structured tool-generated lineage is the only admissible repair trigger here |
| `no_relation_evidence` | −0.257 | coverage 0.300 → 0.014; relation gating is the main safety constraint |
| `flatten_reliability` | −0.243 | coverage → 0.029; tiering separates tool evidence from prose |
| `no_prose` | 0.000 | prose changed no decision |
| `no_config` | 0.000 | framework config changed no decision |
| `only_tool_configs` | 0.000 | tool configs alone were sufficient on this benchmark |
| `inflate_duplicates` | −0.029 | coverage 0.300 → 0.329, still 0 false repairs; **hypothesis not confirmed** |
| `highest_priority_only` | −0.029 | coverage → 0.271 |
| `only_highest_reliability` | −0.029 | coverage → 0.271 |

The two "no effect" rows and the unconfirmed duplicate hypothesis are reported as
measured. They are the most informative rows in the table: on this benchmark the
system is an artifact-evidence system, not a documentation-reading one.

## LLM experiment

`llama3.2:3b` on the six frozen cards where lineage is documented but no
structured artifact states it: **20 claims reported, 0 accepted, 0 repair
attempts, 0 false repairs**; rejections 15 `span_not_found`, 15 `malformed_output`,
4 `lineage_not_stated`, 1 `parent_not_in_source`. On `webAI-Official/TwIL-LM3` the
model produced the correct parent and was rejected for quoting a span that did not
contain it — the bottleneck is grounding and output fidelity, not knowledge. The
fail-closed property held: misreadings became zero evidence, not wrong lineage.

## Limitations

Small, self-authored benchmark (70 cases, one adjudicator, one ecosystem);
`support_score` is not a probability and calibration stays deferred; `quantized_awq`
0/5; two evidence classes changed no decision; the local LLM contributed nothing
measurable at 3B; **0/12 false repairs is an observed count, not a guarantee**
(95% interval reaching 0.242). Full list: `docs/LIMITATIONS.md`.

## Threats to validity

Adjudication error is the largest internal threat (MergeKit input semantics and
"direct parent" judgement are genuine ambiguities, with no inter-rater check).
External: stratified rather than representative selection; Hugging Face only;
four relations; single snapshot per repository. Construct: action accuracy as a
proxy for usefulness; the score is not a probability; 38 unknowable truths mean
the real track measures *refusal quality* more than repair quality. Conclusion:
12 attempts total; several strata have n ≤ 6. Full analysis:
`docs/THREATS_TO_VALIDITY.md`.

## Future work

Emerged from the measured limitations, in priority order:

1. **Quantized/AWQ lineage evidence** (closes the 0/5 stratum): require an
   explicit, structured quantization statement rather than inferring from
   packaging.
2. **Larger, independently adjudicated real track** with ≥ 2 adjudicators and a
   reported agreement statistic.
3. **Stronger grounded local extraction**: constrained decoding or span-verified
   generation to fix the grounding failures, then re-run the same comparator.
4. **Valid held-out calibration** (≥ 50 cases) so a probability mapping can be
   fitted and evaluated on a disjoint split.
5. **Additional hosting ecosystems** and other relation classes (distillation,
   trans-architecture merges).
6. **Multi-step lineage** as a first-class object, so transitive cases are
   representable instead of out of scope.
7. **Artifact/fingerprint verification** where repository hashes can corroborate
   a declared parent.
8. **Post-hoc repair tracking** — whether recommended patches are later accepted,
   the only way to measure usefulness rather than agreement.

## Potential contributions

Framed as project contributions, not novelty claims:

* A working, conservative repair policy for direct repository lineage under
  heterogeneous, partly undocumented evidence, with the declared/independent
  split enforced categorically.
* An explicit four-way policy (KEEP/ADD/REPLACE/**ABSTAIN**) that makes refusal
  a first-class outcome and reports it as a measured cost.
* Evidence independence and reliability tiering implemented as auditable
  mechanisms, with ablations that quantify their contribution — including
  reporting null and disconfirmed hypotheses.
* LineageRepairBench: a frozen, self-validating, offline benchmark with
  CONTROLLED and REAL tracks kept separate, human-readable adjudication with
  stated precedence, baselines, selective evaluation and a versioned False
  Repair Rate.
* A fully offline, byte-reproducible research pipeline whose committed results
  are regenerated from code and verified by tests, so documentation cannot
  silently drift from measurements.

Explicitly **not** claimed: state of the art, first-ever provenance system,
universal superiority over other lineage tools, or any safety guarantee.
