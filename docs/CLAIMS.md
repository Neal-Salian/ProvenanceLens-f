# Research claims: what the evidence supports

Every claim below is scoped to *this* system on *this* benchmark. Claims that a
stronger reading would license are listed next to them and explicitly not made.
If you are writing a report from this project, use the left column and the
denominators, and drop the right column.

## Supported

**S1 — Repair safety on the evaluated benchmark.**
On the 70-case LineageRepairBench (26 CONTROLLED + 44 REAL), ProvenanceLens
attempted **12** repairs (6 on the real track) and **no false repair was
observed**: 0/12 combined, 0/6 real, under the Phase F definition
(incorrect attempted repairs / attempted repairs). Unverifiable repairs: 0/12.
`docs/METHODOLOGY.md` §11 · `results/phase_g/tables/headline_metrics.csv`

**S2 — Every observed action error was an abstention.**
All **7** failing cases (63/70 correct) are abstentions: 6 `unverifiable_lineage`
and 1 `insufficient_support`. No incorrect affirmative repair and no incorrect
`KEEP` was observed. `results/phase_g/tables/failure_taxonomy.csv`

**S3 — Action accuracy, with denominators.**
62/70 = 0.886 combined (Wilson 95% [0.790, 0.941]); REAL 36/44 = 0.818
[0.680, 0.905]; CONTROLLED 26/26 = 1.000. The controlled figure is a
specification check, not evidence of generality.
`results/phase_g/tables/headline_real.csv`

**S4 — Coverage is low, and that is the measured cost of the policy.**
Coverage 21/70 = 0.300 combined, 10/44 = 0.227 real; abstention 49/70 = 0.700.
`results/phase_g/tables/headline_metrics.csv`

**S5 — Structured tool-generated lineage evidence was important for affirmative
repairs on this benchmark.**
Removing adapter/merge/training configs reduced repair attempts from **12 to 0**
and action accuracy by 0.271 (0.886 → 0.614). This is an ablation result on 70
cases, not a general statement about evidence types.
`results/phase_g/tables/ablation_results.csv`

**S6 — Relation evidence is the main constraint on coverage.**
Removing relations from all evidence collapsed coverage from 0.300 to 0.014 and
reduced action accuracy by 0.257.
`results/phase_g/tables/ablation_results.csv`

**S7 — Reliability tiering mattered on this benchmark.**
Flattening all reliability tiers to a single tier reduced action accuracy by
0.243 and coverage to 0.029.
`results/phase_g/tables/ablation_results.csv`

**S8 — Conflict-aware, independence-aware fusion beat simpler strategies here.**
The full system reached 0.886 action accuracy with 0 false repairs; the
aggressive `rule_priority` baseline reached 0.371 with coverage 0.929 and 1 false
repair, and `majority_count` reached 0.357. `results/phase_g/tables/system_comparison.csv`

**S9 — Two evidence classes changed no decision in the evaluated set.**
`no_prose` and `no_config` were exactly neutral (Δ = 0.000) across all 70 cases.
A negative result about this benchmark, reported as such.
`results/phase_g/tables/ablation_results.csv`

**S10 — Quantized AWQ lineage is a measured weakness.**
The `quantized_awq` stratum scored 0/5 on action accuracy, all of them
abstentions on cases whose lineage is documented only in the model card.
`results/phase_g/tables/stratified_results.csv`

**S11 — A small local model added no usable evidence in this experiment.**
With `llama3.2:3b` on six frozen cards: 20 claims reported, **0 accepted**, 0
repair attempts, 0 false repairs. Rejections were grounding and formatting
failures. On `webAI-Official/TwIL-LM3` the correct parent was produced but
rejected for quoting a span that did not contain it. This is a result about this
model at these prompts, not about local models in general. `docs/METHODOLOGY.md` §13

**S12 — The whole pipeline is offline, deterministic and byte-reproducible.**
Two study runs produce byte-identical artifacts; a minimal environment (no
matplotlib, no LangChain) produces metrics identical to the full environment;
the study imports with the network stack absent. `docs/REPRODUCIBILITY.md`

**S13 — Accuracy does not depend on the support threshold in the observed range.**
Selectively accepting decisions was accurate at every measured threshold
(21/21 at coverage 0.300; 16/16 at 0.229), with 0 false repairs at all 21 points.
`results/phase_g/tables/risk_coverage_curve.csv`

**S14 — More than half the benchmark's lineage truth is unknowable.**
38 of 70 cases have an `ambiguous` or `unknown` parent truth, by adjudication
rather than by omission. The system abstains on 49.
`results/phase_g/results.json`

## Not supported — do not claim these

**N1 — "ProvenanceLens never makes incorrect repairs."**
Not supported. 0/12 is an observed count with a 95% interval reaching 0.242, and
it covers only the 12 attempts that occurred. The failure mode exists; the design
lowers its rate.

**N2 — "ProvenanceLens guarantees safety."**
Not supported and not claimed. No guarantee is stated anywhere in the code or
docs; the design intent is conservative, which is different from a guarantee.

**N3 — "Tool-generated evidence is universally required for lineage repair."**
Not supported. S5 is an ablation on 70 cases. A repository whose lineage is only
documented in prose would be a counterexample in principle — the system is
currently unable to use prose alone (S9), which is a limitation, not a law.

**N4 — "State of the art" / "first provenance system for model repositories" /
"outperforms existing tools".**
Not supported and not claimed. No comparison with any external lineage tool was
run; the baselines are this project's own stand-ins.

**N5 — "ProvenanceLens is accurate on real repositories."**
Too strong. 36/44 = 0.818 on 44 self-adjudicated repositories, with a 0/5
stratum, a 0.227 coverage and one adjudicator. Say "on these 44 repositories,
with labels adjudicated by the project authors".

**N6 — "coverage of 0.886" / "89% accuracy" without denominators.**
Misleading in both directions: 0.886 is action accuracy, not coverage (0.300),
and the denominators differ per metric (70, 44, 32, 31, 18, 12, 6).

**N7 — "`support_score` is a confidence" / "the system is 90% sure".**
Not supported and explicitly rejected in code: the score is a capped sum of
documented contributions, not a probability, so no ECE, Brier or reliability
diagram is reported. The calibration module refuses uncalibrated inputs.

**N8 — "Local LLM extraction does not work."**
Not supported. S11 is one model, six cards, one prompt. The measured problem is
grounding and output fidelity at that model size; a stronger grounded extraction
setup is untested.

**N9 — "False repairs are impossible / absent in practice."**
Not supported, and the strongest available evidence points the other way: 38 of
70 truths are unknowable, so many future repairs would be unverifiable rather
than verified-correct.

**N10 — "The benchmark reflects how common these problems are."**
Not supported. Selection was stratified for evidence diversity, not
representativeness, and over-samples rare shapes.

## Phrasing template

When citing this project, use the scope and the denominator every time:

> On the 70-case LineageRepairBench (26 controlled, 44 real-repository cases
> adjudicated by the project authors), ProvenanceLens attempted 12 repairs and no
> false repair was observed (0/12). Action accuracy was 62/70 overall and 36/44
> on real repositories, at a coverage of 21/70; all 7 errors were abstentions.

That sentence is fully supported by `results/phase_g/` and survives review.
