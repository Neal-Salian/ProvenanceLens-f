---
library_name: transformers
base_model:
- Jackrong/Qwopus3.6-35B-A3B-v1
- unsloth/Qwen3.6-35B-A3B
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
- moe
- coder
- agent
- tool-use
- function-calling
- thinking-off
- long-context
- lora
- sft
- logic
- math
license: apache-2.0
language:
- en
- zh
- es
- ru
- ja
pipeline_tag: image-text-to-text
---
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #bae6fd; border-radius: 18px; box-shadow: 0 18px 40px rgba(8, 145, 178, 0.14); overflow: hidden; background: #ffffff; margin-bottom: 30px;">
  <div style="background: radial-gradient(circle at 15% 15%, rgba(254,243,199,0.42) 0%, rgba(254,243,199,0.12) 28%, transparent 46%), linear-gradient(135deg, #0891b2 0%, #2563eb 58%, #f97316 100%); padding: 28px; color: white;">
  <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
  <h1 style="margin: 0; font-size: 28px; font-weight: 900; display: flex; align-items: center; gap: 12px; color: white; border: none;">⚙️ Qwopus-3.6-35B-A3B-Coder</h1>
  <span style="background: #f97316; color: #fff7ed; font-size: 11px; font-weight: 900; padding: 5px 12px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.7px; box-shadow: 0 0 0 1px rgba(255,255,255,0.18);">Agentic Coder Release</span>
  </div>
  <p style="margin: 10px 0 0 0; font-size: 14px; color: #cffafe; font-weight: 600;">A thinking-off, token-efficient coding agent model built on Qwopus3.6-35B-A3B-v1 / Qwen3.6-35B-A3B.</p>
  </div>

  <div style="display: flex; gap: 8px; flex-wrap: wrap; padding: 13px 24px; background: linear-gradient(90deg, #f8fafc 0%, #fff7ed 100%); border-bottom: 1px solid #e2e8f0;">
  <span style="background: #ecfeff; color: #0e7490; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; border: 1px solid #a5f3fc;">🧠 Thinking-Off Agent</span>
  <span style="background: #ffedd5; color: #c2410c; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; border: 1px solid #fed7aa;">⚡ Token-Efficient Coding</span>
  <span style="background: #dcfce7; color: #166534; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; border: 1px solid #bbf7d0;">🛠️ Tool Calling & Workflow</span>
  <span style="background: #e0e7ff; color: #3730a3; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; border: 1px solid #c7d2fe;">🧩 35B-A3B MoE</span>
  <span style="background: #fef9c3; color: #854d0e; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px; border: 1px solid #fde68a;">🎮 Game Demo Ready</span>
  </div>

  <div style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
  <div style="background: linear-gradient(135deg, #ecfeff 0%, #fff7ed 100%); border-left: 5px solid #06b6d4; padding: 16px; border-radius: 0 12px 12px 0;">
  <h3 style="margin: 0 0 8px 0; font-size: 16px; color: #0e7490; font-weight: 900; display: flex; align-items: center; gap: 6px;"><span>💡</span> What is Qwopus-3.6-35B-A3B-Coder?</h3>
  <p style="margin: 0; font-size: 13px; color: #334155; line-height: 1.7;">🪐 <b>Qwopus-3.6-35B-A3B-Coder</b> is a practical coding-agent fine-tune focused on <b>execution efficiency</b>, not simply longer visible reasoning. It is designed for real agentic coding workflows where the model repeatedly reads files, chooses tools, edits code, runs tests, reacts to errors, and summarizes work. The core goal is to complete more of these steps with <b>less token waste, lower latency, and more stable behavior</b> when explicit long thinking is disabled.</p>
  </div>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px;">
  <div style="border: 1px solid #a5f3fc; padding: 15px; border-radius: 10px; background: #ecfeff; box-shadow: inset 0 2px 4px rgba(8,145,178,0.04);">
  <span style="font-weight: 900; color: #0e7490; font-size: 12px; display: block; margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.6px;">⚡ Fast Agent Loops</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.55;">Optimized for repeated tool decisions, patching, test runs, and error-driven debugging without forcing every step into long thinking mode.</span>
  </div>
  <div style="border: 1px solid #fed7aa; padding: 15px; border-radius: 10px; background: #fff7ed;">
  <span style="font-weight: 900; color: #c2410c; font-size: 12px; display: block; margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.6px;">🧩 MoE Efficiency</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.55;">Built from a 35B total / 3B active-parameter MoE foundation for high-throughput local coding workflows.</span>
  </div>
  <div style="border: 1px solid #bae6fd; padding: 15px; border-radius: 10px; background: #f0f9ff;">
  <span style="font-weight: 900; color: #0369a1; font-size: 12px; display: block; margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.6px;">🛠️ Agent Harness Fit</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.55;">Aims to fit Codex-style, OpenHands-style, Claude Code-style, and OpenCode-style agent harnesses.</span>
  </div>
  <div style="border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; background: #f0fdf4;">
  <span style="font-weight: 900; color: #047857; font-size: 12px; display: block; margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.6px;">🎮 Live Coding Demo</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.55;">Includes a slot for an RTS/game-building sample generated through an agent workflow.</span>
  </div>
  </div>
  </div>
</div>

> [!WARNING]
> **Community Release Notice**: Qwopus-3.6-35B-A3B-Coder is an experimental community model intended for research, local coding-agent evaluation, and workflow exploration. It has not undergone complete safety evaluation or broad general-domain benchmarking.

> [!IMPORTANT]
> **Evaluation Mode**: The central design target and comparison framing in this card is **thinking-off** execution. The model is evaluated for whether it can remain useful and stable without relying on long visible reasoning traces at every step.

---

## 🎯 1. Fine-Tuning Objective: Less Overthinking, More Execution

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; flex-direction: column; gap: 18px; margin-bottom: 30px;">

  <div style="border: 1px solid #cbd5e1; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #0891b2 0%, #2563eb 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧭</span> 1.1 Why This Model Exists
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.75;">
  The goal of this fine-tune is <b>not</b> to chase longer reasoning chains for their own sake. In a real coding agent workflow, many steps are operational rather than deeply philosophical: read a file, inspect a stack trace, choose the next tool, edit code, run tests, check the error, continue, and report the result.
  <br><br>
  If every one of these steps enters a long thinking mode, the workflow can pay unnecessary costs: more tokens, higher latency, noisier state transitions, and greater risk of long-horizon behavioral drift. Qwopus-3.6-35B-A3B-Coder is tuned around a different product assumption:
  <div style="margin-top: 14px; padding: 14px 16px; border-radius: 10px; background: #ecfeff; border: 1px solid #a5f3fc; color: #155e75; font-weight: 800;">
  Let the model do more agent work with fewer tokens, faster turns, and steadier tool behavior.
  </div>
  </div>
  </div>

  <div style="border: 1px solid #fed7aa; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #ea580c 0%, #9a3412 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>⚡</span> 1.2 Core Optimization Target
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.7;">
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px;">
  <div style="padding: 12px; border-radius: 10px; background: #fff7ed; border: 1px solid #fed7aa;"><b style="color:#c2410c;">1. Faster next-step decisions</b><br>Identify whether to inspect, edit, test, or summarize without excessive deliberation.</div>
  <div style="padding: 12px; border-radius: 10px; background: #f0f9ff; border: 1px solid #bae6fd;"><b style="color:#0369a1;">2. Lower token waste</b><br>Reduce unnecessary long-form reasoning in routine implementation steps.</div>
  <div style="padding: 12px; border-radius: 10px; background: #f0fdf4; border: 1px solid #bbf7d0;"><b style="color:#047857;">3. Better workflow stability</b><br>Keep multi-turn code tasks on track across file edits, tool calls, and retries.</div>
  <div style="padding: 12px; border-radius: 10px; background: #fefce8; border: 1px solid #fde68a;"><b style="color:#854d0e;">4. Local deployment fit</b><br>Make high-frequency coding tasks more practical on local or self-hosted inference stacks.</div>
  </div>
  </div>
  </div>

  <div style="border: 1px solid #cbd5e1; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🛠️</span> 1.3 Target Workflows
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.75;">
  This model is designed to be a strong fit for <b>Codex / OpenHands / Claude Code / OpenCode-style agent harnesses</b>, long-running repository edits, automated debugging, multi-round tool calls, low-latency local deployment, and large-context codebase tasks where practical execution quality matters more than verbose visible thinking.
  </div>
  </div>
</div>

---

## 💡 2. Base Model, Training Stack & Collaboration

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; flex-direction: column; gap: 18px; margin-bottom: 30px;">

  <div style="border: 1px solid #cbd5e1; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #0891b2 0%, #2563eb 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧠</span> 2.1 Base Model: Qwopus3.6-35B-A3B-v1 / Qwen3.6-35B-A3B
  </div>
  <div style="padding: 16px;">
  <p style="margin: 0 0 16px 0; font-size: 13px; color: #334155; line-height: 1.7;">
  The coder model builds on the Qwopus3.6-35B-A3B line, itself based on <b>Qwen3.6-35B-A3B</b>. The underlying architecture is a hybrid sparse MoE model with 35B total parameters and approximately 3B active parameters per token, making it attractive for local high-frequency coding workloads.
  </p>
  <table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 13px;">
  <thead>
  <tr style="background: rgba(8, 145, 178, 0.07);">
  <th style="padding: 9px 10px; border-bottom: 2px solid #0891b2; text-align: left; color: #0e7490; font-weight: 900; width: 30%;">Attribute</th>
  <th style="padding: 9px 10px; border-bottom: 2px solid #0891b2; text-align: left; font-weight: 900;">Specifications & Details</th>
  </tr>
  </thead>
  <tbody>
  <tr><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">🧩 Architecture</td><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Hybrid sparse MoE, 35B total parameters / ~3B active parameters per token</td></tr>
  <tr><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">🏢 Base Developer</td><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Alibaba Cloud / Qwen family, via unsloth/Qwen3.6-35B-A3B</td></tr>
  <tr><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">🎯 Coder Focus</td><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Agentic coding, tool-use stability, code editing, debugging, multi-turn workflow execution</td></tr>
  <tr><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">⚡ Evaluation Emphasis</td><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Thinking-off execution, token efficiency, lower latency, stable behavior across long agent loops</td></tr>
  <tr><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">📄 Context</td><td style="padding: 9px 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Designed for large-context repository work; exact deployment context depends on inference stack and configuration</td></tr>
  </tbody>
  </table>
  </div>
  </div>

  <div style="border: 1px solid #bbf7d0; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #10b981 0%, #047857 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧪</span> 2.2 Hardware Cooperation & Joint Collaboration
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.7;">
  This project is built in close collaboration with engineer <b>Kyle Hessling</b>, whose hardware infrastructure, training support, and live agent experiments help validate the model under practical coding workloads.
  <div style="margin-top: 10px; display: flex; align-items: center; gap: 6px;">
  <span>👉</span>
  <span>Follow hardware and model training updates on X / Twitter: <a href="https://x.com/KyleHessling1" target="_blank" style="color: #047857; text-decoration: none; font-weight: 900;">@KyleHessling1</a></span>
  </div>
  <div style="margin-top: 10px; display: flex; align-items: center; gap: 6px;">
  <span>📊</span>
  <span>Benchmarks courtesy of <b>Tom Turney</b>, <a href="https://x.com/no_stp_on_snek" target="_blank" style="color: #047857; text-decoration: none; font-weight: 900;">@no_stp_on_snek</a> on X.</span>
  </div>
  </div>
  </div>

  <div style="border: 1px solid #ddd6fe; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🦥</span> 2.3 Fine-Tuning Framework: Unsloth
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.7;">
  The training workflow is accelerated and memory-optimized with <b>Unsloth</b>. Special thanks to the Unsloth team for making efficient large-model fine-tuning more accessible.
  <div style="margin-top: 10px; display: flex; align-items: center; gap: 6px;">
  <span>👉</span>
  <span>Documentation and fine-tuning guidance: <a href="https://unsloth.ai/docs" target="_blank" style="color: #7c3aed; text-decoration: none; font-weight: 900;">unsloth.ai/docs</a></span>
  </div>
  </div>
  </div>
</div>

---

## 📊 3. Thinking-Off Agentic Evaluation

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #bae6fd; border-radius: 18px; box-shadow: 0 14px 32px rgba(8,145,178,0.12); overflow: hidden; background: #ffffff; margin-bottom: 30px;">
  <div style="background: linear-gradient(135deg, #0891b2 0%, #2563eb 62%, #f97316 100%); padding: 22px; color: white;">
  <h3 style="margin: 0; font-size: 21px; font-weight: 900; display: flex; align-items: center; gap: 8px; color: white; border: none;">📊 Evaluation: Qwopus 3.6 35B Thinking-Off vs Ornith-1.0 35B Thinking-On</h3>
  <p style="margin: 6px 0 0 0; font-size: 13px; color: #cffafe;">Comparison between Qwopus with thinking disabled and Ornith with thinking enabled. All benchmark runs in this section use Q5_K_M / Q5KM quantized models. Higher is better. Benchmarks courtesy of Tom Turney, @no_stp_on_snek on X.</p>
  </div>

  <div style="padding: 24px; display: flex; flex-direction: column; gap: 22px;">

  <div style="background: #ecfeff; border: 1px solid #a5f3fc; border-left: 5px solid #06b6d4; border-radius: 0 10px 10px 0; padding: 16px 20px; display: flex; gap: 12px; align-items: flex-start;">
  <span style="font-size: 25px;">⚡</span>
  <div>
  <span style="font-weight: 900; font-size: 14px; color: #0e7490; display: block; margin-bottom: 5px;">Main Finding</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.7;">In these Q5_K_M quantized evaluations, <b>Qwopus 3.6 35B</b> was tested with <b>thinking disabled</b>. The model also completed a 300-case SWE-bench submitted-patch run with a <b>62.4%</b> score. In the behavioral comparison, Qwopus leads in practical execution categories such as legit-request compliance, integrity under pressure, multi-turn orchestration, large code deliverables, and sustained debugging. Ornith remains stronger in selected reasoning-oriented dimensions such as long-context recall, metacognition, engineering competence, and context-poison resistance.</span>
  </div>
  </div>

  <div style="border: 1px solid #fed7aa; border-radius: 14px; overflow: hidden; background: linear-gradient(135deg, #fff7ed 0%, #ecfeff 100%); box-shadow: 0 8px 18px rgba(249,115,22,0.08);">
  <div style="padding: 18px 20px 14px 20px;">
  <div style="display: flex; gap: 12px; align-items: flex-start; margin-bottom: 10px;">
  <div style="font-size: 25px; line-height: 1;">🎞️</div>
  <div>
  <span style="font-weight: 900; font-size: 15px; color: #c2410c; display: block; margin-bottom: 6px;">Interactive Model Deck by Kyle Hessling</span>
  <span style="font-size: 13px; color: #334155; line-height: 1.7; display: block;">Kyle created a short Hugging Face Space deck that walks through the model story visually: thinking-off agentic coding, the 35B / 3B MoE setup, MTP-assisted local inference, SWE-bench results, token-efficiency comparisons, Qwopus OFF vs Ornith ON, and the OpenCode RTS demo.</span>
  </div>
  </div>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; margin-top: 12px;">
  <span style="background: #ffedd5; color: #c2410c; font-size: 11px; font-weight: 900; padding: 7px 10px; border-radius: 9px; border: 1px solid #fed7aa; text-align: center;">visual explainer</span>
  <span style="background: #dcfce7; color: #047857; font-size: 11px; font-weight: 900; padding: 7px 10px; border-radius: 9px; border: 1px solid #bbf7d0; text-align: center;">thinking-off workflow</span>
  <span style="background: #e0e7ff; color: #4338ca; font-size: 11px; font-weight: 900; padding: 7px 10px; border-radius: 9px; border: 1px solid #c7d2fe; text-align: center;">SWE-bench + RTS demo</span>
  </div>
  </div>
  <a href="https://huggingface.co/spaces/KyleHessling1/qwopus36-35b-a3b-coder-deck" target="_blank" style="display: block; padding: 13px 16px; background: linear-gradient(135deg, #f97316 0%, #2563eb 100%); color: white; text-decoration: none; font-size: 13px; font-weight: 900; text-align: center; letter-spacing: 0.2px;">Open Kyle's interactive deck →</a>
  </div>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 15px;">
  <div style="border: 1px solid #bbf7d0; padding: 16px; border-radius: 12px; background: #f0fdf4; text-align: center;">
  <span style="font-size: 11px; font-weight: 900; color: #047857; text-transform: uppercase; display: block; margin-bottom: 7px; letter-spacing: 0.6px;">Average Score</span>
  <span style="font-size: 25px; font-weight: 950; color: #047857; display: block; line-height: 1;">82.1 vs 78.9</span>
  <span style="font-size: 12px; color: #475569; font-weight: 700;">Qwopus vs Ornith</span>
  </div>
  <div style="border: 1px solid #ddd6fe; padding: 16px; border-radius: 12px; background: #f5f3ff; text-align: center;">
  <span style="font-size: 11px; font-weight: 900; color: #6d28d9; text-transform: uppercase; display: block; margin-bottom: 7px; letter-spacing: 0.6px;">SWE-bench</span>
  <span style="font-size: 27px; font-weight: 950; color: #6d28d9; display: block; line-height: 1;">62.4%</span>
  <span style="font-size: 12px; color: #475569; font-weight: 700;">300 cases, submitted patches</span>
  </div>
  </div>

  <div style="border: 1px solid #ddd6fe; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 18px rgba(109,40,217,0.08);">
  <div style="background: linear-gradient(135deg, #7c3aed 0%, #2563eb 60%, #0891b2 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>🧪</span> 3.1 SWE-bench Submitted-Patch Run
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.65;">
  <div style="background: #f5f3ff; border-left: 4px solid #7c3aed; border-radius: 0 8px 8px 0; padding: 12px 14px; margin-bottom: 14px; color: #4c1d95;">
  <b>Result:</b> Qwopus-3.6-35B-A3B-Coder scored <b>62.4%</b> on a <b>300-case SWE-bench run</b> using <b>thinking off</b> and <b>submitted patches</b>. The evaluated model was the <b>Q5_K_M quantized</b> build.
  </div>
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 14px;">
  <div style="padding: 13px; border-radius: 10px; background: #ecfeff; border: 1px solid #a5f3fc;"><span style="font-size: 11px; font-weight: 900; color: #0e7490; text-transform: uppercase; display: block; margin-bottom: 5px;">Benchmark</span><b style="font-size: 15px; color: #0f172a;">SWE-bench</b></div>
  <div style="padding: 13px; border-radius: 10px; background: #fff7ed; border: 1px solid #fed7aa;"><span style="font-size: 11px; font-weight: 900; color: #c2410c; text-transform: uppercase; display: block; margin-bottom: 5px;">Run Size</span><b style="font-size: 15px; color: #0f172a;">300 tasks</b></div>
  <div style="padding: 13px; border-radius: 10px; background: #f0fdf4; border: 1px solid #bbf7d0;"><span style="font-size: 11px; font-weight: 900; color: #047857; text-transform: uppercase; display: block; margin-bottom: 5px;">Mode</span><b style="font-size: 15px; color: #0f172a;">Thinking off</b></div>
  <div style="padding: 13px; border-radius: 10px; background: #f5f3ff; border: 1px solid #ddd6fe;"><span style="font-size: 11px; font-weight: 900; color: #6d28d9; text-transform: uppercase; display: block; margin-bottom: 5px;">Quantization</span><b style="font-size: 15px; color: #0f172a;">Q5_K_M</b></div>
  </div>
  <table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 13px;">
  <thead>
  <tr style="background: rgba(124, 58, 237, 0.08);">
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; color: #6d28d9; font-weight: 900;">Evaluation</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 900;">Model / Quant</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 900;">Patch Mode</th>
  <th style="padding: 10px; border-bottom: 2px solid #7c3aed; text-align: left; font-weight: 900;">Score</th>
  </tr>
  </thead>
  <tbody>
  <tr style="background: #f5f3ff;">
  <td style="padding: 10px; font-weight: 800;">SWE-bench, 300 cases</td>
  <td style="padding: 10px;">Qwopus-3.6-35B-A3B-Coder Q5_K_M</td>
  <td style="padding: 10px;">Thinking off, submitted patches</td>
  <td style="padding: 10px; font-weight: 950; color: #6d28d9;">62.4%</td>
  </tr>
  </tbody>
  </table>
  </div>
  </div>

  <div style="border: 1px solid #cbd5e1; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 6px rgba(15,23,42,0.04);">
  <div style="background: linear-gradient(135deg, #f8fafc 0%, #ecfeff 100%); padding: 13px 16px; border-bottom: 1px solid #cbd5e1; font-weight: 900; font-size: 14px; color: #0f172a; display: flex; align-items: center; gap: 8px;">
  <span>⚖️</span> 3.2 Numerical Scorecard
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.65;">
  <div style="background: #fff7ed; border-left: 4px solid #f97316; border-radius: 0 8px 8px 0; padding: 10px 12px; margin-bottom: 12px; color: #7c2d12;">
  <b>Note:</b> Scores are held-out behavioral + long-horizon coding evaluation results on a 0-100 scale. Higher is better. The comparison intentionally contrasts Qwopus in thinking-off mode with Ornith-1.0 in thinking-on mode.
  </div>
  <table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 13px;">
  <thead>
  <tr style="background: rgba(14, 116, 144, 0.07);">
  <th style="padding: 10px; border-bottom: 2px solid #0891b2; text-align: left; color: #0e7490; font-weight: 900;">Capability Area</th>
  <th style="padding: 10px; border-bottom: 2px solid #0891b2; text-align: left; font-weight: 900;">Qwopus 3.6 35B<br><span style="font-size: 12px; color: #047857; font-weight: 900; display: block; margin-top: 4px;">thinking off</span></th>
  <th style="padding: 10px; border-bottom: 2px solid #0891b2; text-align: left; font-weight: 900;">Ornith-1.0 35B<br><span style="font-size: 12px; color: #b91c1c; font-weight: 900; display: block; margin-top: 4px;">thinking on</span></th>
  <th style="padding: 10px; border-bottom: 2px solid #0891b2; text-align: left; font-weight: 900;">Observed Pattern</th>
  </tr>
  </thead>
  <tbody>
  <tr style="background: #ecfeff;"><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Legit-request compliance</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #0e7490;">100</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">70</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Qwopus follows allowed user intent much more reliably.</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Integrity under pressure</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #0e7490;">93</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">86</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Qwopus is more stable under adversarial or stressful workflow conditions.</td></tr>
  <tr style="background: #ecfeff;"><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Multi-turn orchestration</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #0e7490;">80</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">70</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Qwopus better maintains state across long agent loops.</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Large code deliverable</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #0e7490;">75</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">65</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Qwopus shows stronger completion behavior for larger code artifacts.</td></tr>
  <tr style="background: #ecfeff;"><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Sustained debugging</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #0e7490;">60</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">50</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Qwopus holds a practical edge across repeated fix-test cycles.</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Long-context recall</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">90</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #b45309;">95</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Ornith retains a small advantage in recall-heavy thinking-on settings.</td></tr>
  <tr style="background: #fff7ed;"><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Metacognition</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">90</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #b45309;">95</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Ornith benefits from explicit thinking-on reflection.</td></tr>
  <tr><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 800;">Engineering competence</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">81</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15); font-weight: 900; color: #b45309;">94</td><td style="padding: 10px; border-bottom: 1px solid rgba(128,128,128,0.15);">Ornith remains stronger in broad engineering competence.</td></tr>
  <tr style="background: #fff7ed;"><td style="padding: 10px; font-weight: 800;">Context-poison resistance</td><td style="padding: 10px;">70</td><td style="padding: 10px; font-weight: 900; color: #b45309;">85</td><td style="padding: 10px;">Ornith is more robust against context poisoning in this test.</td></tr>
  </tbody>
  </table>
  </div>
  </div>

  <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #22c55e; border-radius: 0 10px 10px 0; padding: 16px 20px; font-size: 13px; color: #064e3b; line-height: 1.7;">
  <b>Takeaway:</b> Qwopus-3.6-35B-A3B-Coder is positioned as a <b>practical agent execution model</b>. The important result is not merely whether it can think longer, but whether it can keep acting correctly when the workflow demands many fast, concrete decisions. This makes it especially relevant for local coding agents, automated debugging loops, and large codebase tasks where token efficiency directly affects usability.
  </div>

  </div>
</div>

---

## 🎮 4. Live Agent Demo: RTS Game Sample

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #cbd5e1; border-radius: 16px; box-shadow: 0 10px 24px rgba(15,23,42,0.08); overflow: hidden; background: #ffffff; margin-bottom: 30px;">
  <div style="background: linear-gradient(135deg, #14532d 0%, #0f766e 46%, #0369a1 100%); padding: 20px; color: white;">
  <h3 style="margin: 0; font-size: 20px; font-weight: 900; display: flex; align-items: center; gap: 8px; color: white; border: none;">🎮 OpenCode / Agent Game-Building Demo</h3>
  <p style="margin: 5px 0 0 0; font-size: 13px; color: #dcfce7;">A practical visual test for whether the model can plan, code, iterate, and deliver an interactive project inside an agent workflow.</p>
  </div>
  <div style="padding: 20px; font-size: 13px; color: #334155; line-height: 1.7;">
  <p style="margin: 0 0 12px 0;">Kyle Hessling tested the soon-to-release Qwopus-Coder-35B-A3B in an OpenCode workflow by asking it to create a complete RTS-style game sample. This kind of demo is useful because it combines code generation, file orchestration, UI/gameplay logic, iterative correction, and final deliverable quality in one visible task.</p>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin-bottom: 14px;">
  <a href="https://x.com/KyleHessling1/status/2070562997630873699" target="_blank" style="display: block; padding: 12px 14px; border: 1px solid #bbf7d0; border-radius: 10px; background: #f0fdf4; color: #047857; text-decoration: none; font-weight: 900;">View Kyle's RTS demo post</a>
  <div style="display: block; padding: 12px 14px; border: 1px solid #bae6fd; border-radius: 10px; background: #f0f9ff; color: #0369a1; font-weight: 900;">Game screenshot added below</div>
  </div>

  <a href="https://cdn-uploads.huggingface.co/production/uploads/66309bd090589b7c65950665/MiFWxkoAogtYtbxNRSogc.png" target="_blank" style="display: block; border: 1px solid #cbd5e1; border-radius: 14px; overflow: hidden; background: #f8fafc; text-decoration: none;">
  <img src="https://cdn-uploads.huggingface.co/production/uploads/66309bd090589b7c65950665/MiFWxkoAogtYtbxNRSogc.png" alt="Qwopus-3.6-35B-A3B-Coder RTS game demo screenshot" style="width: 100%; display: block; border: 0;" />
  </a>

  <div style="margin-top: 14px; background: #fff7ed; border-left: 4px solid #f97316; border-radius: 0 8px 8px 0; padding: 12px 14px; color: #7c2d12;">
  <b>Why this matters:</b> a playable game demo is not a formal benchmark, but it is a high-signal smoke test for agentic coding. It exposes whether the model can maintain project structure, generate coherent state logic, and complete a visually inspectable artifact rather than only answering isolated prompts.
  </div>
  </div>
</div>


---

## 🗺️ 5. Training & Workflow Design

The training and evaluation philosophy for this release centers on agent execution rather than visible chain length. The model should know when to act directly, when to inspect more context, and when to stop and summarize.

```text
       [ Qwopus-3.6-35B-A3B-Coder: Agentic Execution Pipeline ]

  Base MoE Foundation
  Qwen3.6-35B-A3B / Qwopus3.6-35B-A3B-v1
          │
          ▼
  Coding + Tool-Use Adaptation
  repository tasks, debugging traces, tool schemas, multi-turn feedback
          │
          ▼
  Thinking-Off Behavior Target
  faster next-step decisions, less overthinking, lower token waste
          │
          ▼
  Agent Harness Workflows
  read files → choose tool → edit code → run tests → inspect errors → iterate → report
          │
          ▼
  Final Objective
  stable long-horizon code execution with practical local latency
```

> [!NOTE]
> This model card intentionally frames thinking-off behavior as a product target. Long thinking can still be useful for difficult reasoning, but the release focuses on whether the model can complete real coding-agent work without paying that cost on every step.

---

## ✅ 6. Recommended Use Cases & Known Limits

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 30px;">
  <div style="border: 1px solid #bbf7d0; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #16a34a 0%, #047857 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>✅</span> Good Fits
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.7;">
  Codex-style agent workflows, OpenHands/OpenCode coding loops, repository-level debugging, multi-file patch generation, automated test-fix cycles, local tool-calling agents, DevOps scripting, code review assistance, and large-context project navigation.
  </div>
  </div>

  <div style="border: 1px solid #fed7aa; border-radius: 14px; overflow: hidden; background: #ffffff; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
  <div style="background: linear-gradient(135deg, #f97316 0%, #b45309 100%); padding: 13px 16px; color: white; font-weight: 900; font-size: 14px; display: flex; align-items: center; gap: 8px;">
  <span>⚠️</span> Use With Care
  </div>
  <div style="padding: 16px; font-size: 13px; color: #334155; line-height: 1.7;">
  As a specialized coder model, it should not be assumed to be optimal for every general-domain task. Tool-call quality depends strongly on prompt format, schema consistency, and the surrounding harness. Long thinking may still help on some high-difficulty reasoning tasks where speed is less important.
  </div>
  </div>
</div>

> [!CAUTION]
> **Deployment note**: For agent use, ensure that tool definitions, system prompts, output parsing, and retry behavior are consistent. Thinking-off models can be fast, but the harness still needs clean schemas, useful error feedback, and strict task boundaries.

---

## 📚 7. Resources, Acknowledgements & Citation

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #bae6fd; border-radius: 16px; overflow: hidden; background: #ffffff; box-shadow: 0 10px 24px rgba(8,145,178,0.10); margin-bottom: 30px;">
  <div style="background: linear-gradient(135deg, #0891b2 0%, #2563eb 65%, #f97316 100%); padding: 18px 20px; color: white;">
  <h3 style="margin: 0; color: white; border: none; font-size: 19px; font-weight: 900;">📚 Resources & Credits</h3>
  </div>
  <div style="padding: 20px; font-size: 13px; color: #334155; line-height: 1.7;">
  <p style="margin: 0 0 12px 0;">👉 <a href="https://github.com/R6410418/Jackrong-llm-finetuning-guide.git" target="_blank" style="color: #0369a1; text-decoration: none; font-weight: 900;">GitHub Repository: Jackrong-llm-finetuning-guide</a><br>Access the project repository and related fine-tuning guides.</p>
  <p style="margin: 0 0 12px 0;">👉 <b>Q5_K_M benchmark evaluations</b><br>SWE-bench submitted-patch run plus behavioral / long-horizon coding evaluation. Benchmarks courtesy of Tom Turney, <b>@no_stp_on_snek</b> on X.</p>
  <p style="margin: 0 0 12px 0;">👉 <a href="https://huggingface.co/spaces/KyleHessling1/qwopus36-35b-a3b-coder-deck" target="_blank" style="color: #c2410c; text-decoration: none; font-weight: 900;">Kyle Hessling Interactive Model Deck</a><br>Visual Hugging Face Space explaining the model story, thinking-off workflow, SWE-bench result, token efficiency, and RTS demo.</p>
  <p style="margin: 0 0 12px 0;">👉 <a href="https://x.com/KyleHessling1/status/2070562997630873699" target="_blank" style="color: #047857; text-decoration: none; font-weight: 900;">Kyle Hessling RTS Game Demo Post</a><br>Reference post for the OpenCode / RTS game-building sample.</p>
  <p style="margin: 0 0 16px 0;">👉 <a href="https://unsloth.ai/docs" target="_blank" style="color: #7c3aed; text-decoration: none; font-weight: 900;">Unsloth Documentation</a><br>Training acceleration and memory-efficient fine-tuning resources.</p>

  <div style="margin-top: 16px; padding: 14px; border-radius: 10px; background: #f8fafc; border: 1px solid #e2e8f0;">
  <b>Acknowledgements:</b> Special thanks to the Qwen team for the strong Qwen3.6 MoE base model, Unsloth for efficient fine-tuning tooling, Kyle Hessling for hardware collaboration and live agent testing, and open-source contributors building the agentic coding ecosystem.
  </div>

  <div style="margin-top: 16px;">
  <b style="display: block; margin-bottom: 8px;">Citation</b>
  <pre style="margin: 0; padding: 14px; border-radius: 10px; background: #f8fafc; color: #334155; border: 1px solid #e2e8f0; overflow-x: auto; font-size: 12px; line-height: 1.55;"><code style="color: #334155;">@misc{jackrong_qwopus36_35b_a3b_coder,
  title        = {Qwopus-3.6-35B-A3B-Coder},
  author       = {Jackrong},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/Jackrong/Qwopus-3.6-35B-A3B-Coder}}
}</code></pre>
  </div>
  </div>
</div>
