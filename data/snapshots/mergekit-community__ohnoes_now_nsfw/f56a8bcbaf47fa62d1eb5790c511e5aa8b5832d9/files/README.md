---
base_model:
- FreedomIntelligence/HuatuoGPT-o1-8B
- Blackroot/Llama-3-LongStory-LORA
- FreedomIntelligence/HuatuoGPT-o1-8B
- vincentyandex/lora_llama3_chunked_novel_bs128
- FreedomIntelligence/HuatuoGPT-o1-8B
- eeeebbb2/3aff0ea7-4262-4abb-97b1-1879f340d32e
- FreedomIntelligence/HuatuoGPT-o1-8B
- grimjim/Llama-3-Instruct-abliteration-LoRA-8B
- FreedomIntelligence/HuatuoGPT-o1-8B
- ResplendentAI/Llama3_RP_ORPO_LoRA
- FreedomIntelligence/HuatuoGPT-o1-8B
- surya-narayanan/professional_psychology
- FreedomIntelligence/HuatuoGPT-o1-8B
- surya-narayanan/human_sexuality
library_name: transformers
tags:
- mergekit
- merge

---
# merge

This is a merge of pre-trained language models created using [mergekit](https://github.com/cg123/mergekit).

## Merge Details
### Merge Method

This model was merged using the [Model Stock](https://arxiv.org/abs/2403.19522) merge method using [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [grimjim/Llama-3-Instruct-abliteration-LoRA-8B](https://huggingface.co/grimjim/Llama-3-Instruct-abliteration-LoRA-8B) as a base.

### Models Merged

The following models were included in the merge:
* [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [Blackroot/Llama-3-LongStory-LORA](https://huggingface.co/Blackroot/Llama-3-LongStory-LORA)
* [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [vincentyandex/lora_llama3_chunked_novel_bs128](https://huggingface.co/vincentyandex/lora_llama3_chunked_novel_bs128)
* [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [eeeebbb2/3aff0ea7-4262-4abb-97b1-1879f340d32e](https://huggingface.co/eeeebbb2/3aff0ea7-4262-4abb-97b1-1879f340d32e)
* [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [ResplendentAI/Llama3_RP_ORPO_LoRA](https://huggingface.co/ResplendentAI/Llama3_RP_ORPO_LoRA)
* [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [surya-narayanan/professional_psychology](https://huggingface.co/surya-narayanan/professional_psychology)
* [FreedomIntelligence/HuatuoGPT-o1-8B](https://huggingface.co/FreedomIntelligence/HuatuoGPT-o1-8B) + [surya-narayanan/human_sexuality](https://huggingface.co/surya-narayanan/human_sexuality)

### Configuration

The following YAML configuration was used to produce this model:

```yaml
models:   
  - model: FreedomIntelligence/HuatuoGPT-o1-8B+eeeebbb2/3aff0ea7-4262-4abb-97b1-1879f340d32e
  - model: FreedomIntelligence/HuatuoGPT-o1-8B+surya-narayanan/professional_psychology
  - model: FreedomIntelligence/HuatuoGPT-o1-8B+Blackroot/Llama-3-LongStory-LORA
  - model: FreedomIntelligence/HuatuoGPT-o1-8B+ResplendentAI/Llama3_RP_ORPO_LoRA
  - model: FreedomIntelligence/HuatuoGPT-o1-8B+vincentyandex/lora_llama3_chunked_novel_bs128  
  - model: FreedomIntelligence/HuatuoGPT-o1-8B+surya-narayanan/human_sexuality 
merge_method: model_stock
base_model: FreedomIntelligence/HuatuoGPT-o1-8B+grimjim/Llama-3-Instruct-abliteration-LoRA-8B
dtype: bfloat16
```
