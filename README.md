# nano‑agent

*A minimal, no‑magic coding‑agent scaffold for:*

1. agent‑in‑the‑loop reinforcement learning  
2. understanding coding agents in clear, minimal terms  
3. running neat little code fixes with modern LLMs

---

## What it is

`nano‑agent` is a zero‑bloat wrapper that turns any OpenAI‑style LLM into a coding agent with two tools:

```

shell(cmd)  # ls, cat, grep … (stateful, runs in rbash)
apply_patch({...})  # search/replace on one file

````

Nothing else.

No internal state modeling, no fuzzy patching, no hidden prompts or repo graphs.  
You get the raw reasoning, tool calls, and results — exactly what the model saw and did.

---

## Why it exists

Most coding agents (e.g. Aider, SWE-Agent, Devin) are designed to perform well. To achieve that, they bake in layers of human-designed heuristics:  
navigation memory, prompt rewriting, hand-crafted repo maps, retry logic...

These make agents more *capable*, but also more *opaque*.  
They're hard to analyze, and thus hard to adopt to generate rollout training data.

`nano‑agent` takes the opposite stance:  
Inspired by [**The Bitter Lesson**](http://www.incompleteideas.net/IncIdeas/BitterLesson.html), we believe that long-term performance comes not from human intuition, but from **letting models learn their own strategies** — even if they start out worse.  
That's what `nano‑agent` tries to provide.

---

## Example: minimal SWE‑Gym rollout

```python
import tempfile
from datasets import load_dataset
from nano_agent import Agent
from git import Repo

run = load_dataset("SWE-Gym/SWE-Gym", split="train[:1]")[0]

tempdir = tempfile.mkdtemp()
Repo.clone_from(f"https://github.com/{run['repo']}.git", tempdir)

agent = Agent(
    model="hosted_vllm/qwen3-8b",
    api_base="http://localhost:8000/v1",
    thinking=True  # enables <think> ... </think> reasoning blocks
)
agent.run(run["problem_statement"], repo_root=tempdir)
print(agent.messages, agent.tools)  # or access in `.nano-agent/<timestamp>/
```

---

## Use with HuggingFace TRL

Because `nano‑agent` exposes the agent via a single `.run()` call and produces token-level message logs, it works "cleanly" as a data generator inside **TRL's `GPROTrainer`**.

> **Note:** "cleanly" refers to modifications made in our [TRL fork](https://github.com/ASSERT-KTH/trl) to enable direct agent integration. These changes support the [CodeRepairRL](https://github.com/ASSERT-KTH/CodeRepairRL) project but may not be merged into the main HuggingFace repository.

To use it:

* Write a rollout client that wraps `Agent.run()`
* Extract the diff and messages for each training example
* Feed those into TRL's reward modeling or fine-tuning pipelines

This lets you train models that learn to use tools directly, grounded in interaction data — no custom env needed.

---

## Install

```bash
pip install nano-agent  # TODO: publish
```

---

It's not the strongest agent — but it's ideal as a training foundation.

---

## Citation

```
@misc{nano-agent2025,
  author       = {Bjarni Haukur},
  title        = {nano-agent: a minimalist scaffold for agent-in-the-loop training},
  howpublished = {\url{https://github.com/BjarniHaukur/nano-agent}},
  year         = {2025}
}
```
