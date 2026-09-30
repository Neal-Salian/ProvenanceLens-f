---
language:
  - en
library_name: transformers
pipeline_tag: text-generation
base_model: HuggingFaceTB/SmolLM3-3B
license: other
license_name: webai-non-commercial-license-ver.-1.0
license_link: https://huggingface.co/webAI-Official/TwIL-LM3/blob/main/LICENSE.md
tags:
  - formal-logic
  - reasoning
  - lora
  - model-merging
  - wise-ft
  - reinforcement-learning
  - grpo
  - smollm3
  - twil-lm
---

# TwIL-LM3

A 3B reasoning model for **formal logic** tasks, built from
[`HuggingFaceTB/SmolLM3-3B`](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) through LoRA
supervised fine-tuning, checkpoint fusion, WiSE-FT weight interpolation, and entropy-weighted
GRPO reinforcement learning.

It improves in-domain formal-logic performance by **+26% relative** over its base model
(macro gate 0.336 → 0.422) **and improves held-out benchmark performance at the same time**
(+0.022 core average). It is the only arm in this project that gains on both tracks, which is
why it is the recommended release of the pair.

Try out the model on our TwIL-LM3.1 branch, a better version of TwIL-LM3. 

![TwIL-LM3 formal and general reasoning benchmarks against gpt-oss-120b, Qwen3-8B, LFM2-2.6B and Llama-3.2-3B](benchmarks.jpg)

## Highlights

* **Gains on both tracks at once** — the only arm in this project that does. In-domain macro gate
  0.336 → 0.422, and the held-out 10-dataset macro 0.7193 → 0.7339 rather than the usual collapse
  that follows task-specific fine-tuning.
* **Beats every arm up to and including LFM2.5-8B-A1B** — roughly three times its parameter count
  — on all six Track A objective lanes and all four summary rows, not on average alone.
* **Competitive with 8B on strict scoring.** On strict-7, which gives no loose-match credit
  anywhere, it sits 0.012 behind Qwen3-8B (0.1971 against 0.2093) at 2.6x fewer parameters, and
  ahead of it on Lean formalisation (token-F1 0.5869 against 0.4022) and semantic parsing (0.4416
  against 0.4257).
* **Structured formal output.** Tuned for the objects rather than the prose: FOL translation,
  entailment labels, semantic parses, Lean statements and Lean proof critique.
* **The most efficient arm measured, at any scale.** 482-token Track B generations and 32.9
  completed answers per second — about eight times gpt-oss-120b's rate — because it answers
  short rather than because it decodes unusually fast.
* **Lowest maths-corpus perplexity of any released arm in the table** (3.8229), including
  Qwen3-8B at 4.0083.
* **Runs anywhere.** 3.08B parameters in bf16, with Q4\_K\_M GGUF at 1.78 GiB for CPU or 4 GB of
  VRAM.

It is not a general assistant: there is no safety or preference tuning here beyond what SmolLM3
carries, and instruction following regressed slightly. See
[Limitations](#limitations-and-caveats).

## Model Details

| Property                  | Value                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| Model ID                  | `webAI-Official/TwIL-LM3`                                                                            |
| Base model                | [`HuggingFaceTB/SmolLM3-3B`](https://huggingface.co/HuggingFaceTB/SmolLM3-3B)                |
| Total parameters          | 3.08B                                                                                       |
| Architecture              | SmolLM3 decoder-only transformer; 36 layers, hidden size 2048                                |
| Input / output            | Text / text                                                                                 |
| Language                  | English                                                                                     |
| Tokenizer vocabulary size | 128,256                                                                                     |
| Context window            | 65,536 tokens                                                                               |
| Checkpoint precision      | bfloat16 (5.73 GiB), plus Q4\_K\_M / Q5\_K\_M / Q6\_K / Q8\_0 / F16 GGUF builds              |
| Post-training             | LoRA SFT → checkpoint fusion → WiSE-FT (λ = 0.25) → MGPO reinforcement learning (step 2071)  |
| Reasoning format          | Emits a `<think>…</think>` block before the answer                                           |
| Evaluated decoding        | Greedy, 2048 new tokens, `max_seq_len` 8192                                                  |
| Specialisation            | Formal logic: FOL translation, entailment, semantic parsing, Lean formalisation and critique |
| License                   | webAI Non-Commercial License ver. 1.0                                                       |

The base model's 65,536-token context is carried through unchanged, but every score on this card
was measured inside an 8,192-token window; longer contexts are inherited rather than validated
here.

## Results

### Track A — in-domain formal logic

All arms below were run through the same harness, prompts and decoding settings described under
[Evaluation protocol](#evaluation-protocol). Throughput rows are reported because in-domain score
alone is misleading for a 3B model: `ans/s` is defined throughout as `tok/s ÷ mean generation
length`, so it measures completed answers rather than raw decode rate.

| lane / metric | TwIL-LM3 | TwIL-LM3* | SmolLM3-3B base | Llama-3.2-3B | LFM2-2.6B | LFM2.5-8B-A1B | Qwen3-8B | gpt-oss-120b ‡ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| lean_formalize token_f1 | 0.5869 | **0.6456** | 0.4347 | 0.3690 | 0.1321 | 0.4655 | 0.4022 | 0.6306 |
| rule_induction derivation | 0.3192 | **0.9644** | 0.1029 | 0.0825 | 0.0615 | 0.1936 | 0.3680 | 0.6518 |
| entailment_label accuracy | 0.5750 | 0.6867 | 0.3750 | 0.3300 | 0.4700 | 0.5400 | 0.5800 | **0.7750** |
| mcq_answer accuracy | 0.1100 | **0.5200** | 0.0000 | 0.0000 | 0.0150 | 0.0750 | 0.0000 | 0.0700 |
| semantic_parse token_f1 | 0.4416 | **0.8762** | 0.4149 | 0.3102 | 0.3665 | 0.3778 | 0.4257 | 0.4331 |
| lean_critic accuracy | 0.6600 | 0.5200 | 0.6500 | 0.5300 | 0.5900 | 0.5500 | **0.7950** | 0.5550 |
| lm_corpus perplexity ↓ | 2.8972 | 3.1284 | 3.1818 | 2.8478 | 4.3815 | 4.9472 | **2.5440** | 912.23 § |
| math_corpus perplexity ↓ | 3.8229 | **3.5245** | 4.0685 | 4.7531 | 6.7472 | 8.3323 | 4.0083 | 1045.63 § |
| average, 6 lanes | 0.4488 | **0.7021** | 0.3296 | 0.2703 | 0.2725 | 0.3670 | 0.4285 | 0.5192 |
| **macro gate** | 0.4218 | **0.5896** | 0.3466 † | 0.2925 | 0.3473 | 0.3757 | 0.5336 | — |
| **strict-7** | 0.1971 | **0.3290** | 0.1493 | 0.1229 | 0.1579 | 0.1714 | 0.2093 | — |
| macro_primary | 0.4475 | 0.4958 | 0.4075 | 0.3450 | 0.4188 | 0.4213 | **0.5750** | — |
| tok/s | 15880 | 15840 | 15564 | 16160 | **25230** | 22480 | 9420 | 3374 |
| mean gen length | **564** | 572 | 999 | 696 | 2296 | 1830 | 2094 | 1005 |
| **ans/s** | **28.1** | 27.7 | 15.6 | 23.2 | 10.9 | 12.0 | 4.5 | 3.4 |

\* **TwIL-LM3\*** is our latest version of TwIL-LM3. **The weights will be released soon** — the
files in this repository are the current TwIL-LM3 release, not this one. Lanes marked — are not
yet reported for it.

‡ **gpt-oss-120b** runs MXFP4 weights at tensor-parallel 2 — quantized and multi-GPU, so its
throughput rows are not directly comparable to the single-GPU BF16 arms. Its `procedural` lane
and the loose-match scorings were not collected, so the three summary rows below the six-lane
average cannot be computed for it; that is what the — cells mean, not a zero.

§ The 120B's perplexities are three orders of magnitude off every other arm because its harmony
response format and tokenizer make the corpus lanes score a different quantity. The number is
reported for completeness but is not a comparable measurement.

† The base column here comes from the external-comparison run rather than the paired base-vs-TwIL
run, hence 0.3466 against the 0.3356 quoted in the summary at the top of this card — run-to-run
variation of the same checkpoint. The paired run is the correct basis for the improvement claim.

**`average, 6 lanes`** is the plain mean of the six objective rows above it, each at whatever
scoring that row reports. It is a coarser summary than the three that follow — it mixes token-F1
with accuracy — but it is the only summary row every arm here can be compared on, including the
120B.

The next three rows aggregate more carefully. None of them include the perplexity lanes or the
token-F1 scorings, which are not on a common 0–1 accuracy scale.

**`macro gate`** is the headline metric and the one the training pipeline gates on. It is the
equal-weight mean of five objectives: the four bounded classification lanes (`entailment_label`,
`mcq_answer`, `procedural`, `lean_critic`) plus `rule_induction`, scored by its continuous
derivation score. Rule induction is included specifically so a fine-tune cannot pass the gate
while quietly regressing inductive reasoning. In the gate, `mcq_answer` and `procedural` are
credited as `max(exact_match, loose_match)`: for free-text answer lanes, a response that is
correct but differently formatted is a formatting artefact rather than a reasoning failure. This
affects the aggregate only — the per-lane rows above stay strict.

**`macro_primary`** is the same mean over the four classification lanes alone, without
`rule_induction`. It is the narrower "bounded classification" view, kept for comparability with
earlier reports; the gate is the metric to read for overall in-domain capability.

**`strict-7`** is the mean of seven lanes scored under strict metrics only (`fol_translation`,
`entailment_label`, `mcq_answer`, `semantic_parse` and `lean_formalize` exact match,
`lean_critic` and `procedural` accuracy), with no loose-match credit anywhere. It is deliberately
harsh — exact match on generative lanes is near zero for every arm — so it is useful for ranking
models against each other but not as an absolute capability measure.

TwIL-LM3 beats every arm up to and including LFM2.5-8B-A1B, and does so on all six objective
lanes and all four summary rows, not on average alone. Against the strongest of them it is
0.4218 to 0.3757 on the gate at roughly a third of the total parameters, with the margin coming
from the lanes the pipeline targets directly: `lean_formalize` token-F1 0.5869 against 0.4655,
`rule_induction` 0.3192 against 0.1936, `semantic_parse` 0.4416 against 0.3778.

It does not beat the two largest arms. Qwen3-8B leads it on the gate 0.5336 to 0.4218 and
gpt-oss-120b leads the six-lane average 0.5192 to 0.4488. That gap is worth reading carefully in
Qwen's case: almost all of it is loose-match credit. Qwen answers MCQ correctly but never in the
requested format — strict accuracy 0.0000 against TwIL-LM3's 0.1100, while its loose match is
0.745 — and the macro rows credit `max(exact_match, loose_match)`. On `strict-7`, which gives no
loose-match credit anywhere, the two are 0.2093 to 0.1971, a gap of 0.012 rather than 0.11. Qwen
also wins `lean_critic` outright at 0.7950 and has the lowest `lm_corpus` perplexity at 2.5440.
The 120B leads three lanes outright and is genuinely stronger at entailment (0.7750) and rule
induction (0.6518).

The size and speed context matters for both. Qwen3-8B is 2.6x the parameters and produces 4.5
answers/sec against TwIL-LM3's 28.1; the 120B is 40x the parameters and produces 3.4. TwIL-LM3
is the strongest arm here at its own scale and the most efficient arm at any scale.

The unreleased TwIL-LM3\* moves the gate to 0.5896 and strict-7 to 0.3290, roughly +0.17 and
+0.13 over the current release. The gains are concentrated in the two lanes where TwIL-LM3 is
weakest in absolute terms rather than relative ones — `rule_induction` 0.3192 → 0.9644 and
`semantic_parse` token-F1 0.4416 → 0.8762 — plus strict MCQ accuracy 0.1100 → 0.5200. It gives
back `lean_critic` (0.6600 → 0.5200) and a little `lm_corpus` perplexity, so it is not uniformly
better.

It is also the most efficient arm in the table by a wide margin — 28.1 answers/sec, from
generations averaging 564 tokens where every other arm except Llama runs past 690. The Liquid
models decode faster in raw tokens per second, 25230 and 22480 against 15880, but their length
more than cancels it.

### Track B — held-out benchmarks

| dataset | TwIL-LM3 | SmolLM3-3B base | Llama-3.2-3B | LFM2-2.6B | LFM2.5-8B-A1B | Qwen3-8B | gpt-oss-120b ‡ |
|---|---:|---:|---:|---:|---:|---:|---:|
| gsm8k | 0.8733 | 0.8833 | 0.8300 | 0.8767 | 0.9133 | 0.9567 | **0.9767** |
| svamp | 0.8500 | 0.8567 | 0.8200 | 0.9000 | 0.9133 | **0.9400** | **0.9400** |
| gsm_symbolic | 0.7567 | 0.7633 | 0.8067 | **0.9767** | 0.9267 | 0.8133 | 0.8467 |
| arc_cot | 0.8467 | 0.8400 | 0.7967 | 0.8667 | 0.9033 | 0.9633 | **0.9667** |
| logicbench | 0.7167 | 0.6467 | 0.5733 | 0.6267 | 0.7200 | **0.8567** | 0.8533 |
| strategyqa | 0.6500 | 0.6333 | 0.6533 | 0.6433 | 0.6667 | 0.7400 | **0.7867** |
| drop | 0.7467 | 0.7000 | 0.6733 | 0.6900 | 0.6633 | **0.8833** | 0.8500 |
| csqa | 0.7367 | 0.7067 | 0.7500 | 0.7433 | 0.7700 | **0.8633** | 0.8367 |
| musr | 0.4957 | 0.4997 | 0.4932 | 0.4867 | 0.5703 | 0.6301 | **0.6852** |
| mmlu_redux | 0.6667 | 0.6633 | 0.6000 | 0.7133 | 0.8367 | 0.8500 | **0.9467** |
| ifeval | 0.6433 | 0.6767 | 0.7167 | 0.7300 | **0.8900** | 0.8400 | 0.7900 |
| rudas_ood | 0.0365 | 0.0209 | **0.0733** | 0.0017 | 0.0061 | 0.0468 | 0.0000 ¶ |
| bbh_logic | 0.6633 | 0.6667 | 0.5333 | 0.5713 | 0.7700 | 0.6367 | **0.9980** |
| math500 | 0.6900 | 0.7000 | 0.4233 | 0.7133 | 0.7800 | 0.6100 | **0.8433** |
| **macro (10 CoT datasets)** | 0.7339 | 0.7193 | 0.6997 | 0.7523 | 0.7884 | 0.8493 | **0.8689** |
| **macro (all 14)** | 0.6694 | 0.6612 | 0.6245 | 0.6814 | 0.7378 | 0.7591 | **0.8086** |
| tok/s | 15880 | 15564 | 16160 | 25230 | 22480 | 9420 | 3374 |
| mean gen length | **482** | 626 | 510 | ≈796 | ≈1327 | ≈1931 | 801 |
| **ans/s** | **32.9** | 24.9 | 31.7 | ≈31.7 | ≈16.9 | 4.9 | 4.2 |

‡ MXFP4 weights, tensor-parallel 2 — quantized and multi-GPU, so not directly comparable to the
single-GPU BF16 rows. ¶ 74% of its `rudas_ood` generations hit the length cap, so that cell is a
truncation artefact rather than a measured score; excluding the row, its 13-dataset macro is
0.8708.

Lengths marked ≈ are derived from stored generations using each model's characters-per-token
ratio rather than re-tokenized directly; the method reproduces the three directly measured
lengths to within 3.5%.

The honest summary of this table is that TwIL-LM3 does not lead it. Larger models score higher,
in order of size, and the 120B leads nine of fourteen rows. Two things are worth extracting
anyway. First, TwIL-LM3 improves on its own base while sitting mid-table (0.7339 against 0.7193
on the 10-dataset macro), which is the point of the WiSE-FT stage — in-domain gains without
transfer collapse. Second, it produces the shortest generations of any arm here at 482 tokens
and consequently the most answers per second at 32.9, roughly eight times the 120B's rate.

## Usage

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "webAI-Official/TwIL-LM3"
tok = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id, torch_dtype=torch.bfloat16, device_map="auto"
)

messages = [{"role": "user", "content":
             "Does 'All dogs are mammals. Rex is a dog.' entail 'Rex is a mammal'? "
             "Answer entailment, contradiction, or neutral."}]
inputs = tok.apply_chat_template(
    messages, add_generation_prompt=True,
    return_tensors="pt", return_dict=True,
).to(model.device)

out = model.generate(**inputs, max_new_tokens=2048, do_sample=False)
print(tok.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
```

`return_dict=True` matters on transformers 5.x, where `apply_chat_template` returns a
`BatchEncoding` rather than a bare tensor; the above works on both 4.x and 5.x.

The reported numbers use **greedy decoding** (`do_sample=False`) and a **2048-token** generation
budget. Note that the shipped `generation_config.json` inherits SmolLM3's sampling defaults
(`do_sample=true`, `temperature=0.6`, `top_p=0.95`), so `do_sample=False` must be passed
explicitly to reproduce the evaluation. The model opens a `<think>...</think>` reasoning block
before answering, so a short generation budget truncates reasoning and scores far worse.

### GGUF / llama.cpp

Quantized GGUF builds ship in this repository alongside the safetensors weights. The `smollm3`
architecture is supported by llama.cpp, and the chat template, `<|im_end|>` EOS and BOS are
carried into the GGUF metadata, so chat mode works without extra flags.

| file | quant | size | bits/weight | notes |
|---|---|---:|---:|---|
| `TwIL-LM3-Q4_K_M.gguf` | Q4_K_M | 1.78 GiB | 4.96 | recommended default; runs on CPU or 4 GB of VRAM |
| `TwIL-LM3-Q5_K_M.gguf` | Q5_K_M | 2.06 GiB | 5.74 | a little more headroom than Q4_K_M |
| `TwIL-LM3-Q6_K.gguf` | Q6_K | 2.35 GiB | 6.56 | close to Q8_0 quality at two-thirds the size |
| `TwIL-LM3-Q8_0.gguf` | Q8_0 | 3.05 GiB | 8.50 | near-lossless, for quality-sensitive use |
| `TwIL-LM3-F16.gguf` | F16 | 5.73 GiB | 16.00 | unquantized, for requantization or reference runs |

```bash
llama-cli -m TwIL-LM3-Q4_K_M.gguf -cnv --temp 0 -n 2048
```

Two things matter for reproducing the scores above under llama.cpp. Pass `--temp 0`, because the
evaluation is greedy while the packaged sampling defaults are not. And leave the generation
budget large — 2048 tokens or more — since the model emits a `<think>` block before answering
and a short budget truncates it, which costs far more accuracy than the quantization does.

F16 and Q8_0 were produced directly by `convert_hf_to_gguf.py` from the released bf16 weights; the
K-quants (Q4_K_M, Q5_K_M, Q6_K) were quantized from the F16 build with `llama-quantize`, without
an importance matrix. All five were smoke-tested for load and generation on CPU. Note that F16 is
not bit-identical to the released weights: bf16 and f16 carry the same 16 bits but trade exponent
range against mantissa precision, so the conversion is a narrowing one, in practice negligible
for inference.

The published Track A and Track B numbers were measured on the **bf16** weights through vLLM, not
on any of these GGUF builds, so expect small deviations — most likely at Q4_K_M — that have not
been quantified here.

## How it was built

Four stages on top of the base model:

1. **LoRA supervised fine-tuning** on a synthetic formal-logic corpus covering the Track A
   objectives (first-order-logic translation, entailment labelling, semantic parsing, Lean
   formalisation and critique, procedural reasoning, rule induction).
2. **Checkpoint fusion** — parameter-space averaging of intermediate SFT checkpoints selected
   by a diversity probe, rather than taking the final checkpoint.
3. **WiSE-FT interpolation** toward the pretrained base, `W = (1 − λ)·W_base + λ·W_finetuned`
   with **λ = 0.25** — i.e. only a quarter of the fine-tuned delta is retained. λ was chosen by
   constrained optimisation: maximise in-domain score subject to minimal degradation on held-out
   benchmarks. This conservative λ is the direct reason held-out capability survives.
4. **MGPO** — entropy-weighted GRPO reinforcement learning against a programmatic verifier, with
   partial credit for loose matches and token-F1 so that all-fail prompt groups still produce
   gradient. Published checkpoint is **step 2071**.

A sibling arm that skipped stage 3's conservative interpolation scores considerably higher
in-domain (macro gate 0.515) but gives back roughly twelve points of held-out capability. This
release is the balanced point of that trade; the other was not published.

## Limitations and caveats

**Truncation.** At a 2048-token budget, 4.4% of Track A generations hit the cap — better than
the base's 17.4%, but still above the 2% threshold our protocol requires to mark a comparison
`rankable`. The Track A macro gate should therefore be read as indicative rather than exact.
Because a truncated response scores zero regardless of reasoning quality, both numbers are
pessimistic, and the base substantially more so — meaning the true Track A gap is probably
narrower than +0.086.

**Scope.** Tuned for formal logic. The Track B suite does not cover code generation or tool use
(HumanEval, LiveCodeBench and BFCL were not run for this model or its base), so this release
makes no claim about those.

**Not a chat model.** It was optimised against automatic verifiers on logic tasks. It has had no
safety tuning beyond whatever the base model carries, and no instruction-following alignment
work — IFEval regressed slightly.

**Failed consolidation stage.** A post-RL self-distillation round (SDFT) was attempted and made
both tracks worse at every budget tried (−18% Track A at one epoch on this family). It is not
part of this model.

## Evaluation protocol

- Track A: `n = 200` per objective, greedy (`temperature = 0`), `max_new_tokens = 2048`, one
  retry at 4096 for truncated rows, `max_seq_len = 8192`, seed 42.
- Track B: 300 examples per task, greedy, `max_gen_toks = 4096`, `max_model_len = 8192`,
  `repetition_penalty = 1.0`, chat template applied, vLLM backend.
- Both tracks use the same protocol for the model and its base, in a paired run over identical
  sampled rows.

`repetition_penalty = 1.0` is load-bearing. A 1.1 penalty produced apparent 20-point swings on
Track B that were pure decoding artefact; the decoding kwargs are hashed into the protocol
identity so a mismatched runner fails loudly instead of quietly producing a different number.

## Relationship to TwIL-LM

[**TwIL-LM2**](https://huggingface.co/webAI-Official/TwIL-LM) is the 1.7B member of this family, built
from SmolLM2 by the same pipeline. It reaches a higher in-domain score relative to its own base —
and leads every arm we have measured on Track A strict-7, at any size — but it gives back
held-out capability; this model is the one that improves both. Both repositories now ship full
merged models on `main`, loaded directly with `AutoModelForCausalLM`; the original LoRA-adapter
release is archived on that repository's `TwIL-LM1` branch.

## License and attribution

Released under the **webAI Non-Commercial License ver. 1.0** — see `LICENSE.md` in this
repository.

The base model, [`HuggingFaceTB/SmolLM3-3B`](https://huggingface.co/HuggingFaceTB/SmolLM3-3B),
is Apache 2.0; its licence text is retained as `apache-2.0-LICENSE.txt` and all credit for the
base model goes to the HuggingFaceTB team. Apache 2.0 permits distributing derivative works
under different terms provided attribution is preserved, which is what the pair of licence files
in this repository does.
