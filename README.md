# Nano
<p align="center">
  <img
    src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHNoYXBlLXJlbmRlcmluZz0iY3Jpc3BFZGdlcyIgdmlld0JveD0iMCAtMC41IDMwIDIxIiB3aWR0aD0iMjQwIiBoZWlnaHQ9IjE2OCI+PHBhdGggc3Ryb2tlPSIjMjgyODI4IiBkPSJNMCwwaDMwTTAsMWgzME0wLDJoMTJNMTgsMmgxMk0wLDNoMTFNMTksM2gxMU0wLDRoMTFNMTksNGgxMU0wLDVoMTFNMTksNWgxMU0wLDZoMTFNMTksNmgxMU0wLDdoMTJNMTgsN2gxMk0wLDhoMTNNMTcsOGgxM00wLDloMTFNMTksOWgxMU0wLDEwaDExTTEyLDEwaDFNMTcsMTBoMU0xOSwxMGgxMU0wLDExaDEzTTE0LDExaDJNMTcsMTFoMTNNMCwxMmgzME0wLDEzaDMwTTAsMTRoMk0zLDE0aDNNNywxNGgzTTExLDE0aDFNMTYsMTRoMU0xOCwxNGgzTTIyLDE0aDFNMjgsMTRoMk0wLDE1aDNNNCwxNWgyTTgsMTVoMk0xMSwxNWgxTTEzLDE1aDJNMTYsMTVoMU0xOSwxNWgyTTIyLDE1aDFNMjQsMTVoM00yOCwxNWgyTTAsMTZoNE01LDE2aDFNNywxNmgxTTksMTZoMU0xMSwxNmgxTTE2LDE2aDFNMTgsMTZoMU0yMCwxNmgxTTIyLDE2aDFNMjQsMTZoM00yOCwxNmgyTTAsMTdoM000LDE3aDJNNywxN2gyTTExLDE3aDFNMTMsMTdoMk0xNiwxN2gxTTE4LDE3aDJNMjIsMTdoMU0yNCwxN2gzTTI4LDE3aDJNMCwxOGgyTTMsMThoM003LDE4aDNNMTEsMThoMU0xMywxOGgyTTE2LDE4aDFNMTgsMThoM00yMiwxOGgxTTI4LDE4aDJNMCwxOWgzME0wLDIwaDMwIi8+PHBhdGggc3Ryb2tlPSIjMDAwMDAwIiBkPSJNMTIsMmg2TTExLDNoOE0xMSw0aDFNMTgsNGgxTTExLDVoMU0xMyw1aDFNMTYsNWgxTTE4LDVoMU0xMSw2aDhNMTIsN2g2TTEzLDhoNE0xMSw5aDhNMTEsMTBoMU0xMywxMGg0TTE4LDEwaDFNMTMsMTFoMU0xNiwxMWgxIi8+PHBhdGggc3Ryb2tlPSIjNjZmZjY2IiBkPSJNMTIsNGg2TTEyLDVoMU0xNCw1aDJNMTcsNWgxTTIsMTRoMU02LDE0aDFNMTAsMTRoMU0xMiwxNGg0TTE3LDE0aDFNMjEsMTRoMU0yMywxNGg1TTMsMTVoMU02LDE1aDJNMTAsMTVoMU0xMiwxNWgxTTE1LDE1aDFNMTcsMTVoMk0yMSwxNWgxTTIzLDE1aDFNMjcsMTVoMU00LDE2aDFNNiwxNmgxTTgsMTZoMU0xMCwxNmgxTTEyLDE2aDRNMTcsMTZoMU0xOSwxNmgxTTIxLDE2aDFNMjMsMTZoMU0yNywxNmgxTTMsMTdoMU02LDE3aDFNOSwxN2gyTTEyLDE3aDFNMTUsMTdoMU0xNywxN2gxTTIwLDE3aDJNMjMsMTdoMU0yNywxN2gxTTIsMThoMU02LDE4aDFNMTAsMThoMU0xMiwxOGgxTTE1LDE4aDFNMTcsMThoMU0yMSwxOGgxTTIzLDE4aDUiLz48L3N2Zz4"
    width="240" height="168"
    alt="Nano Logo"
  />
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
