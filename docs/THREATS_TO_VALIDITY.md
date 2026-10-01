# Threats to validity

The standard four kinds, applied concretely to this project, with what would
change the conclusion. A reader who wants one section should read this one.

## Internal validity — could the study's own machinery produce the result?

### I.1 Adjudication error (the largest internal threat)

The 44 REAL labels were adjudicated by the project authors from frozen
artifacts, with one adjudicator and no inter-rater agreement. Two specific
failure modes are plausible and would not be detected by the current process:

* **MergeKit input semantics.** Whether a merge's "parents" are the composed
  `base+lora` entries or the plain repositories is a genuine semantic question.
  `mergekit-community/Qwen3-1.5B-Instruct` and `ohnoes_now_nsfw` are labelled
  ambiguous for exactly this reason, and `qylu4156/strongreject-15k-v1` depends
  on reading a specific README statement.
* **"Direct parent" judgement.** For a derivative of a derivative, whether the
  direct parent is the base or the intermediate is a judgement call; the
  precedence rule picks the tool-generated field, which is a convention, not a
  fact.

Effect: parent and relation accuracy on the real track (9/18 and 10/18) could
move in either direction under a different adjudicator. Action accuracy is more
robust, because most errors are abstentions that any reasonable adjudicator
would also expect to abstain on.

*Mitigation needed:* multiple independent adjudicators, an adjudication protocol
fixed before labelling, and a reported agreement statistic.

### I.2 Implementation defects

Paraphrased in the sense that matters here: the reasoning code is small and
covered by 563 tests, but no test can prove the *policy thresholds* are right —
only that they are applied consistently. `support >= 0.55` and the relation gate
were chosen during Phase D from the controlled cases and never revisited. That
choice is now frozen, which is correct for reproducibility and wrong for
optimality.

*Mitigation needed:* a held-out split for threshold selection, which does not
currently exist.

### I.3 Evidence-parser assumptions

The parsers assume: front matter is the declaration; a field that names a model
without asserting a relationship implies no relation; a quantization relation
requires an explicit statement. Each is defensible and each is an assumption.
The most consequential is the second: a training config that says
`base_model: X` will not yield `finetune`, so those cases are *expected* to
abstain. This shapes the abstention count more than any policy threshold.

### I.4 Ablation construction

Ablations transform evidence, not code, which keeps the engine identical and the
deltas attributable — but it means an ablation can only remove what the
extractor happened to produce. `no_prose` removes *extracted* prose claims; if
the extractor missed a claim, the ablation cannot show it. The exactly-neutral
`no_prose` result is therefore partly a statement about the extractor, not only
about fusion.

### I.5 Reporting and transcription

Mitigated structurally: every documented number is rendered from
`results/phase_g/results.json`, and a test fails when a document disagrees with a
fresh run. The three presentation defects found in finalisation are documented in
`LIMITATIONS.md` §14; none changed a metric.

## External validity — do the findings generalise?

### E.1 Selected repositories, not a sample

44 repositories from a six-stratum plan designed for evidence diversity. The plan
over-samples rare shapes relative to their real frequency. No prevalence claim,
no "most repositories do X" claim is supported.

### E.2 One ecosystem

Hugging Face only, via one collector with one file-selection policy. Other
hosts (ModelScope, GitHub model cards, local registries) and their metadata
conventions are untested; the declared-vs-independent split may not even be
expressible in another ecosystem's metadata format.

### E.3 Limited relation classes

Four relations. Distillation, trans-architecture merges, synthetic-data lineages
and "trained on the output of" are out of scope by design; a repository whose
true relation is `distill` is outside the system and would be scored against a
label the system cannot represent.

### E.4 Snapshot timing

Each repository is observed once, at one commit. Metadata drift over time is
neither measured nor claimed.

### E.5 Downstream usefulness unmeasured

Action accuracy measures agreement with adjudicated labels, not whether a repair
would be *useful* to a downstream consumer. The controlled cases in particular
encode the policy, so 26/26 is a self-consistency result.

## Construct validity — are we measuring the right things?

### C.1 Action accuracy is a proxy

The label is "which of four actions should be taken". A reader may reasonably
prefer a different loss — for instance, treating an unnecessary `KEEP` as worse
than an abstention, or weighting a missed `ADD` more heavily than a missed
`KEEP`. The benchmark reports the confusion matrix so alternative readings are
possible, but the headline uses one weighting.

### C.2 `support_score` is not a probability

Documented at length elsewhere; repeated here because it is a construct risk.
The score is **not** a confidence percentage, and any reader who treats it as
one will misread the risk–coverage curve. The report, the figures and the CLI all label it
explicitly, and the calibration module refuses to produce ECE/Brier for it.

### C.3 Labels simplify real lineage complexity

Real lineage is multi-step, contested and sometimes political. A binary
"parent" label flattens that. `ambiguous` and `unknown` are honest labels, not
failures to label — but they mean the benchmark measures *refusal quality* more
than *repair quality* on the real track, because 38 of 70 truths are not knowable.

### C.4 Baselines are stand-ins

`majority_count` and `rule_priority` are plausible strategies implemented by
this project. They are not tuned, but a stronger baseline (a trained classifier
over the same evidence, or a human expert panel) might close the gap, which
would weaken the "conflict-aware fusion matters" reading of the ablations.

## Conclusion validity — are the conclusions warranted?

### N.1 Small samples

Repair attempts total **12** (6 on the real track). Every claim about repair
safety rests on that. The 95% Wilson interval on 0/12 extends to 0.242, so the
data are consistent with a true false-repair rate of up to roughly one in four
attempts. "Zero false repairs were observed" is a statement about these attempts;
"the false-repair rate is low" is a much weaker statement about the world.

### N.2 Some categories have very small N

`quantized_awq` n=5, `lora_adapters` n=6, `quantized_gguf` n=6, `pre_phase_g`
n=3. The per-stratum table is a map of where to look, not a set of estimates;
several strata have intervals wide enough to include 1.0.

### N.3 Zero observed false repairs is not zero population risk

Stated as its own item because it is the most quotable number in the project and
the easiest to misuse. No statistical argument turns 0/12 into a guarantee, and
the system's conservatism is a *design* choice that reduces the rate without
eliminating the failure mode.

### N.4 No significance testing

Ablation verdicts are descriptive thresholds on paired small samples, not tests.
`highest_priority_only` at −0.029 is two cases; treating it as evidence that
source hierarchies are worse than conflict-aware fusion would be over-reading.

### N.5 Single system, single version

One implementation, one prompt version, one parser set. Nothing here separates
the *idea* from this instantiation of it.

## What would most improve the evidence

Ordered by how much each would change the confidence in the conclusions:

1. **A larger, independently adjudicated real track** with two or more
   adjudicators and a reported agreement statistic (attacks I.1, N.1, E.1).
2. **A held-out split** for any threshold or mapping selection, which would
   finally justify a calibrated score (attacks I.2, C.2).
3. **Repair attempts in the hundreds**, ideally from real repositories where the
   truth is corroborated by an artifact (attacks N.1, N.3).
4. **A second hosting ecosystem** (attacks E.2).
5. **Multi-step lineage as a first-class object**, so `distill` and transitive
   cases are representable rather than out of scope (attacks E.3, C.3).
