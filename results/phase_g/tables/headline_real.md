| metric | numerator | denominator | value | ci95_low | ci95_high | definition |
| --- | --- | --- | --- | --- | --- | --- |
| action_accuracy | 36 | 44 | 0.8182 | 0.6804 | 0.9049 | action correct / scored cases |
| parent_exact_match | 9 | 18 | 0.5000 | 0.2903 | 0.7097 | exact parent-set match over cases with KNOWN parent truth (multi-parent compared as a set) |
| relation_accuracy | 10 | 18 | 0.5556 | 0.3372 | 0.7544 | relation correct / scored cases |
| coverage | 10 | 44 | 0.2273 | 0.1284 | 0.3699 | non-ABSTAIN predictions / scored cases (abstention is never counted as correct) |
| repair_attempt_rate | 6 | 44 | 0.1364 | 0.0640 | 0.2671 | attempted repairs (ADD or REPLACE) / scored cases |
| false_repair_rate | 0 | 6 | 0.0000 | 0.0000 | 0.3903 | incorrect attempted repairs / attempted repairs (the false repair rate) |
| unverifiable_repair_rate | 0 | 6 | 0.0000 | 0.0000 | 0.3903 | attempted repairs whose correctness cannot be verified / attempted repairs |
| abstention_rate | 34 | 44 | 0.7727 | 0.6301 | 0.8716 | ABSTAIN predictions / scored cases |
