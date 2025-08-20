<p align="center">
  <img src="nano.svg"/>
</p>

# Nano <div style="float: right;">[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ASSERT-KTH/nano-agent)</div>

*A minimal coding‑agent for:*

1. agent‑in‑the‑loop reinforcement learning  
2. understanding coding agents in clear, minimal terms  
3. running neat little code fixes

---

## What it is

`Nano` is a zero‑bloat wrapper that turns any tool-enabled LLM into a coding agent with two tools:

```

shell(cmd)  # ls, cat, grep …
apply_patch({...})  # search/replace on one file

```

> **Note:** `Nano` uses `rbash` (restricted bash) to confine the agent to its designated workspace. This, along with Nano's requirement of starting in a clean git repository, helps ensure its operations remain contained and predictable.


---

## Why it exists

Most coding agents (e.g. Aider, SWE-Agent, Devin) are designed to perform well. To achieve that, they bake in layers of effective but ad-hoc solutions:  
repo maps, navigation memory, multi agent orchestration, adherence prompting, retry logic,...

These make agents more *capable*, but also more *opaque*. They're hard to analyze, and thus harder to adopt.

`Nano` takes the opposite stance: 
 
Inspired by [**The Bitter Lesson**](http://www.incompleteideas.net/IncIdeas/BitterLesson.html), we believe that long-term performance comes not from encoding human intuitions, but from **letting models learn their own strategies**, even if they start out worse.  

Effective reinforcement learning relies on a complete and unaltered log of agent interactions. `Nano` ensures this transparency by providing direct, non-obfuscated access to the raw reasoning, tool calls, and results, offering a precise record of what the model saw and did.

That's what `Nano` tries to provide.

---

## Install

```bash
git clone git@github.com:ASSERT-KTH/nano-agent.git && cd nano-agent && pip install -e .
# or
pip install nano-agent
```

Then you just need an API key for your chosen provider or host them yourself with [vLLM](https://docs.vllm.ai/en/latest/). See [litellm](https://docs.litellm.ai/docs/) documentation for more details.

---

## Example: rollout to Tensor

```python
from nano import Agent
from transformers import AutoTokenizer

agent = Agent(model="openai/gpt-4.1-mini")
agent.run("There is a bug in this repo...")

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
tokens = tokenizer.apply_chat_template(
  agent.messages,
  tools=agent.tools,
  tokenize=True,
  return_format="pt"
)
```

## Example: minimal SWE‑Gym rollout

```python
import tempfile
from git import Repo  # git-python
from nano import Agent
from datasets import load_dataset

run = load_dataset("SWE-Gym/SWE-Gym", split="train[:1]")[0]

tempdir = tempfile.mkdtemp()
Repo.clone_from(f"https://github.com/{run['repo']}.git", tempdir)

agent = Agent(
    model="hosted_vllm/qwen/qwen3-8b",
    api_base="http://localhost:8000/v1",
)
diff = agent.run(run["problem_statement"], repo_root=tempdir)
print(diff)  # the unified diff produced by the agent
print(agent.messages, agent.tools)  # or access in `~/.nano/<timestamp>/
```

---

## Use with HuggingFace TRL

Because `Nano` can communicate with any tool-enabled OpenAI compatible endpoint and produces token-level message logs, it works "cleanly" as a data generator inside **TRL's `GPROTrainer`**.

> **Note:** "cleanly" refers to modifications made in our [TRL fork](https://github.com/ASSERT-KTH/trl) to enable direct agent integration. These changes support the [CodeRepairRL](https://github.com/ASSERT-KTH/CodeRepairRL) project but may not be merged into the main HuggingFace repository.

To use it:

* Write a rollout client that wraps `Agent.run()`
* Extract the diff and messages for each training example
* Feed those into TRL's reward modeling or fine-tuning pipelines

This lets you train models that learn to use tools directly, grounded in interaction data — no custom env needed.

This approach acknowledges that the agent may initially fail in certain situations; however, these failures are valuable learning opportunities. We can then directly reinforce favorable behaviors and successful outcomes using outcome supervision, progressively refining the agent's strategies.

---


## Citation

```
@misc{nano-agent2025,
  author       = {Bjarni Haukur},
  title        = {Nano: a minimalist coding agent for agent-in-the-loop training},
  howpublished = {\url{https://github.com/ASSERT-KTH/nano-agent}},
  year         = {2025}
}
```



## 🏆 Current Leaderboard

Performance on SWE-bench Lite subset, ranked by code similarity

<table>
<thead>
<tr>
<th>#</th>
<th>Ver</th>
<th>Model</th>
<th>Code Sim</th>
<th>Test Sim</th>
<th style='text-align: right !important' align='right'>Tokens</th>
<th style='text-align: right !important' align='right'>Tools</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>v3.2.0</td>
<td>claude-sonnet-4-20250514</td>
<td>0.394</td>
<td>0.188</td>
<td style='text-align: right !important' align='right'>14,746 / 16,384</td>
<td style='text-align: right !important' align='right'>41.5 / 100</td>
</tr>
<tr>
<td>2</td>
<td>v3.2.0</td>
<td>gpt-4.1</td>
<td>0.387</td>
<td>0.092</td>
<td style='text-align: right !important' align='right'>9,777 / 16,384</td>
<td style='text-align: right !important' align='right'>35.7 / 100</td>
</tr>
<tr>
<td>3</td>
<td>v4.0.1</td>
<td>kimi-k2</td>
<td>0.382</td>
<td>0.009</td>
<td style='text-align: right !important' align='right'>5,508 / 16,384</td>
<td style='text-align: right !important' align='right'>19.7 / 100</td>
</tr>
<tr>
<td>4</td>
<td>v4.0.1</td>
<td>qwen3-coder</td>
<td>0.374</td>
<td>0.042</td>
<td style='text-align: right !important' align='right'>6,979 / 16,384</td>
<td style='text-align: right !important' align='right'>26.5 / 100</td>
</tr>
<tr>
<td>5</td>
<td>v3.2.0</td>
<td>gemini-2.5-pro-preview</td>
<td>0.370</td>
<td>0.034</td>
<td style='text-align: right !important' align='right'>6,008 / 16,384</td>
<td style='text-align: right !important' align='right'>13.6 / 100</td>
</tr>
<tr>
<td>6</td>
<td>v4.0.0</td>
<td>gpt-4.1</td>
<td>0.367</td>
<td>0.074</td>
<td style='text-align: right !important' align='right'>8,637 / 16,384</td>
<td style='text-align: right !important' align='right'>28.6 / 100</td>
</tr>
<tr>
<td>7</td>
<td>v3.3.0</td>
<td>gemini-2.5-flash</td>
<td>0.363</td>
<td>0.022</td>
<td style='text-align: right !important' align='right'>4,337 / 16,384</td>
<td style='text-align: right !important' align='right'>13.2 / 100</td>
</tr>
<tr>
<td>8</td>
<td>v3.2.0</td>
<td>gemini-2.5-flash-preview-05-20</td>
<td>0.362</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>4,547 / 16,384</td>
<td style='text-align: right !important' align='right'>10.1 / 100</td>
</tr>
<tr>
<td>9</td>
<td>v3.2.0</td>
<td>gpt-4.1-mini</td>
<td>0.350</td>
<td>0.017</td>
<td style='text-align: right !important' align='right'>7,403 / 16,384</td>
<td style='text-align: right !important' align='right'>29.7 / 100</td>
</tr>
<tr>
<td>10</td>
<td>v3.2.0</td>
<td>deepseek-chat</td>
<td>0.336</td>
<td>0.011</td>
<td style='text-align: right !important' align='right'>3,297 / 16,384</td>
<td style='text-align: right !important' align='right'>7.5 / 100</td>
</tr>
<tr>
<td>11</td>
<td>v4.0.1</td>
<td>glm-4.5</td>
<td>0.323</td>
<td>0.107</td>
<td style='text-align: right !important' align='right'>12,477 / 16,384</td>
<td style='text-align: right !important' align='right'>28.7 / 100</td>
</tr>
<tr>
<td>12</td>
<td>v4.0.1</td>
<td>gpt-5-mini</td>
<td>0.288</td>
<td>0.022</td>
<td style='text-align: right !important' align='right'>12,366 / 16,384</td>
<td style='text-align: right !important' align='right'>27.5 / 100</td>
</tr>
<tr>
<td>13</td>
<td>v3.2.0</td>
<td>qwen-2.5-72b-instruct</td>
<td>0.272</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>5,873 / 16,384</td>
<td style='text-align: right !important' align='right'>35.1 / 100</td>
</tr>
<tr>
<td>14</td>
<td>v3.2.0</td>
<td>qwen3-32b</td>
<td>0.255</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>5,281 / 16,384</td>
<td style='text-align: right !important' align='right'>28.3 / 100</td>
</tr>
<tr>
<td>15</td>
<td>v3.2.0</td>
<td>llama-4-maverick</td>
<td>0.255</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>4,647 / 16,384</td>
<td style='text-align: right !important' align='right'>10.4 / 100</td>
</tr>
<tr>
<td>16</td>
<td>v3.2.0</td>
<td>qwen3-14b-thinking</td>
<td>0.253</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>8,549 / 16,384</td>
<td style='text-align: right !important' align='right'>16.3 / 100</td>
</tr>
<tr>
<td>17</td>
<td>v3.3.0</td>
<td>gemini-2.5-flash-lite-preview-06-17</td>
<td>0.243</td>
<td>0.005</td>
<td style='text-align: right !important' align='right'>6,294 / 16,384</td>
<td style='text-align: right !important' align='right'>21.6 / 100</td>
</tr>
<tr>
<td>18</td>
<td>v3.2.0</td>
<td>qwen3-32b-thinking</td>
<td>0.224</td>
<td>0.005</td>
<td style='text-align: right !important' align='right'>9,357 / 16,384</td>
<td style='text-align: right !important' align='right'>8.3 / 100</td>
</tr>
<tr>
<td>19</td>
<td>v3.2.0</td>
<td>qwen3-8b-thinking</td>
<td>0.210</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>8,688 / 16,384</td>
<td style='text-align: right !important' align='right'>15.0 / 100</td>
</tr>
<tr>
<td>20</td>
<td>v3.2.0</td>
<td>qwen3-8b</td>
<td>0.190</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>8,704 / 16,384</td>
<td style='text-align: right !important' align='right'>56.5 / 100</td>
</tr>
<tr>
<td>21</td>
<td>v3.2.0</td>
<td>gpt-4.1-nano</td>
<td>0.188</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>8,536 / 16,384</td>
<td style='text-align: right !important' align='right'>33.1 / 100</td>
</tr>
<tr>
<td>22</td>
<td>v3.2.0</td>
<td>qwen3-14b</td>
<td>0.176</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>10,800 / 16,384</td>
<td style='text-align: right !important' align='right'>82.6 / 100</td>
</tr>
<tr>
<td>23</td>
<td>v3.2.0</td>
<td>devstral-small</td>
<td>0.092</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>14,603 / 16,384</td>
<td style='text-align: right !important' align='right'>13.0 / 100</td>
</tr>
</tbody>
</table>

## 🏆 SWE-bench Verified Leaderboard

Performance on SWE-bench Verified subset, ranked by code similarity

<table>
<thead>
<tr>
<th>#</th>
<th>Ver</th>
<th>Model</th>
<th>Code Sim</th>
<th>Test Sim</th>
<th style='text-align: right !important' align='right'>Tokens</th>
<th style='text-align: right !important' align='right'>Tools</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>v3.3.2</td>
<td>gemini-2.5-flash</td>
<td>0.353</td>
<td>0.000</td>
<td style='text-align: right !important' align='right'>5,956 / 16,384</td>
<td style='text-align: right !important' align='right'>12.5 / 100</td>
</tr>
</tbody>
</table>

**How it works:**
- **Input**: A GitHub repository containing a bug with a known ground truth solution
- **Task**: Nano provides models with tools to explore the codebase and generate a fix
- **Output**: Nano produces a unified git diff containing all proposed code changes
- **Evaluation**: We measure how closely the model's solution matches the ground truth using:
  - **Code Similarity**: How well the fix matches the actual bug fix (primary ranking metric)
  - **Test Similarity**: How well any test changes match the ground truth test updates

**Note:** Prone to a lot of noise, small test set with few repetitions.
