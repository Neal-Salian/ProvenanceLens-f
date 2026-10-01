---
license: gemma
base_model: google/gemma-4-e4b-it
language:
- ar
- en
library_name: transformers
pipeline_tag: text-generation
tags:
- gemma
- arabic
- dialectal-arabic
- nli
- claims-comparison
- lora
- fine-tuned
---

# gemma4-e4b-claims-comparison

A fine-tuned [`google/gemma-4-e4b-it`](https://huggingface.co/google/gemma-4-e4b-it)
that acts as a **Dialectal Arabic Natural Language Inference (NLI) engine**. Given two
Arabic claims (`claim_a`, `claim_b`), it reasons inside its thinking channel
and outputs **exactly one** of seven semantic-relationship categories.

This checkpoint is the LoRA adapter merged back into the base model (full bf16 weights).

## Categories

| # | Category | Meaning |
|---|----------|---------|
| 1 | `Equivalent` | Same scope and fact; differ only in linguistic form (paraphrase). |
| 2 | `Contradictory` | The claims explicitly violate or contradict each other. |
| 3 | `OverlapIncomparable` | Share common elements, but each has independent facts absent from the other. |
| 4 | `DifferentFacts` | Completely distinct facts with no meaningful semantic overlap. |
| 5 | `Uncertain` | Ambiguous, pronoun-heavy without referents, or lacking context to judge. |
| 6 | `A-MoreSpecific` | Same core fact, but `claim_a` adds compatible, granular details. |
| 7 | `B-MoreSpecific` | Same core fact, but `claim_b` adds compatible, granular details. |

Ties are resolved to the **lowest numerical index**.

## Prompt format

The model expects a **system** turn with the task instructions and a **user** turn with
the two claims. It emits its reasoning in a thinking channel (`<|channel>thought … <channel|>`)
and then the final category name.

**System message:**

```text
You are an expert Dialectal Arabic Natural Language Inference (NLI) engine.
Your task is to compare two Arabic claims (claim_a and claim_b) and categorize their semantic relationship into exactly ONE of seven categories.

Categories:
1) Equivalent: Same scope and fact; differing only in linguistic form (paraphrase).
2) Contradictory: The claims explicitly violate or contradict each other.
3) OverlapIncomparable: Share common elements, but each contains independent facts absent from the other.
4) DifferentFacts: Completely distinct facts with no meaningful semantic overlap.
5) Uncertain: Text is ambiguous, pronoun-heavy without referents, or lacks necessary context to judge.
6) A-MoreSpecific: Same core fact, but claim_a adds compatible, granular details.
7) B-MoreSpecific: Same core fact, but claim_b adds compatible, granular details.

Protocol:
1. Analyze the semantic core, entities, temporal modifiers, and negation markers in both claims inside your thinking channel. Always reason in ENGLISH, even though the claims are in Arabic.
2. Determine the exact logical relationship category.
3. If a claim pair exhibits characteristics of multiple categories, you must resolve the tie by strictly selecting the category with the lowest numerical index (e.g., if a pair could be interpreted as both Contradictory [2] and DifferentFacts [4], you must output Contradictory).
4. Output ONLY the category name as your final response outside the thought block. It MUST be EXACTLY one of: Equivalent, Contradictory, OverlapIncomparable, DifferentFacts, Uncertain, A-MoreSpecific, B-MoreSpecific. No other text, no punctuation.
```

**User message:**

```text
claim_a: {a}
claim_b: {b}
```

**Assistant message** (what the model produces):

```text
<|channel>thought
...English reasoning about the two claims...
<channel|>
Equivalent
```

## Inference

```python
from transformers import pipeline, GenerationConfig

MODEL_ID = "k-chirkunov/gemma4-e4b-claims-comparison"

SYSTEM_PROMPT = """\
You are an expert Dialectal Arabic Natural Language Inference (NLI) engine.
Your task is to compare two Arabic claims (claim_a and claim_b) and categorize their semantic relationship into exactly ONE of seven categories.

Categories:
1) Equivalent: Same scope and fact; differing only in linguistic form (paraphrase).
2) Contradictory: The claims explicitly violate or contradict each other.
3) OverlapIncomparable: Share common elements, but each contains independent facts absent from the other.
4) DifferentFacts: Completely distinct facts with no meaningful semantic overlap.
5) Uncertain: Text is ambiguous, pronoun-heavy without referents, or lacks necessary context to judge.
6) A-MoreSpecific: Same core fact, but claim_a adds compatible, granular details.
7) B-MoreSpecific: Same core fact, but claim_b adds compatible, granular details.

Protocol:
1. Analyze the semantic core, entities, temporal modifiers, and negation markers in both claims inside your thinking channel. Always reason in ENGLISH, even though the claims are in Arabic.
2. Determine the exact logical relationship category.
3. If a claim pair exhibits characteristics of multiple categories, you must resolve the tie by strictly selecting the category with the lowest numerical index (e.g., if a pair could be interpreted as both Contradictory [2] and DifferentFacts [4], you must output Contradictory).
4. Output ONLY the category name as your final response outside the thought block. It MUST be EXACTLY one of: Equivalent, Contradictory, OverlapIncomparable, DifferentFacts, Uncertain, A-MoreSpecific, B-MoreSpecific. No other text, no punctuation.
"""

USER_TEMPLATE = "claim_a: {a}\nclaim_b: {b}\n"

CATEGORIES = [
    "Equivalent", "Contradictory", "OverlapIncomparable",
    "DifferentFacts", "Uncertain", "A-MoreSpecific", "B-MoreSpecific",
]

pipe = pipeline(task="any-to-any", model=MODEL_ID, dtype="auto", device_map="auto")

gen = GenerationConfig.from_pretrained(MODEL_ID)
gen.max_new_tokens = 4096
gen.do_sample = True
gen.temperature = 0.3
gen.top_p = 0.95
gen.top_k = 64


def compare(claim_a: str, claim_b: str) -> str:
    messages = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT.strip()}]},
        {"role": "user", "content": [{"type": "text", "text": USER_TEMPLATE.format(a=claim_a, b=claim_b)}]},
    ]
    out = pipe(
        messages,
        return_full_text=False,
        skip_special_tokens=False,        # keep <channel|> so we can split off the reasoning
        chat_template_kwargs={"enable_thinking": True},
        generate_kwargs={"generation_config": gen},
    )
    raw = out[0]["generated_text"].strip()

    # Take only the text after the thinking channel closes.
    text = raw.rsplit("<channel|>", 1)[-1] if "<channel|>" in raw else raw
    for marker in ("<eos>", "<pad>", "<turn|>", "<|turn>", "<|think|>", "<|channel>"):
        text = text.replace(marker, "")
    text = text.strip().lower()

    # Pick the category mentioned last in the final answer.
    best, best_pos = "Uncertain", -1
    for c in CATEGORIES:
        pos = text.rfind(c.lower())
        if pos > best_pos:
            best, best_pos = c, pos
    return best


if __name__ == "__main__":
    a = "الطعام في المطعم كان لذيذاً جداً"
    b = "الأكل في المطعم كان طيب مرة"
    print(compare(a, b))   # -> Equivalent
```

> **Note on special tokens.** This chat template uses `<|turn>role` / `<turn|>` turn markers
> and a `<|channel>thought … <channel|>` thinking channel — all registered special tokens.
> Pass `skip_special_tokens=False` so the `<channel|>` delimiter survives decoding, split the
> raw text on it to separate reasoning from the final answer, and only then strip the remaining
> marker tokens.

## Training

- **Base model:** `google/gemma-4-e4b-it`
- **Method:** LoRA SFT (r=16, alpha=32) on the language-model projection layers, merged to full bf16 weights.
- **Loss:** completion-only (prompt tokens masked).
- **Data:** [`k-chirkunov/jeeran_claims_comparison_conversations`](https://huggingface.co/datasets/k-chirkunov/jeeran_claims_comparison_conversations)

## License

Governed by the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
