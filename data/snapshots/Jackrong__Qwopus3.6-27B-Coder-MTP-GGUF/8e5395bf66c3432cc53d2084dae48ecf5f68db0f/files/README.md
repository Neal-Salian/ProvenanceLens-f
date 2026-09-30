---
library_name: transformers
base_model:
- Jackrong/Qwopus3.6-27B-v2
tags:
- gguf
- llama.cpp
- image-text-to-text
- vision
- multimodal
- text-generation-inference
- transformers
- unsloth
- conversational
- qwen3_6
- reasoning
- chain-of-thought
- lora
- sft
- agent
- tool-use
- function-calling
- coder
license: apache-2.0
language:
- en
- zh
- es
- ru
- ja
pipeline_tag: image-text-to-text
datasets:
- Jackrong/Claude-opus-4.6-TraceInversion-9000x
- Jackrong/Claude-opus-4.7-TraceInversion-5000x
- lambda/hermes-agent-reasoning-traces
---
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #cbd5e1; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05); overflow: hidden; background: #ffffff; margin-bottom: 30px;">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #4c1d95 100%); padding: 24px; color: white;">
  <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
  <h1 style="margin: 0; font-size: 26px; font-weight: 800; display: flex; align-items: center; gap: 12px; color: white; border: none;">🪐 Qwopus-3.6-27B-Coder</h1>
  <span style="background: #10b981; color: white; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px;">Coder SFT Release</span>
  </div>
  <p style="margin: 8px 0 0 0; font-size: 14px; color: #ddd6fe; font-weight: 500;">Agentic Coding &amp; Tool-Use Reasoning Model Fine-Tuned on Qwopus3.6-27B-v2</p>
  </div>
  <div style="display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 24px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
  <span style="background: #f3e8ff; color: #6b21a8; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #e9d5ff;">🧬 Trace Inversion & Negentropy</span>
  <span style="background: #dbeafe; color: #1e40af; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #bfdbfe;">🧠 27B Dense Model</span>
  <span style="background: #e0f2fe; color: #0369a1; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #bae6fd;">⚡ Agentic Coding</span>
  <span style="background: #d1fae5; color: #065f46; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #a7f3d0;">🛠️ Tool Calling & Agent</span>
  <span style="background: #dcfce7; color: #166534; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid #bbf7d0;">🏆 SWE-bench Verified: 67.0% (off-thinking)</span>
  </div>
  <div style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
  <div style="background: #f5f3ff; border-left: 5px solid #7c3aed; padding: 16px; border-radius: 0 8px 8px 0;">
  <h3 style="margin: 0 0 8px 0; font-size: 15px; color: #6d28d9; font-weight: 700; display: flex; align-items: center; gap: 6px;"><span>💡</span> What is Qwopus-3.6-27B-Coder?</h3>
  <p style="margin: 0; font-size: 13px; color: #334155; line-height: 1.6;">🪐 <b>Qwopus-3.6-27B-Coder</b> is a reasoning-enhanced agentic coding model built on top of <b>Qwopus3.6-27B-v2</b>. It inherits the powerful reasoning foundation of the v2 base — which achieved <b>87.43% MMLU-Pro</b> and <b>75.25% SWE-bench Verified</b> — and further specializes it for agentic code generation, structured tool calling, debugging, and instruction-following in developer workflows. The model is designed to excel at repository-level coding tasks, multi-turn tool orchestration, and complex logical reasoning under realistic agent environments.</p>
  </div>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 10px;">
  <div style="border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; background: #fafafa; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-weight: 700; color: #6b21a8; font-size: 12px; display: block; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">🧩 Agentic Coding</span>
  <span style="font-size: 13px; color: #4b5563; line-height: 1.5;">Optimized for repository-level coding, debugging, patch generation, and structured multi-step development workflows.</span>
  </div>
  <div style="border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; background: #fafafa; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-weight: 700; color: #6b21a8; font-size: 12px; display: block; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">🛠️ Tool Calling</span>
  <span style="font-size: 13px; color: #4b5563; line-height: 1.5;">Learns from real agent trajectories with tool definitions, tool calls, and environment feedback for robust multi-turn execution.</span>
  </div>
  <div style="border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; background: #fafafa; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-weight: 700; color: #6b21a8; font-size: 12px; display: block; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">🧬 Trace Inversion</span>
  <span style="font-size: 13px; color: #4b5563; line-height: 1.5;">Inherits the full Qwopus training recipe with reconstructed step-by-step reasoning trajectories from Claude Opus.</span>
  </div>
  <div style="border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; background: #fafafa; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-weight: 700; color: #6b21a8; font-size: 12px; display: block; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">🚀 27B Scale</span>
  <span style="font-size: 13px; color: #4b5563; line-height: 1.5;">Dense 27B parameters with native long-context support, delivering deep reasoning with practical single-GPU deployability.</span>
  </div>
  </div>
  </div>
</div>

> [!WARNING]
> **Community Release Notice**: Qwopus-3.6-27B-Coder is an experimental community release intended for research, evaluation, and agent workflow exploration. It has not undergone full safety evaluation or broad general-domain benchmarking.

> [!IMPORTANT]
> **Benchmark Status**: The first completed benchmark is SWE-bench Verified full 500 in **thinking-off / no-thinking mode**, where the Q5_K_M 27B GGUF run resolved **335/500 = 67.0%**. Other benchmark suites remain pending and will be updated as testing completes.

---

## 💡 1. Base Model, Training Stack & Collaboration

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; flex-direction: column; gap: 20px; margin-bottom: 30px;">

  <!-- Card 1.1: Base Model Overview -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧠</span> 1.1 Base Model: Qwopus3.6-27B-v2
  </div>
  <div style="padding: 16px;">
  <p style="margin: 0 0 16px 0; font-size: 13px; color: #334155; line-height: 1.6;">
  <b>Qwopus3.6-27B-v2</b> is a reasoning-enhanced dense language model built on <b>Qwen3.6-27B</b>. Through a multi-stage curriculum learning pipeline and Trace Inversion augmentation, it achieves strong performance across knowledge, coding, and reasoning benchmarks. This coder variant inherits that foundation and extends it with specialized coding and tool-use data.
  </p>
  <table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 13px;">
  <thead>
  <tr style="background: rgba(124, 58, 237, 0.05);">
  <th style="padding: 8px 10px; border-bottom: 2px solid #7c3aed; text-align: left; color: #7c3aed; font-weight: bold; width: 30%;">Attribute</th>
  <th style="padding: 8px 10px; border-bottom: 2px solid #7c3aed; text-align: left;">Specifications &amp; Details</th>
  </tr>
  </thead>
  <tbody>
  <tr>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold;">🧠 Architecture</td>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Dense Transformer / 27 Billion Parameters</td>
  </tr>
  <tr>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold;">🏢 Base Developer</td>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Alibaba Cloud (DAMO Academy) — Qwen3.6-27B</td>
  </tr>
  <tr>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold;">🎯 Primary Focus</td>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Agentic coding, tool-use stability, code debugging, structured instruction following, repository-level tasks</td>
  </tr>
  <tr>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold;">🧬 Distillation Strategy</td>
  <td style="padding: 8px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Trace Inversion + high-quality agent trajectories + curriculum SFT</td>
  </tr>
  </tbody>
  </table>
  </div>
  </div>

  <!-- Card 1.2: Hardware Cooperation -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #10b981 0%, #047857 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧪</span> 1.2 Hardware Cooperation &amp; Joint Collaboration
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  This project is built in close collaboration and joint effort with engineer <b>Kyle Hessling</b>, whose hardware infrastructure and training support made stable 27B-scale fine-tuning and evaluation possible.
  <div style="margin-top: 10px; display: flex; align-items: center; gap: 6px;">
  <span>👉</span>
  <span>You can follow him for hardware and model training updates on X / Twitter: <a href="https://x.com/KyleHessling1" target="_blank" style="color: #047857; text-decoration: none; font-weight: 700;">@KyleHessling1</a></span>
  </div>
  </div>
  </div>

  <!-- Card 1.3: Fine-tuning Framework -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🦥</span> 1.3 Fine-Tuning Framework (Unsloth)
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  The model training workflow is accelerated and memory-optimized with <b>Unsloth</b>. Special thanks to the Unsloth team for making efficient large-model fine-tuning accessible.
  <div style="margin-top: 10px; display: flex; align-items: center; gap: 6px;">
  <span>👉</span>
  <span>Documentation and fine-tuning guidance: <a href="https://unsloth.ai/docs" target="_blank" style="color: #7c3aed; text-decoration: none; font-weight: 700;">unsloth.ai/docs</a></span>
  </div>
  </div>
  </div>

  <!-- Card 1.4: MTP Variant -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>⚡</span> 1.4 MTP Variant: Faster Speculative Decoding
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.7;">
  A <b>Multi-Token Prediction (MTP)</b> variant of this model is also available, featuring auxiliary prediction heads (<code>draft=2</code>) for speculative decoding. Based on the Qwopus3.6-27B-v2-MTP benchmark, the MTP variant achieved <b>~1.66x speedup</b> over standard decoding with preserved accuracy. See the <a href="https://huggingface.co/Jackrong/Qwopus3.6-27B-v2-MTP" target="_blank" style="color: #0284c7; text-decoration: none; font-weight: 700;">Qwopus3.6-27B-v2-MTP</a> model card for detailed MTP performance analysis.
  <div style="margin-top: 10px; display: flex; align-items: center; gap: 6px; color: #475569; font-weight: 500;">
  <span>🌟</span><span>The custom MTP heads processing pipeline is open-sourced in <a href="https://github.com/R6410418/Jackrong-llm-finetuning-guide/tree/main/qwen-mtp-gguf" target="_blank" style="color: #0284c7; text-decoration: none; font-weight: 700;">qwen-mtp-gguf</a>. If you find this toolkit helpful, please consider leaving a star on GitHub!</span>
  </div>
  </div>
  </div>
</div>

---

## 📖 2. Background & Motivation

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; flex-direction: column; gap: 20px; margin-bottom: 30px;">

  <!-- Card 2.1: Why a 27B Coder Model -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🎯</span> 2.1 Why a 27B Coder Model?
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  The Qwopus coder line has demonstrated strong results at the 4B and 9B scales. The 27B coder variant represents a significant leap in reasoning depth, code generation quality, and tool-use robustness. At 27B parameters, the model has sufficient capacity to internalize complex repository structures, multi-file dependencies, and nuanced tool-calling patterns — while remaining deployable on a single GPU (e.g., RTX 5090). This scale bridges the gap between compact local models and expensive API-based solutions, making it suitable for production agentic coding workflows.
  </div>
  </div>

  <!-- Card 2.2: Trace Inversion & Agent Behavior -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧬</span> 2.2 Trace Inversion &amp; Agent Behavior
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  Commercial and frontier models often expose only compressed reasoning summaries. Qwopus-style training uses <b>Trace Inversion</b> to reconstruct these compressed "Reasoning Bubbles" into fuller learnable reasoning traces. For coding, this is paired with agent trajectories that include tool definitions, tool calls, and real feedback, teaching the model to reason through interactive work rather than only produce static answers.

  <br><br>This model integrates:
  <ul>
  <li><b>claude-opus-4.6-traceInversion-9000x</b>: 9,000 high-value, fully reconstructed step-by-step reasoning trajectories.</li>
  <li><b>claude-opus-4.7-traceInversion-5000x</b>: 5,000 complex multi-turn logic and mathematics samples optimized for negative entropy reconstruction.</li>
  <li><b>lambda/hermes-agent-reasoning-traces</b>: ~10,000 high-quality multi-turn tool-calling trajectories from GLM-5.1 and kimi-4.6 models.</li>
  </ul>
  </div>
  </div>

  <!-- Card 2.3: Training Data Details -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>📦</span> 2.3 Special Dataset: Trace Inversion &amp; Agent Traces
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  <b>Trace Inversion:</b> Uses a specialized logical reconstructor, <a href="https://huggingface.co/Jackrong/Trace-Inverter-4B" target="_blank" style="color: #0369a1; text-decoration: none; font-weight: bold;">Trace-Inverter-4B</a>, to reverse-engineer compressed reasoning bubbles into complete, step-by-step learnable CoT chains. This approach addresses the <b>"Information Entropy Trap"</b> — where direct imitation of compressed summaries leads to reasoning fractures — by ensuring the model learns continuous, rigorous logical derivations.

  <br><br>
  <b>Agent Traces (lambda/hermes-agent-reasoning-traces):</b> Each sample contains real multi-turn tool execution results (not fabricated outputs), with step-by-step reasoning inside <code>&lt;think&gt;</code> tags. Coverage includes:
  <ul>
  <li><b>Terminal &amp; Coding:</b> Script writing, debugging, environment configuration</li>
  <li><b>Repository Tasks:</b> Bug fixing, refactoring, code review</li>
  <li><b>Browser Automation:</b> Web navigation, scraping, form filling</li>
  <li><b>Agent Tools:</b> Memory persistence, task delegation, skill management</li>
  </ul>
  </div>
  </div>
</div>

---

## 📊 3. Performance Benchmarks

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #cbd5e1; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05); overflow: hidden; background: #ffffff; margin-bottom: 30px;">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 20px; color: white;">
  <h3 style="margin: 0; font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 8px; color: white; border: none;">📊 Evaluation &amp; Performance Metrics</h3>
  <p style="margin: 4px 0 0 0; font-size: 13px; color: #ddd6fe;">First completed result: SWE-bench Verified full 500, evaluated in no-thinking mode for fast local agentic coding.</p>
  </div>

  <div style="padding: 24px; display: flex; flex-direction: column; gap: 24px;">

  <!-- No-thinking highlight banner -->
  <div style="background: #f5f3ff; border: 1px solid #ddd6fe; border-left: 5px solid #7c3aed; border-radius: 0 8px 8px 0; padding: 16px 20px; display: flex; gap: 12px; align-items: flex-start;">
  <span style="font-size: 24px;">⚡</span>
  <div>
  <span style="font-weight: 800; font-size: 14px; color: #5b21b6; display: block; margin-bottom: 4px;">No-Thinking SWE-bench Result</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.6;">This benchmark was intentionally run with <b>thinking disabled</b>. The goal is to show the model's practical coding ability when used as a fast local agent, without relying on long visible reasoning traces. On an RTX 5090 with MTP enabled, the model runs at approximately <b>100 tokens/sec</b>, making this result especially relevant for interactive development workflows.</span>
  </div>
  </div>

  <!-- Key Stats Grid -->
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px;">
  <div style="border: 1px solid #ddd6fe; padding: 16px; border-radius: 10px; background: #f5f3ff; text-align: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-size: 11px; font-weight: 800; color: #6d28d9; text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.5px;">SWE-bench Verified</span>
  <span style="font-size: 30px; font-weight: 900; color: #5b21b6; display: block; line-height: 1;">67.0%</span>
  <span style="font-size: 12px; color: #64748b; font-weight: 600;">335 / 500 resolved</span>
  </div>
  <div style="border: 1px solid #bae6fd; padding: 16px; border-radius: 10px; background: #f0f9ff; text-align: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-size: 11px; font-weight: 800; color: #0369a1; text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.5px;">Inference Mode</span>
  <span style="font-size: 24px; font-weight: 900; color: #0369a1; display: block; line-height: 1;">Thinking Off</span>
  <span style="font-size: 12px; color: #64748b; font-weight: 600;">no visible CoT required</span>
  </div>
  <div style="border: 1px solid #bbf7d0; padding: 16px; border-radius: 10px; background: #f0fdf4; text-align: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-size: 11px; font-weight: 800; color: #047857; text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.5px;">Local Throughput</span>
  <span style="font-size: 30px; font-weight: 900; color: #047857; display: block; line-height: 1;">~100 t/s</span>
  <span style="font-size: 12px; color: #64748b; font-weight: 600;">RTX 5090 + MTP</span>
  </div>
  <div style="border: 1px solid #fed7aa; padding: 16px; border-radius: 10px; background: #fff7ed; text-align: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
  <span style="font-size: 11px; font-weight: 800; color: #c2410c; text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.5px;">Evaluation Build</span>
  <span style="font-size: 24px; font-weight: 900; color: #c2410c; display: block; line-height: 1;">Q5_K_M</span>
  <span style="font-size: 12px; color: #64748b; font-weight: 600;">27B GGUF quant</span>
  </div>
  </div>

  <!-- Test Configuration Note -->
  <div style="background: #f8fafc; border-left: 4px solid #475569; border-radius: 0 8px 8px 0; padding: 12px 16px; font-size: 13px; color: #0f172a; line-height: 1.65;">
  <b>Evaluation setup:</b> SWE-bench Verified <b>full 500</b>, Qwopus-3.6-27B-Coder <b>Q5_K_M</b> GGUF, <b>thinking-off / no-thinking mode</b>. Final score: <b>335/500 = 67.0%</b>.
  </div>

  <!-- Main SWE-bench Result -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 12px 16px; color: white; font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>💻</span> 3.1 SWE-bench Verified: Full 500 No-Thinking Result
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  <p style="margin: 0 0 12px 0;">SWE-bench Verified measures whether a model can solve real GitHub issues by editing repository code and passing the hidden tests. In this run, Qwopus-3.6-27B-Coder solved <b>335 out of 500</b> verified tasks while running in <b>no-thinking mode</b>, prioritizing direct action quality and local speed over long explicit reasoning.</p>
  <table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 13px;">
  <thead>
  <tr style="background: rgba(124, 58, 237, 0.06);">
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; color: #6d28d9; font-weight: 800;">Metric</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 800;">Result</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 800;">Notes</th>
  </tr>
  </thead>
  <tbody>
  <tr>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Final score</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #5b21b6;">335/500 = 67.0%</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Full SWE-bench Verified 500-task split</td>
  </tr>
  <tr>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Mode</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #0369a1;">Thinking off</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">No long visible chain-of-thought during evaluation</td>
  </tr>
  <tr>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Quantization</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #c2410c;">Q5_K_M GGUF</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Local 27B quantized deployment</td>
  </tr>
  <tr>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Throughput</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #047857;">~100 tokens/sec</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Observed on RTX 5090 with MTP enabled</td>
  </tr>
  </tbody>
  </table>
  </div>
  </div>

  <!-- Repository Breakdown -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 12px 16px; border-bottom: 1px solid #cbd5e1; font-weight: 800; font-size: 14px; color: #1e293b; display: flex; align-items: center; gap: 8px;">
  <span>🧩</span> 3.2 Repository-Level Breakdown
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  <p style="margin: 0 0 12px 0;">The result is strongest on practical library-maintenance tasks such as scikit-learn, xarray, requests, and Django, while also showing solid coverage on symbolic mathematics, test infrastructure, documentation tooling, and plotting libraries.</p>
  <div style="width: 100%; display: grid; grid-template-columns: minmax(220px, 2fr) minmax(120px, 1fr) minmax(120px, 1fr); border: 1px solid rgba(203,213,225,0.7); border-radius: 10px; overflow: hidden; font-family: inherit; font-size: 13px;">
  <div style="background: rgba(14, 165, 233, 0.07); padding: 9px 10px; border-bottom: 2px solid #0ea5e9; color: #0369a1; font-weight: 800;">Repository</div>
  <div style="background: rgba(14, 165, 233, 0.07); padding: 9px 10px; border-bottom: 2px solid #0ea5e9; font-weight: 800;">Resolved</div>
  <div style="background: rgba(14, 165, 233, 0.07); padding: 9px 10px; border-bottom: 2px solid #0ea5e9; font-weight: 800;">Rate</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">scikit-learn</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">27/32</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #047857;">84%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">pydata/xarray</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">18/22</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #047857;">82%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">psf/requests</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">6/8</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #047857;">75%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">django</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">166/231</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #047857;">72%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">sympy</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">48/75</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #6d28d9;">64%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">pytest</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">12/19</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #6d28d9;">63%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">sphinx-doc</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">26/44</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #6d28d9;">59%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">matplotlib</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">20/34</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #6d28d9;">59%</div>
  <div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">astropy</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">9/22</div><div style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #b45309;">41%</div>
  <div style="padding: 9px 10px; font-weight: 700;">pylint</div><div style="padding: 9px 10px;">2/10</div><div style="padding: 9px 10px; font-weight: 800; color: #b45309;">20%</div>
  </div>
  </div>
  </div>

  <!-- Thinking-on comparison table -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #eef2ff 0%, #ede9fe 100%); padding: 12px 16px; border-bottom: 1px solid #cbd5e1; font-weight: 800; font-size: 14px; color: #4c1d95; display: flex; align-items: center; gap: 8px;">
  <span>⚖️</span> 3.3 SWE-bench Verified Reference Comparison
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  <div style="background: #fff7ed; border-left: 4px solid #f97316; border-radius: 0 8px 8px 0; padding: 10px 12px; margin-bottom: 12px; color: #7c2d12;">
  <b>Important comparison note:</b> the reference scores below are from external model reports and are generally <b>thinking-enabled</b> or harness-specific where noted. Qwopus-3.6-27B-Coder is shown here as a <b>no-thinking</b>, quantized local run, so this table should be read as positioning context rather than a strict same-mode leaderboard.
  </div>
  <table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 13px;">
  <thead>
  <tr style="background: rgba(124, 58, 237, 0.06);">
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; color: #6d28d9; font-weight: 800;">Model</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 800;">Thinking Mode</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 800;">SWE-bench Verified</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 800;">Context</th>
  </tr>
  </thead>
  <tbody>
  <tr style="background: #f5f3ff;">
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #5b21b6;">Qwopus-3.6-27B-Coder</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800; color: #0369a1;">Off / No-thinking</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #5b21b6;">67.0</td>
  <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Q5_K_M, RTX 5090 + MTP, ~100 t/s</td>
  </tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">OpenAI GPT-5</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">70.1</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">OpenAI GPT-5 mini</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">59.8</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">OpenAI GPT-5 nano</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">34.8</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">GLM-4.7</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">70.6</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">OpenHands reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">GLM-4.5-Air</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">57.6</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">OpenHands reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Qwen3-Coder-30B-A3B-Instruct (2025-07)</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Off / No-thinking</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">70.3</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">No-thinking reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Claude 4.0 Opus</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">67.6</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Claude 4.5 Opus</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">80.9</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Qwen3.6-27B</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">77.2</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Qwen3.5-397B-A17B</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">76.2</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Qwen3.5-27B</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">75.0</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Qwen3.6-35B-A3B</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">73.4</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 700;">Gemma4-31B</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">On</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">52.0</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-on reference</td></tr>
  <tr><td style="padding: 10px; font-weight: 700;">Gemma4-26B-A4B</td><td style="padding: 10px;">On</td><td style="padding: 10px; font-weight: 800;">17.4</td><td style="padding: 10px;">Thinking-on reference</td></tr>
  </tbody>
  </table>
  </div>
  </div>

  <!-- Kyle live test module -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #0f766e 0%, #0369a1 100%); padding: 12px 16px; color: white; font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🎮</span> 3.4 Live Thinking-Disabled Demo: Boat Survival
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  <p style="margin: 0 0 12px 0;">Kyle Hessling also tested Qwopus-3.6-27B-Coder in a small interactive game environment with thinking disabled. The demo is a practical smoke test for fast decision-making, instruction adherence, and local responsiveness beyond static benchmark tables.</p>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 12px;">
  <a href="https://huggingface.co/spaces/KyleHessling1/Boat-Survival-Thinking-Disabled-Qwopus-3.6-27B-Coder" target="_blank" style="display: block; padding: 12px 14px; border: 1px solid #bae6fd; border-radius: 8px; background: #f0f9ff; color: #0369a1; text-decoration: none; font-weight: 800;">Open the Hugging Face Space</a>
  <a href="https://x.com/KyleHessling1/status/2064449362382758354" target="_blank" style="display: block; padding: 12px 14px; border: 1px solid #bbf7d0; border-radius: 8px; background: #f0fdf4; color: #047857; text-decoration: none; font-weight: 800;">View Kyle's reference post</a>
  </div>
  <a href="https://huggingface.co/spaces/KyleHessling1/Boat-Survival-Thinking-Disabled-Qwopus-3.6-27B-Coder" target="_blank" style="display: block; border: 1px solid #cbd5e1; border-radius: 10px; overflow: hidden; background: #f8fafc; text-decoration: none;">
  <img src="https://cdn-uploads.huggingface.co/production/uploads/66309bd090589b7c65950665/sGQKmrMc6L6guMoaB5_Y2.png" alt="Boat Survival thinking-disabled Qwopus-3.6-27B-Coder demo screenshot" style="width: 100%; display: block; border: 0;" />
  </a>
  </div>
  </div>

  <!-- Interpretation -->
  <div style="background: #ecfdf5; border: 1px solid #bbf7d0; border-left: 5px solid #10b981; border-radius: 0 8px 8px 0; padding: 16px 20px; font-size: 13px; color: #064e3b; line-height: 1.65;">
  <b>Takeaway:</b> The headline is not that this no-thinking local run beats every thinking-enabled frontier reference. The important result is that a quantized 27B local coder can reach <b>67.0%</b> on the full SWE-bench Verified split while staying fast enough for interactive agent loops. This makes Qwopus-3.6-27B-Coder a practical option for developers who want strong repository-level repair performance without paying the latency cost of long reasoning mode.
  </div>

  </div>
</div>

---

## 🗺️ 4. Training & Data Pipeline Overview

The training process fuses **Trace Inversion** data augmentation with a **Three-Stage Curriculum Learning** pipeline. The core engineering focuses on expanding context length gradually while training on reconstructed reasoning traces and real agent trajectories to keep the output format stable.

```text
       [ 🗺️ Trace Inversion: Reconstructing Distillation Workflow ]

  A. Surrogate Model Training (Trace Inverter)
     Open-source Model (GLM-5.1 / DS-V4) ──► Complete Reasoning Chain ──► [ Qwen3-235B Compression ] ──► Reasoning Bubbles
                                              │                                   │
                                              └──────────► [ Training ] ◄─────────┘
                                                   (Base: Qwen3-4B-Instruct)
                                                   (Result: Trace-Inverter-4B)

  B. Inversion Phase: Reconstructing Claude-4.7-Max
     _______________________________________________________
    |                                                       |
    |  Claude-4.7-Max API ──► Compressed Bubbles + Answer   |
    |_______________________________________________________|
                      │
                      ▼
    [ 🧠 Trace-Inverter-4B (Logic Reconstructor) ] ──► Synthetic Deep Reasoning Trace (Learnable CoT)
                      │
                      ▼
    [ 🧩 Data Splicing ] ◄────────── (Original Prompt + Response)
    (Embed reconstructed CoT in <think> tags, splicing with original prompt/response)
                      │
                      ▼
             (Result: claude-opus-4.6/4.7 inverted sets)

  C. Final Coder SFT Curriculum Pipeline
     ___________________________________________
    |                                           |
    |       Base Model (Qwopus3.6-27B-v2)       |
    |___________________________________________|
                      │
                      ▼
    [ 📦 Phase 1: Format Inception ] ──► [ 🛠️ Phase 2: Agent/Coding Expansion ] ──► [ 🚀 Phase 3: Long-Context SFT ]
      ( < 4096 tokens )                     ( 4096 - 8192 tokens )                     ( 8192 - 32K tokens )
      (Stable <think> format)               (Tool traces + coding tasks)               (Long / multi-turn / replay)
                      │                                                                            │
                      └─────────────────────────────┬──────────────────────────────────────────────┘
                                                    ▼
                                   _______________________________________________
                                  |                                               |
                                  |   🌟 Final Model: Qwopus-3.6-27B-Coder        |
                                  |_______________________________________________|
```

> [!NOTE]
> Due to the complex and diverse format of agent trajectory datasets, rigorous cleaning and format standardization were applied to ensure data quality.

---

## 📚 5. Three-Stage Curriculum Learning

To steadily scale reasoning quality under long-context inference, **Qwopus-3.6-27B-Coder** uses a curriculum-style data mixture building on the approach proven in the Qwopus coder line. The model is first stabilized on short, clean reasoning samples, then exposed to complex coding and agent traces, and finally reinforced with longer contexts plus replay data.

<table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <thead>
    <tr style="background: rgba(124, 58, 237, 0.05);">
      <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; color: #7c3aed; font-size: 14px; width: 25%;">Curriculum Stage</th>
      <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-size: 14px; width: 35%;">Focus &amp; Sample Characteristics</th>
      <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-size: 14px;">Strategy Details</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold; font-size: 13px; color: #7c3aed;">📦 Stage 1: Format Inception</td>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-size: 13px;">• Limit context within 4,096 tokens<br>• Emphasize stable reasoning templates</td>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-size: 13px;">Focuses on short-to-medium length, cleanly formatted reasoning samples. The primary goal is to establish reliable structured reasoning output, including stable <code>&lt;think&gt;</code> boundaries, before exposing the model to longer chains.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold; font-size: 13px; color: #7c3aed;">🛠️ Stage 2: Complexity Expansion</td>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-size: 13px;">• Extend length to 4,096 - 8,192 tokens<br>• Introduce higher-difficulty coding and agent samples</td>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-size: 13px;">Gradually increases the ratio of complex reasoning chains, code debugging tasks, and multi-turn tool traces. The model learns to connect reasoning, action selection, and environment feedback.</td>
    </tr>
    <tr>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: bold; font-size: 13px; color: #7c3aed;">🚀 Stage 3: Long-Context SFT</td>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-size: 13px;">• Progressively scale samples up to 32K tokens<br>• Use short-sample replay</td>
      <td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-size: 13px;">Pushes the model toward long-context and multi-turn reasoning while replaying high-quality short samples to reduce instruction-following drift.</td>
    </tr>
  </tbody>
</table>

---

## 🎯 6. Recommended Use Cases & Known Limits

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 30px;">

  <!-- Card 6.1: Good Fits -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #10b981 0%, #047857 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>✅</span> Good Fits
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  Agentic code generation and repository-level debugging, complex tool-call orchestration, structured multi-step reasoning, code review and patch generation, DevOps scripting and automation, and any workflow requiring deep logical reasoning combined with tool execution.
  </div>
  </div>

  <!-- Card 6.2: Known Limits -->
  <div style="border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
  <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 12px 16px; color: white; font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>❌</span> Known Limits
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.6;">
  As a specialized coder model, it has not undergone comprehensive general-domain safety evaluation. Capability decay may occur in non-coding or non-agent tasks. Tool-call behavior depends strongly on prompt format and tool schema consistency.
  </div>
  </div>
</div>

> [!CAUTION]
> **Deployment note**: The model may emit reasoning inside `<think>` and `</think>` tags. Front-end applications and agent frameworks should parse or hide these sections where appropriate. For tool calling, ensure the prompt format and system prompt match the training data configuration to activate agent capabilities.

---

## ⚠️ 7. Training & Deployment Notes

> [!CAUTION]
> **Compatibility Notes**
> - **Tool Calling Format**: To activate the model's agent capabilities, ensure the prompt format and system prompt include appropriate tool definitions and match the training data format.
> - **Reasoning Output Extraction**: The model's thinking process is wrapped in `<think>` and `</think>` tags. Front-end applications may need to parse and hide these tags.

---

## 📋 8. Benchmark Progress

The first completed evaluation is the no-thinking SWE-bench Verified run reported above. Additional local agentic benchmarks remain pending and will be added after testing.

| Benchmark | Status | Result / Reference |
|-----------|--------|-------------------|
| SWE-bench Verified | ✅ Completed | 335/500 = 67.0% (thinking-off, Q5_K_M, RTX 5090 + MTP) |
| BugFind-15 | 📋 Pending | 9B reference: 79 |
| HermesAgent-20 | 📋 Pending | 9B reference: 85 |
| ToolCall-15 | 📋 Pending | 9B reference: 100 |
| InstructFollow-15 | 📋 Pending | 9B reference: 93 |

---

## 📚 9. Resources & Guides

👉 **[GitHub Repository: Jackrong-llm-finetuning-guide](https://github.com/R6410418/Jackrong-llm-finetuning-guide.git)**
Access the repository to dive into the codebase and reproduce our results.

👉 **[Qwen MTP GGUF Processing Workflow](https://github.com/R6410418/Jackrong-llm-finetuning-guide/tree/main/qwen-mtp-gguf)**
A custom splitting and merging methodology designed specifically for Qwen series Multi-Token Prediction (MTP) heads.

👉 **[benchlocal Evaluation Framework](https://github.com/stevibe/benchlocal)**
The evaluation framework used to run the local agentic and coding benchmarks.

👉 **[Qwopus3.6-27B-v2 Model Card](https://huggingface.co/Jackrong/Qwopus3.6-27B-v2)**
Base model card with full MMLU-Pro, SWE-bench, and throughput benchmarks.

---

## 🙏 10. Acknowledgements

Special thanks to:
- The **Qwen team** for providing the powerful Qwen3.6-27B base model.
- **Unsloth** for providing the highly efficient fine-tuning framework.
- **Kyle Hessling** for the close collaboration on hardware, training infrastructure, and evaluation support.
- Open-source datasets and community contributors, particularly **`lambda/hermes-agent-reasoning-traces`** for the high-quality agent trajectory data.

---

## 📖 11. Citation

```bibtex
@misc{jackrong_qwopus36_27b_coder,
  title        = {Qwopus-3.6-27B-Coder},
  author       = {Jackrong},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/Jackrong/Qwopus-3.6-27B-Coder}}
}
```
