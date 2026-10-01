---
license: other
license_name: nvidia-license
license_link: https://huggingface.co/nvidia/LocateAnything-3B
base_model: nvidia/LocateAnything-3B
tags:
- locate-anything.cpp
- ggml
- gguf
- object-detection
- open-vocabulary-detection
- visual-grounding
- localai
pipeline_tag: object-detection
library_name: gguf
---

# locate-anything.cpp - GGUF

GGUF builds of [`nvidia/LocateAnything-3B`](https://huggingface.co/nvidia/LocateAnything-3B)
for **[locate-anything.cpp](https://github.com/mudler/locate-anything.cpp)** - a C++/ggml
inference engine for open-vocabulary detection / visual grounding, no Python at inference time.

**Brought to you by the [LocalAI](https://github.com/mudler/LocalAI) team.**

The detections are the same as the official PyTorch implementation (the engine is
parity-gated against it), and it runs faster - on CPU and GPU.

## Files

| File | Bits (LM) | Size | Notes |
| ---- | --------- | ---- | ----- |
| `locate-anything-f16.gguf`  | f16  | ~9.2 GB | LM matmuls in f16, everything else f32 |
| `locate-anything-q8_0.gguf` | q8_0 | ~6.3 GB | near-lossless; **box-identical** to f32 - recommended |
| `locate-anything-q6_k.gguf` | q6_k | ~5.5 GB | box-identical to f32 |
| `locate-anything-q5_k.gguf` | q5_k | ~5.1 GB | sub-pixel box drift |
| `locate-anything-q4_k.gguf` | q4_k | ~4.7 GB | smallest; sub-pixel box drift |

The full-precision `f32` GGUF (~15 GB) is reproducible from the HF weights with
`scripts/convert_locateanything_to_gguf.py` in the repo.

## Performance

Same detections as the official model, faster. Full methodology, the warm/median setup,
parity checks, and more images are in the repo's
[`benchmarks/BENCHMARK.md`](https://github.com/mudler/locate-anything.cpp/blob/master/benchmarks/BENCHMARK.md).

### Quantization (CPU, Ryzen 9 9950X3D)

Slow-mode inference on the 448 fixture; `vs official` divides the official PyTorch **f32**
time (23.65 s) by each. Only the Qwen2 LM matmuls are quantized, so box parity is preserved
through q6_k:

| dtype | size | infer | vs official f32 | boxes |
| ----- | ---- | ----- | --------------- | ----- |
| f16   | 9.15 GB | 13.68 s | 1.7× | identical |
| q8_0  | 6.26 GB | 6.07 s  | **3.9×** | identical |
| q6_k  | 5.51 GB | 5.77 s  | **4.1×** | identical |
| q5_k  | 5.10 GB | 5.11 s  | **4.6×** | sub-pixel |
| q4_k  | 4.72 GB | 4.29 s  | **5.5×** | sub-pixel |

![quantization size vs speedup](quant_tradeoff.png)

### GPU (NVIDIA GB10, vs the official bf16 model)

Run against the official model exactly as its model card documents (bf16), greedily, on one
GB10 GPU. Precision-matched (our **f16** vs its bf16) ours is **~1.7×** faster; the
recommended **q8_0** build (box-identical) is **~1.9-2.1×**:

![GB10 GPU speedup vs official bf16](gpu_speedup.png)

## Quantization policy

Only the Qwen2 language-model matmuls (`attn_{q,k,v,o}`, `ffn_{gate,up,down}`, `lm.output`)
are quantized. The MoonViT vision tower, the projector, all norms and biases, and the two
host-read f32 tensors (`lm.tok_embd`, `vit.pos_emb`) stay **f32** - so the parity-sensitive
vision path is untouched. q8_0/q6_k are box-identical; lower bit-widths trade a little box
precision for size.

## Usage

```sh
# build the CLI (see the repo README), then:
locate-anything-cli detect \
    --model locate-anything-q8_0.gguf \
    --input image.jpg \
    --prompt "Locate all the instances that matches the following description: person</c>car." \
    --annotated out.png
# -> {"detections":[{"label":"person","box":[...]}, ...]}  + an annotated PNG
```

Decode modes: `--mode hybrid` (default), `slow`, `fast`. GPU: build with `-DLA_GGML_CUDA=ON`
and run with `LA_DEVICE=` (auto-GPU). Separate categories in the prompt with `</c>`.

## License

The model weights are NVIDIA's, distributed under
[NVIDIA's license](https://huggingface.co/nvidia/LocateAnything-3B); this repository
redistributes them in GGUF form for use with locate-anything.cpp (MIT).
