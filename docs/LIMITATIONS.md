# Limitations

Measured limitations, in the order a reader is most likely to hit them. Nothing
here is hedged: these are the reasons the numbers in `results/phase_g/` should not
be read as more than they are.

## 1. The benchmark is small, and 70 cases is not a sample of anything

70 cases: 26 constructed (CONTROLLED) and 44 adjudicated (REAL). Several metrics
rest on fewer than 20 cases — parent accuracy is scored on 32, relation accuracy
on 31, false repairs on 12 attempts (6 on the real track). A single case moves
action accuracy by 1.4 points, and the Wilson intervals in the results document
are wide for exactly this reason. **Read the intervals, not the point estimates.**

## 2. The real track is not a census of Hugging Face

44 repositories were selected by a stratified plan (six strata, fixed quotas,
ordering by downloads then id) to cover *evidence shapes* — not to be
representative. Nothing here supports "this is how common such problems are on
Hugging Face", and the plan deliberately over-samples rare shapes (AWQ, merge
configs, LoRA) relative to their real frequency.

## 3. The controlled cases are constructed edge cases

Their labels encode the documented policy, so 26/26 is a **specification check**:
the implementation still matches its specification. It says nothing about
generality, and no baseline comparison on the controlled track should be quoted as
evidence about real repositories.

## 4. Ground truth was adjudicated by the project authors

The REAL labels were produced by the same people who built the system, by
adjudicating frozen artifacts. There was one adjudicator and no inter-rater
agreement measurement, so systematic misreading of, say, MergeKit input semantics
would not be caught by the process itself. Where a case could not be resolved it
was labelled `ambiguous` or `unknown` rather than guessed — 38 of 70 cases have a
parent truth that is **not knowable** — but "unknowable" is itself a judgement.

## 5. `support_score` is not a calibrated probability

It is a capped sum of documented per-artifact contributions. It has no frequency
interpretation, so ECE, Brier score and reliability diagrams are not reported
anywhere in this project. Threshold sweeps over it are useful for exploring the
trade-off and are **not** claims about confidence.

## 6. Calibration remains deferred

A probability mapping would need to be fitted on a held-out split of at least 50
cases and evaluated on a disjoint split. There is no such split, and inventing
one from these 70 cases would produce a number that looks like a probability and
is not. The code enforces this: the calibration module refuses uncalibrated
inputs and reports which conditions are missing.

## 7. Quantized and AWQ lineage is a measured weakness

The `quantized_awq` stratum scored **0/5** on action accuracy. For every AWQ
derivative in the benchmark the parent is declared and the relation is documented
only in the model card, with no structured artifact stating it — so the engine
abstains, and abstention is scored as a miss against the adjudicated `ADD`.

This is the clearest single gap in the system, and it was **not** "fixed" during
finalisation: tuning it against these five cases would be fitting the benchmark.
Recovering it safely needs evidence the repositories do not currently contain in
structured form, or a genuinely grounded extraction path (see
`PAPER_NOTES.md` future work).

## 8. Two evidence classes changed no decision in the evaluated set

`no_prose` and `no_config` were **exactly neutral** on all 70 cases: removing
model-card prose, or removing framework config, did not change a single
decision. Prose items do appear in the evidence-contribution table as *decisive
candidates* (5 items), but none of them was load-bearing on its own.

Stated plainly: **on this benchmark ProvenanceLens is an artifact-evidence
system, not a documentation-reading one.** A benchmark with more
prose-documented lineage could show a different picture, and that is untested.

## 9. The duplicate-inflation hypothesis was not confirmed

`inflate_duplicates` was predicted to produce over-confident repairs by counting
repeated mentions naively. Measured effect: coverage rose slightly (0.300 →
0.329) and false repairs stayed at 0. The hypothesis was **not supported** at
this sample size. It is retained in the ablation table and the pre-registered
hypothesis list rather than being quietly dropped.

## 10. Local LLM extraction contributed nothing measurable

With `llama3.2:3b`: 20 claims reported, **0 accepted**, 0 repair attempts, 0
false repairs. The rejections were grounding failures (paraphrased spans that do
not occur in the text) and malformed output. On one case the model produced the
correct parent and was still rejected because its quoted span did not contain it.

This is a negative result for **this model at these prompts**, and the safety
property held: a small model's misreadings became zero evidence rather than wrong
lineage. It is not evidence that local models cannot help, and it is not evidence
that they can.

## 11. Zero observed false repairs does **not** mean false repairs are impossible

This is the most important caveat in the project. 0/12 is an upper bound on the
observed rate in 12 attempts, with a 95% Wilson interval reaching
[0.000, 0.242]. It is not a safety guarantee, and it does not transfer to
repositories, adapters or relation types that were never tried. The system is
*designed* to be conservative, which lowers the rate; it does not make wrong
repairs impossible.

## 12. Repository metadata evolves after the snapshot

Every case is frozen at one commit. Real repositories are re-tagged, corrected or
deleted; a finding about a snapshot says nothing about the repository today. The
pinned revisions in `results/phase_g/manifest.json` are the only valid reference
point, and re-running against live repositories would produce different (possibly
conflicting) labels.

## 13. Scope limits

* One hosting ecosystem (Hugging Face) and one collection strategy.
* Four relations. Anything else — trans-architecture derivatives, distillation
  chains, dataset lineage — is out of scope and untested.
* Entity resolution is offline and conservative, so bare model names abstain.
* Snapshot timing is a single pass; no repository is re-collected over time, so
  no claim about metadata *drift* is supported.

## 14. Reporting defects found during finalisation

For completeness, three presentation-level problems in the Phase G report were
fixed in Phase H and the artifacts regenerated: an evidence-usage definition
sentence that asserted a property the data contradicted, unrounded interval
bounds in the stratum table, and two figures whose labels or interpolation band
implied more than was measured. **No metric, table value or label changed** — the
report digest moved only because a definition string was corrected. Every metric
table is byte-identical to the Phase G baseline.
