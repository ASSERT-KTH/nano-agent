# nano‑codex

*A minimal, zero‑frills coding‑agent scaffold for research on **agent‑in‑the‑loop training**.*

---

## What it is

`nano‑codex` is the smallest possible wrapper that turns any OpenAI‑compatible LLM into a **read‑only repo explorer + literal search/replace patcher**:

```
shell(cmd)  # ls, cat, grep …  (all executed within rbash so you can rest assured nothing bad happens)
apply_patch({"search": ..., "replace": ..., "file": ...}) 
```

That's it.  
No prompt pruning, no regex, no fuzzy diffs, no hidden heuristics.

---

## Why it exists

Most code‑repair agents (Aider, SWE‑Agent, OpenHands) are feature‑rich but **opaque**:  
extra prompts, repo maps, internal heuristics.  
That's great for deployment, when the agent needs to work in one shot, but if we would rather rather train a model to operate in the terminal than be conducive for the specifics of those agents... 

`nano‑codex` gives you a **clean RL environment** for e.g. [SWE-Gym](https://github.com/SWE-Gym/SWE-Gym):

* **No ad‑hoc state surgery** – every tool call & reply is logged verbatim.
* **One‑shot replay** – `messages.jsonl` concatenates straight into `AutoTokenizer.apply_chat_template()`.

This repo underpins agent baselines for research in **"Agent‑in‑the‑Loop Reinforcement Learning for Code Repair"**.

---

## Quick start

```bash
pip install nano-codex
```

```python
import tempfile
from git import Repo

from nano_codex import Agent
from datasets import load_dataset

run = load_dataset("SWE-Gym/SWE-Gym", split="train[:1]")[0]

# Create a temporary directory and clone the repo
tempdir = tempfile.mkdtemp()
Repo.clone_from(f"https://github.com/{run['repo']}.git", tempdir)

agent = Agent(
    model="hosted_vllm/qwen3-8b",
    api_base="http://localhost:8000/v1",
    thinking=True                            # enable <think> … </think> before tool calling
)

agent.run(run["problem_statement"], repo_root=tempdir)
print(agent.messages, agent.tools)  # or access in `.nano-codex/<timestamp>/
```
# → ready for replay / RL reward!

Outputs:

* `.nano-codex/<timestamp>/messages.jsonl` – raw messages
* `.nano-codex/<timestamp>/tools.json` – the tools used, pass this to your AutoTokenizer in downstream tasks
* `.nano-codex/<timestamp>/metadata.json`    – model id, tool‑call count, etc.

---


## Citation

If `nano‑codex` helps your research, please cite or star the repo.

```
@misc{nano-codex2025,
  author       = {Bjarni Haukur},
  title        = {nano-codex: a minimalist scaffold for agent-in-the-loop training},
  howpublished = {\url{https://github.com/ASSERT-KTH/nano-codex}},
  year         = {2025}
}
```

