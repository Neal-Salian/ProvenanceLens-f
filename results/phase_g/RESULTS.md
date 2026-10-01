# ProvenanceLens — measured results (LineageRepairBench)

> Generated from `results/phase_g/results.json` by `provenancelens.evaluation.canonical`. Do not edit by hand: regenerate with `python -m provenancelens.evaluation.phase_g_cli publish --canonical results/phase_g`. A test fails if this file and a fresh run disagree.

- Report digest: `9e85c22f7e3ec98f7c1bf274347081c5883466d40791161f5e497e638a5fa65b`
- Benchmark version: `1.0` (phase-f-g-1.0 metric definitions)
- Offline, deterministic, no LLM and no network.

## Benchmark composition

| track | n_cases | label_provenance |
| --- | --- | --- |
| controlled | 26 | synthetic_construction |
| real | 44 | manual_adjudication |
| TOTAL | 70 | mixed |

Expected action labels (adjudicated, not predicted):

| expected_action | n_cases |
| --- | --- |
| ABSTAIN | 43 |
| ADD | 16 |
| KEEP | 9 |
| REPLACE | 2 |

Declared-metadata state as adjudicated:

| metadata_state | n_cases |
| --- | --- |
| incomplete | 6 |
| incorrect | 2 |
| missing | 16 |
| undetermined | 38 |
| valid | 8 |

Cases whose parent truth is not knowable (ambiguous or unknown): **38** of 70.

## Main results — CONTROLLED

| metric | numerator | denominator | value | ci95 |
| --- | --- | --- | --- | --- |
| action_accuracy | 26 | 26 | 1.0000 | [0.871, 1.000] |
| parent_exact_match | 10 | 14 | 0.7143 | [0.454, 0.883] |
| relation_accuracy | 11 | 13 | 0.8462 | [0.578, 0.957] |
| coverage | 11 | 26 | 0.4231 | [0.255, 0.611] |
| repair_attempt_rate | 6 | 26 | 0.2308 | [0.110, 0.421] |
| false_repair_rate | 0 | 6 | 0.0000 | [0.000, 0.390] |
| unverifiable_repair_rate | 0 | 6 | 0.0000 | [0.000, 0.390] |
| abstention_rate | 15 | 26 | 0.5769 | [0.389, 0.745] |

## Main results — REAL

| metric | numerator | denominator | value | ci95 |
| --- | --- | --- | --- | --- |
| action_accuracy | 36 | 44 | 0.8182 | [0.680, 0.905] |
| parent_exact_match | 9 | 18 | 0.5000 | [0.290, 0.710] |
| relation_accuracy | 10 | 18 | 0.5556 | [0.337, 0.754] |
| coverage | 10 | 44 | 0.2273 | [0.128, 0.370] |
| repair_attempt_rate | 6 | 44 | 0.1364 | [0.064, 0.267] |
| false_repair_rate | 0 | 6 | 0.0000 | [0.000, 0.390] |
| unverifiable_repair_rate | 0 | 6 | 0.0000 | [0.000, 0.390] |
| abstention_rate | 34 | 44 | 0.7727 | [0.630, 0.872] |

## Main results — COMBINED

| metric | numerator | denominator | value | ci95 |
| --- | --- | --- | --- | --- |
| action_accuracy | 62 | 70 | 0.8857 | [0.790, 0.941] |
| parent_exact_match | 19 | 32 | 0.5938 | [0.423, 0.745] |
| relation_accuracy | 21 | 31 | 0.6774 | [0.501, 0.814] |
| coverage | 21 | 70 | 0.3000 | [0.205, 0.415] |
| repair_attempt_rate | 12 | 70 | 0.1714 | [0.101, 0.276] |
| false_repair_rate | 0 | 12 | 0.0000 | [0.000, 0.242] |
| unverifiable_repair_rate | 0 | 12 | 0.0000 | [0.000, 0.242] |
| abstention_rate | 49 | 70 | 0.7000 | [0.585, 0.795] |

Intervals are Wilson 95% score intervals; several denominators are small, so a point estimate alone would mislead. `parent_exact_match` and `relation_accuracy` are scored only on cases with KNOWN truth, which is why their denominators are smaller than the case count.

## Repair safety

| quantity | combined | real |
| --- | --- | --- |
| repair attempts | 12 | 6 |
| false repairs | 0 | 0 |
| unverifiable repairs | 0 | 0 |
| False Repair Rate (numerator/denominator) | 0/12 | 0/6 |

**False Repair Rate** = incorrect attempted repairs / total attempted repairs, where an attempted repair is an ADD or REPLACE whose proposed lineage contradicts adjudicated truth that is KNOWN. An attempt on non-knowable truth is reported separately as *unverifiable* and is counted as neither correct nor false. This definition is unchanged from Phase F.

Zero observed false repairs is a property of this 70-case benchmark, not a guarantee: see `docs/THREATS_TO_VALIDITY.md`.

## Coverage and abstention

| scope | coverage | abstention_rate | action_accuracy |
| --- | --- | --- | --- |
| COMBINED | 0.3000 | 0.7000 | 0.8857 |
| REAL | 0.2273 | 0.7727 | 0.8182 |


## Baseline comparison

| system | action_accuracy | macro_f1 | coverage | attempted_repairs | false_repairs | parent_exact_match | relation_accuracy | abstention_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| provenancelens | 0.8857 | 0.8928 | 0.3000 | 12 | 0 | 0.5938 | 0.6774 | 0.7000 |
| config_only | 0.6143 | 0.7611 | 0.0000 | 0 | 0 | 0.0000 | 0.0000 | 1.0000 |
| prose_only | 0.6143 | 0.7611 | 0.0000 | 0 | 0 | 0.0000 | 0.0000 | 1.0000 |
| rule_priority | 0.3714 | 0.4792 | 0.9286 | 23 | 1 | 0.9375 | 0.7742 | 0.0714 |
| majority_count | 0.3571 | 0.4703 | 0.8286 | 21 | 0 | 0.9062 | 0.5161 | 0.1714 |
| always_keep | 0.3286 | 0.3726 | 0.6571 | 0 | 0 | 0.5625 | 0.1935 | 0.3429 |
| declared_metadata | 0.3286 | 0.3726 | 0.6571 | 0 | 0 | 0.5625 | 0.1935 | 0.3429 |

`config_only` and `prose_only` abstain on every case: honest but useless alone. `rule_priority` and `majority_count` repair far more often and are far less accurate; `rule_priority` is the only baseline that produces a false repair. `declared_metadata` and `always_keep` are identical by construction (neither ever repairs).

## Ablation results

| ablation | action_accuracy | delta_action_accuracy | macro_f1 | coverage | attempted_repairs | false_repairs | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full | 0.8857 | 0.0000 | 0.8928 | 0.3000 | 12 | 0 | reference |
| no_prose | 0.8857 | 0.0000 | 0.8928 | 0.3000 | 12 | 0 | no measurable effect on this benchmark |
| no_config | 0.8857 | 0.0000 | 0.8928 | 0.3000 | 12 | 0 | no measurable effect on this benchmark |
| no_tool_configs | 0.6143 | -0.2714 | 0.7611 | 0.0000 | 0 | 0 | component matters (removing it hurts) |
| only_tool_configs | 0.8857 | 0.0000 | 0.8928 | 0.3000 | 12 | 0 | no measurable effect on this benchmark |
| inflate_duplicates | 0.8571 | -0.0286 | 0.8034 | 0.3286 | 14 | 0 | component matters (removing it hurts) |
| flatten_reliability | 0.6429 | -0.2429 | 0.5471 | 0.0286 | 1 | 0 | component matters (removing it hurts) |
| no_relation_evidence | 0.6286 | -0.2571 | 0.4839 | 0.0143 | 0 | 0 | component matters (removing it hurts) |
| highest_priority_only | 0.8571 | -0.0286 | 0.8506 | 0.2714 | 10 | 0 | component matters (removing it hurts) |
| only_highest_reliability | 0.8571 | -0.0286 | 0.8506 | 0.2714 | 10 | 0 | component matters (removing it hurts) |

Each ablation transforms the evidence handed to the **unmodified** engine, so a delta is attributable to the ablated component. Verdicts are descriptive, not significance tests.

Pre-registered hypotheses (kept even where the measurement contradicted them):

- `no_prose` — RQ4: how much of the decision comes from model-card prose? Prose is a supporting signal, not a deciding one: removing it should not create a false repair.
- `no_config` — RQ4: how much does framework config contribute? config.json-style evidence is the main structured signal and should matter more than prose.
- `no_tool_configs` — RQ4: how much do adapter/merge/training files contribute? These files carry the strongest lineage signal; removing them should cost recall on adapter and merge cases.
- `only_tool_configs` — RQ4: are adapter/merge/training files sufficient alone? They are necessary but not sufficient: prose and config resolve cases whose lineage is only documented in the model card.
- `inflate_duplicates` — RQ5: what does per-file deduplication buy? Naive record counting inflates support with repeated mentions and should produce over-confident repair attempts.
- `flatten_reliability` — RQ6: does tiered reliability matter versus equal tiers? Tiered reliability separates tool-generated lineage from model-card claims, so flattening it should cost precision.
- `no_relation_evidence` — RQ7: how much does relation evidence matter? Relations are rarely provable from artifacts alone; removing them should shift repair actions toward parent-only changes.
- `highest_priority_only` — RQ8: is a fixed source hierarchy sufficient? A single source hierarchy cannot express conflicts, so accuracy should drop relative to conflict-aware fusion.
- `only_highest_reliability` — RQ8: does the single best item decide? Taking only the strongest item discards corroboration and should cost precision.

## Selective prediction (risk–coverage)

| threshold | coverage | accepted | selective_accuracy | selective_accuracy_ci95 | attempted_repairs | false_repairs |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0000 | 0.3000 | 21 | 1.0000 | - | 12 | 0 |
| 0.5000 | 0.3000 | 21 | 1.0000 | - | 12 | 0 |
| 1.0000 | 0.0286 | 21 | 1.0000 | - | 2 | 0 |

Selected from 21 measured thresholds (0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0); the full sweep is in `tables/risk_coverage_curve.csv`.

## Failure analysis

| category | n_cases | n_controlled | n_real | description |
| --- | --- | --- | --- | --- |
| correct | 63 | 26 | 37 | the decision matched the adjudicated label |
| unverifiable_lineage | 6 | 0 | 6 | no independent evidence exists, so abstention is the only safe action |
| insufficient_support | 1 | 0 | 1 | evidence exists but its support score is below the policy threshold |
| relation_not_provable | 0 | 0 | 0 | the parent is identifiable but no artifact establishes the relation |
| prose_only_lineage | 0 | 0 | 0 | lineage is documented only in model-card prose without a canonical id |
| declared_metadata_contradicted | 0 | 0 | 0 | the declared metadata contradicts what independent evidence shows |
| multi_parent_conflict | 0 | 0 | 0 | several parents are supported and the policy cannot choose among them |
| false_repair | 0 | 0 | 0 | an attempted repair contradicted knowable truth |
| incorrect_non_repair | 0 | 0 | 0 | a KEEP or abstention decision was wrong for another reason |

Every one of the 7 failures is an abstention: no incorrect affirmative repair and no incorrect KEEP was observed. Per-case detail is in `tables/failures.csv`.

## Per-stratum results

| stratum | n_cases | action_accuracy | action_accuracy_ci95 | coverage | attempted_repairs | false_repairs |
| --- | --- | --- | --- | --- | --- | --- |
| controlled | 26 | 1.0000 | - | 0.4231 | 6 | 0 |
| instruction_finetunes | 8 | 1.0000 | - | 0.0000 | 0 | 0 |
| lora_adapters | 6 | 0.8333 | - | 0.0000 | 0 | 0 |
| mergekit_merges | 8 | 1.0000 | - | 0.0000 | 0 | 0 |
| peft_adapters | 8 | 1.0000 | - | 1.0000 | 5 | 0 |
| pre_phase_g | 3 | 1.0000 | - | 0.6667 | 1 | 0 |
| quantized_awq | 5 | 0.0000 | - | 0.0000 | 0 | 0 |
| quantized_gguf | 6 | 0.8333 | - | 0.0000 | 0 | 0 |

Strata are the ones the acquisition plan declared (see `data/acquisition/real_selection.json`), not strata derived from results. `quantized_awq` is the clearest measured weakness: 0/5, because for every AWQ derivative the parent is declared and the relation is documented only in the model card, with no structured artifact stating it.

## Evidence contribution

| source | cases_present | presence_share | decisive_items |
| --- | --- | --- | --- |
| adapter_config | 18 | 0.2571 | 18 |
| config | 5 | 0.0714 | 4 |
| merge_config | 4 | 0.0571 | 9 |
| readme | 10 | 0.1429 | 5 |
| training_config | 8 | 0.1143 | 5 |

presence is frequency; decisiveness is attribution. Declared metadata is the audit subject and is never independent evidence, so it appears in neither column. A decisive item is an independent evidence item whose candidate parent is in the adjudicated parent set. Whether such an item changes the final decision is a different question, answered by the ablation table rather than by these counts.

## Local LLM extraction experiment (optional, opt-in)

Run separately with `python -m provenancelens.evaluation.phase_g_cli llm-compare --model llama3.2:3b`. It is **not** part of the deterministic study and its output is not in this manifest. Measured with the already-installed `llama3.2:3b` on the six frozen cards where lineage is documented but no structured artifact states it: 20 claims reported, 0 accepted, 0 repair attempts, 0 false repairs; rejections were 15 `span_not_found`, 15 `malformed_output`, 4 `lineage_not_stated`, 1 `parent_not_in_source`. On `webAI-Official/TwIL-LM3` the model produced the correct parent but quoted a span that did not contain it, so validation rejected it. Read this as a grounding and output-fidelity problem at that model size, not as evidence that local models are useless.

## Calibration status

`support_score` is a heuristic evidence strength — a capped sum of documented per-artifact contributions — with no frequency interpretation. ECE, Brier score and reliability diagrams are therefore **not** reported anywhere. Probability calibration stays deferred until a mapping can be fitted on a held-out split (>= 50 cases) and evaluated on a disjoint split.

## Limitations

See `docs/LIMITATIONS.md` and `docs/THREATS_TO_VALIDITY.md`. In short: 70 self-authored cases, 44 of them from one hosting ecosystem and self-adjudicated; zero observed false repairs is not a guarantee; `quantized_awq` lineage is a measured gap; and no claim of state of the art or universal superiority is made.
