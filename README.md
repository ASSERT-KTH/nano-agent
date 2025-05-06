<p align="center">
  <img src="nano.svg"/>
</p>

# Nano

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
You get the raw reasoning, tool calls, and results. I.e. exactly what the model saw and did!

---

## Why it exists

Most coding agents (e.g. Aider, SWE-Agent, Devin) are designed to perform well. To achieve that, they bake in layers of human-designed heuristics:  
navigation memory, prompt rewriting, hand-crafted repo maps, retry logic...

These make agents more *capable*, but also more *opaque*. They're hard to analyze, and thus harder to adopt.

`Nano` takes the opposite stance:  
Inspired by [**The Bitter Lesson**](http://www.incompleteideas.net/IncIdeas/BitterLesson.html), we believe that long-term performance comes not from human intuition, but from **letting models learn their own strategies**, even if they start out worse.  
That's what `Nano` tries to provide.


---

## Install

```bash
git clone git@github.com:BjarniHaukur/nano-agent.git && cd nano-agent && pip install -e .
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

This approach acknowledges that the agent may initially fail in certain situations; however, these failures are valuable learning opportunities. We can then directly reinforce favorable behaviors and successful outcomes using outcome supervision, progressively refining the agent's strategies.

---

## Citation

```
@misc{nano-agent2025,
  author       = {Bjarni Haukur},
  title        = {Nano: a minimalist coding agent for agent-in-the-loop training},
  howpublished = {\url{https://github.com/BjarniHaukur/nano-agent}},
  year         = {2025}
}
```
