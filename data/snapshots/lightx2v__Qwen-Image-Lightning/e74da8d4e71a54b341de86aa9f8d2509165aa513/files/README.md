---
license: apache-2.0
language:
- en
- zh
base_model:
- Qwen/Qwen-Image
pipeline_tag: text-to-image
tags:
- Qwen-Image
- distillation
- LoRA
- lora
library_name: diffusers
---

Please refer to [Qwen-Image-Lightning github](https://github.com/ModelTC/Qwen-Image-Lightning/) to learn how to use the models.

use with diffusers 🧨:

make sure to install diffusers from `main` (`pip install git+https://github.com/huggingface/diffusers.git`)
```
from diffusers import DiffusionPipeline, FlowMatchEulerDiscreteScheduler
import torch 
import math

# From https://github.com/ModelTC/Qwen-Image-Lightning/blob/342260e8f5468d2f24d084ce04f55e101007118b/generate_with_diffusers.py#L82C9-L97C10
scheduler_config = {
    "base_image_seq_len": 256,
    "base_shift": math.log(3),  # We use shift=3 in distillation
    "invert_sigmas": False,
    "max_image_seq_len": 8192,
    "max_shift": math.log(3),  # We use shift=3 in distillation
    "num_train_timesteps": 1000,
    "shift": 1.0,
    "shift_terminal": None,  # set shift_terminal to None
    "stochastic_sampling": False,
    "time_shift_type": "exponential",
    "use_beta_sigmas": False,
    "use_dynamic_shifting": True,
    "use_exponential_sigmas": False,
    "use_karras_sigmas": False,
}
scheduler = FlowMatchEulerDiscreteScheduler.from_config(scheduler_config)
pipe = DiffusionPipeline.from_pretrained(
    "Qwen/Qwen-Image", scheduler=scheduler, torch_dtype=torch.bfloat16
).to("cuda")
pipe.load_lora_weights(
    "lightx2v/Qwen-Image-Lightning", weight_name="Qwen-Image-Lightning-8steps-V1.0.safetensors"
)

prompt = "a tiny astronaut hatching from an egg on the moon, Ultra HD, 4K, cinematic composition."
negative_prompt = " "
image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    width=1024,
    height=1024,
    num_inference_steps=8,
    true_cfg_scale=1.0,
    generator=torch.manual_seed(0),
).images[0]
image.save("qwen_fewsteps.png")
```