| metric | numerator | denominator | value | ci95_low | ci95_high | definition |
| --- | --- | --- | --- | --- | --- | --- |
| action_accuracy | 62 | 70 | 0.8857 | 0.7904 | 0.9409 | action correct / scored cases |
| parent_exact_match | 19 | 32 | 0.5938 | 0.4226 | 0.7448 | exact parent-set match over cases with KNOWN parent truth (multi-parent compared as a set) |
| relation_accuracy | 21 | 31 | 0.6774 | 0.5014 | 0.8143 | relation correct / scored cases |
| coverage | 21 | 70 | 0.3000 | 0.2054 | 0.4154 | non-ABSTAIN predictions / scored cases (abstention is never counted as correct) |
| repair_attempt_rate | 12 | 70 | 0.1714 | 0.1009 | 0.2762 | attempted repairs (ADD or REPLACE) / scored cases |
| false_repair_rate | 0 | 12 | 0.0000 | 0.0000 | 0.2425 | incorrect attempted repairs / attempted repairs (the false repair rate) |
| unverifiable_repair_rate | 0 | 12 | 0.0000 | 0.0000 | 0.2425 | attempted repairs whose correctness cannot be verified / attempted repairs |
| abstention_rate | 49 | 70 | 0.7000 | 0.5846 | 0.7946 | ABSTAIN predictions / scored cases |
