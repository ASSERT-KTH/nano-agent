# Nano
<p align="center">
<svg xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges" viewBox="0 -0.5 30 21" width="240" height="168"><path stroke="#282828" d="M0,0h30M0,1h30M0,2h12M18,2h12M0,3h11M19,3h11M0,4h11M19,4h11M0,5h11M19,5h11M0,6h11M19,6h11M0,7h12M18,7h12M0,8h13M17,8h13M0,9h11M19,9h11M0,10h11M12,10h1M17,10h1M19,10h11M0,11h13M14,11h2M17,11h13M0,12h30M0,13h30M0,14h2M3,14h3M7,14h3M11,14h1M16,14h1M18,14h3M22,14h1M28,14h2M0,15h3M4,15h2M8,15h2M11,15h1M13,15h2M16,15h1M19,15h2M22,15h1M24,15h3M28,15h2M0,16h4M5,16h1M7,16h1M9,16h1M11,16h1M16,16h1M18,16h1M20,16h1M22,16h1M24,16h3M28,16h2M0,17h3M4,17h2M7,17h2M11,17h1M13,17h2M16,17h1M18,17h2M22,17h1M24,17h3M28,17h2M0,18h2M3,18h3M7,18h3M11,18h1M13,18h2M16,18h1M18,18h3M22,18h1M28,18h2M0,19h30M0,20h30"/><path stroke="#000000" d="M12,2h6M11,3h8M11,4h1M18,4h1M11,5h1M13,5h1M16,5h1M18,5h1M11,6h8M12,7h6M13,8h4M11,9h8M11,10h1M13,10h4M18,10h1M13,11h1M16,11h1"/><path stroke="#66ff66" d="M12,4h6M12,5h1M14,5h2M17,5h1M2,14h1M6,14h1M10,14h1M12,14h4M17,14h1M21,14h1M23,14h5M3,15h1M6,15h2M10,15h1M12,15h1M15,15h1M17,15h2M21,15h1M23,15h1M27,15h1M4,16h1M6,16h1M8,16h1M10,16h1M12,16h4M17,16h1M19,16h1M21,16h1M23,16h1M27,16h1M3,17h1M6,17h1M9,17h2M12,17h1M15,17h1M17,17h1M20,17h2M23,17h1M27,17h1M2,18h1M6,18h1M10,18h1M12,18h1M15,18h1M17,18h1M21,18h1M23,18h5"/></svg>

</p>

*A minimal, no‑magic coding‑agent for:*

1. agent‑in‑the‑loop reinforcement learning  
2. understanding coding agents in clear, minimal terms  
3. running neat little code fixes with modern LLMs

---

## What it is

`Nano` is a zero‑bloat wrapper that turns any tool-enabled LLM into a coding agent with two tools:

```

shell(cmd)  # ls, cat, grep … (stateful, runs in rbash)
apply_patch({...})  # search/replace on one file

```

> **Note:** Nano runs commands in `rbash` (restricted bash), which helps provide a safer execution environment by limiting access to certain operations.

Nothing else.

No internal state modeling, no fuzzy patching, no hidden prompts or repo graphs.  
You get the raw reasoning, tool calls, and results — exactly what the model saw and did.

---

## Why it exists

Most coding agents (e.g. Aider, SWE-Agent, Devin) are designed to perform well. To achieve that, they bake in layers of human-designed heuristics:  
navigation memory, prompt rewriting, hand-crafted repo maps, retry logic...

These make agents more *capable*, but also more *opaque*.  
They're hard to analyze, and thus hard to adopt to generate rollout training data.

`Nano` takes the opposite stance:  
Inspired by [**The Bitter Lesson**](http://www.incompleteideas.net/IncIdeas/BitterLesson.html), we believe that long-term performance comes not from human intuition, but from **letting models learn their own strategies** — even if they start out worse.  
That's what `Nano` tries to provide.


---

## Install

```bash
git clone git@github.com:ASSERT-KTH/nano-agent.git && cd nano-agent && pip install -e .
# or
pip install nano-agent  # TODO: publish
```

Then you just need an API key for your chosen provider or host them yourself with [vLLM](https://docs.vllm.ai/en/latest/). See [litellm](https://docs.litellm.ai/docs/) documentation for more details.

---

## Example: rollout to Tensor

```python
from transformers import AutoTokenizer
from nano_agent import Agent

agent = Agent(model="openrouter/qwen/qwen3-8b", thinking=True)
agent.run(".", "There is a bug in this repo...")

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
from nano_agent import Agent
from datasets import load_dataset

run = load_dataset("SWE-Gym/SWE-Gym", split="train[:1]")[0]

tempdir = tempfile.mkdtemp()
Repo.clone_from(f"https://github.com/{run['repo']}.git", tempdir)

agent = Agent(
    model="hosted_vllm/qwen/qwen3-8b",
    api_base="http://localhost:8000/v1",
    thinking=True  # enables <think> ... </think> reasoning blocks
)
diff = agent.run(run["problem_statement"], repo_root=tempdir)
print(diff)  # the unified diff produced by the agent
print(agent.messages, agent.tools)  # or access in `.nano/<timestamp>/
```

---

## Use with HuggingFace TRL

Because `Nano` can communicate with any OpenAI compatible endpoint and produces token-level message logs, it works "cleanly" as a data generator inside **TRL's `GPROTrainer`**.

> **Note:** "cleanly" refers to modifications made in our [TRL fork](https://github.com/ASSERT-KTH/trl) to enable direct agent integration. These changes support the [CodeRepairRL](https://github.com/ASSERT-KTH/CodeRepairRL) project but may not be merged into the main HuggingFace repository.

To use it:

* Write a rollout client that wraps `Agent.run()`
* Extract the diff and messages for each training example
* Feed those into TRL's reward modeling or fine-tuning pipelines

This lets you train models that learn to use tools directly, grounded in interaction data — no custom env needed.

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
