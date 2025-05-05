import json
from pathlib import Path
from datetime import datetime

import litellm

from nano_codex.git import is_git_repo
from tools import shell, apply_patch, SHELL_TOOL, PATCH_TOOL


SYSTEM_PROMPT = """You are nano-codex, an expert software engineering agent specializing in code repair.
Your task is to analyze a codebase, understand a reported issue, and then provide a fix.

**Available Tools:**

1. shell: A read-only shell environment to:
   - Navigate the repository (ls, pwd)
   - Explore file structure (find . -type f)
   - Examine file contents (cat, head, tail)
   - Search for code patterns (ripgrep/rg)
   - Understand the code context surrounding the issue

2. apply_patch: Use this when you have a solution.
   - Takes an array of patches, each containing:
     - search: The exact string to find (must appear exactly once in file)
     - replace: The string to replace it with
     - file: Path to the file to modify
   - Changes are applied as search/replace operations
   - Returns a git diff showing applied changes

**Workflow:**

1. Understand the Problem: Read the user-provided issue description carefully
2. Explore the Codebase: Use shell methodically to locate relevant files and understand the code
3. Identify the Fix: Determine the precise changes needed
4. Submit Patches: Call apply_patch with your search/replace patches to implement the fix

**Important Notes:**
- The shell tool is read-only and cannot modify files
- All changes must be submitted via the apply_patch tool
- Each search string must appear exactly once in the target file
- Be extremely careful with whitespace and indentation in your search/replace strings
- Plan your exploration efficiently as you have limited tool calls
"""

class Agent:
    MAX_TOOL_CALLS = 10

    def __init__(self, model:str = "openai/gpt-4.1-mini", api_base: str|None = None, thinking: bool = False, temperature: float = 0.7):
        """
        Initialize the agent with the given model and configuration.

        Args:
            model (str): The model to use for the agent. LiteLLM syntax (e.g. "anthropic/...", "openrouter/deepseek/...", "hosted_vllm/qwen/...")
            api_base (Optional[str]): For plugging in a local server (e.g. "http://localhost:8000/v1")
        """
        self.model_id = model
        self.api_base = api_base
        self.thinking = thinking

        self.tools = [SHELL_TOOL, PATCH_TOOL]
        
        self.llm_kwargs = dict(
            model=self.model_id,
            api_base=self.api_base,
            temperature=temperature,
            chat_template_kwargs={"enable_thinking": thinking}
        )

        self._reset()

    def _reset(self):
        self.remaining = self.MAX_TOOL_CALLS
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        ts = datetime.now().isoformat(timespec="seconds")
        self.out_dir = Path(".nano-codex")/ts ; self.out_dir.mkdir(parents=True, exist_ok=True)

        self.messages_file = self.out_dir/"messages.jsonl"
        self.tools_file = self.out_dir/"tools.json"
        self.messages_file.touch()
        self.tools_file.touch()

        self.messages_file.open("a").write(json.dumps(self.messages[0], ensure_ascii=False) + "\n")
        self.tools_file.open("a").write(json.dumps(self.tools, ensure_ascii=False, indent=4))

    def run(self, repo_root: str|Path, task: str):
        cwd = repo_root = Path(repo_root)

        assert cwd.exists(), "Repository not found"
        assert is_git_repo(cwd), "Must be run inside a git repository"
        
        self.remaining = self.MAX_TOOL_CALLS
        self._append({"role": "user", "content": task})

        while True:
            if self.remaining <= 0:
                break

            msg = self._chat()

            assert "tool_calls" in msg, "Assistant returned plain text without tool calls"
            assert len(msg["tool_calls"]) == 1, "Assistant returned multiple tool calls"

            call = msg["tool_calls"][0]
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])

            if name == "shell":
                output, cwd = shell(
                    args["cmd"],
                    cwd=cwd,
                    repo_root=repo_root,
                    remaining_tool_calls=self.remaining,
                )
            elif name == "apply_patch":
                unified_diff = apply_patch(
                    repo_root,
                    args["patches"],
                )
                return unified_diff
            else:
                raise ValueError(f"Unknown tool: {name}")
            
            self._tool_reply(call, output)
            self.remaining -= 1

        self._reset()

    def _chat(self) -> dict:
        reply = litellm.completions(
            **self.llm_kwargs,
            messages=self.messages,
            tools=self.tools,
            tool_choice="auto",
            max_tokens=4096
        )

        msg = reply["choices"][0]["message"]

        if self.thinking and (reasoning := msg.pop("reasoning_content", None)):
            self._append({
                "role": "assistant",
                "content": reasoning,
                "name": "reasoning"          # optional tag; ignored by templates
            })


        self._append(msg)

        return msg

    def _log(self, obj: dict):
        self.messages_file.open("a").write(
            json.dumps(obj, ensure_ascii=False) + "\n")

    def _append(self, msg: dict):
        self.messages.append(msg)
        self._log({"message": msg})
        
    def _tool_reply(self, call: dict, output: str):
        self._append({
            "role": "tool",
            "content": output,
            "tool_call_id": call["id"]
        })
