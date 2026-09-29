---
base_model:
- Qwen/Qwen2.5-1.5B-Instruct
- Qwen/Qwen2.5-Math-1.5B-Instruct
- Qwen/Qwen2.5-Coder-1.5B-Instruct
library_name: transformers
tags:
- mergekit
- merge

---
# merge

This is a merge of pre-trained language models created using [mergekit](https://github.com/cg123/mergekit).

## Merge Details
### Merge Method

This model was merged using the [TIES](https://arxiv.org/abs/2306.01708) merge method using [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) as a base.

### Models Merged

The following models were included in the merge:
* [Qwen/Qwen2.5-Math-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B-Instruct)
* [Qwen/Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct)

### Configuration

The following YAML configuration was used to produce this model:

```yaml
models:
  - model: Qwen/Qwen2.5-Coder-1.5B-Instruct
    parameters:
      density: 1.0
      weight: 1.0
  - model: Qwen/Qwen2.5-Math-1.5B-Instruct
    parameters:
      density: 1.0
      weight: 1.0
merge_method: ties
base_model: Qwen/Qwen2.5-1.5B-Instruct
parameters:
  normalize: true
  int8_mask: true
dtype: float16

```
