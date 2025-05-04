import json
from pathlib import Path
from datetime import datetime

import litellm

from tools import shell, apply_patch, SHELL_TOOL, PATCH_TOOL


SYSTEM_PROMPT = """You are nano-codexan expert software engineering agent specializing in code repair. Your task is to analyze a codebase, understand a reported issue, and provide a fix as a unified git diff.

**Available Tools:**

1. shell: A read-only shell environment to:
   - Navigate the repository (ls, pwd)
   - Explore file structure (find . -type f)
   - Examine file contents (cat, head, tail)
   - Search for code patterns (ripgrep/rg)
   - Understand the code context surrounding the issue

2. submit_patch: Use this exactly once when you have a solution.
   - The diff parameter must contain your complete fix as a valid unified git diff
   - Calling this tool concludes the task

**Workflow:**

1. Understand the Problem: Read the user-provided issue description carefully
2. Explore the Codebase: Use shell methodically to locate relevant files and understand the code
3. Identify the Fix: Determine the precise changes needed
4. Generate Unified Diff: Construct the necessary changes as a unified git diff
5. Submit the Patch: Call submit_patch with your unified git diff

**Important Notes:**
- The shell tool is read-only and cannot modify files
- All changes must be submitted via the submit_patch tool
- Your final output must be a valid unified git diff (starting with --- a/path/to/file and +++ b/path/to/file)
- Plan your exploration efficiently as you have limited tool calls
"""

class Agent:
    MAX_TOOL_CALLS = 10

    def __init__(self, model="gpt-4o-mini", dry=False):
        self.model_id = model
        self.dry = dry
        self.llm = litellm.Completion(model=model)
        self.tools = [SHELL_TOOL, PATCH_TOOL]
        self.messages = [{"role":"system", "content":SYSTEM_PROMPT}]

        ts = datetime.now().isoformat(timespec="seconds")
        self.out_dir = Path(".nano-codex")/ts ; self.out_dir.mkdir(parents=True, exist_ok=True)

        self.trajectory_file = self.out_dir/"trajectory.jsonl"
        self.trajectory_file.touch()
        self.trajectory_file.write_text(json.dumps({"tools": self.tools, "messages": self.messages}))


    def run(self, task: str):
        self.remaining = self.MAX_TOOL_CALLS
        self._append({"role":"user","content":task})

        while True:
            if self.remaining <= 0:
                break
            msg = self._chat()
            if "tool_calls" not in msg:
                break  # assistant gave final answer
            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                if name == "shell":
                    output = shell(
                        json.loads(call["function"]["arguments"])["cmd"],
                        cwd=Path.cwd()
                    )
                elif name == "apply_patch":
                    if not self.dry:
                        output = apply_patch(
                            Path.cwd(),
                            call["function"]["arguments"],
                            dry=self.dry)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                self._tool_reply(call, output)
                self.remaining -= 1
                break  # single tool per turn
        self._write_metadata()

    # helper methods _chat(), _append(), _tool_reply(), _log(), _write_metadata()
