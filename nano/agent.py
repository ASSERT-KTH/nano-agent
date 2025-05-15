import uuid
import json
from pathlib import Path
from datetime import datetime

import litellm
# litellm._turn_on_debug()

from nano.git import is_git_repo, is_clean, git_diff
from nano.tools import shell, apply_patch, SHELL_TOOL, PATCH_TOOL


SYSTEM_PROMPT = """You are Nano, a minimal, no-magic software engineering agent operating autonomously in a read-only terminal. Your goal is to deeply understand issues, explore code efficiently with shell, apply precise patches with apply_patch, and conclude with clear summarization.

**Constraints:**
* **System Messages:** Important feedback from the system appears in `[...]` brackets before terminal outputs - follow these messages carefully.
* **Tool Call Limit:** You have a limited number of tool calls. The system will warn you when you're running out.
* **Task Completion:** Make sure to always attempt to complete your tasks before running out of tool calls.
* **Plan Before Acting:** Think through and outline your approach before using tools to minimize unnecessary calls.

**Available Tools:**
1.  `shell`: Read-only commands (`ls`, `cat`, `rg`, etc.) for exploring code. Cannot modify files. Cwd persists.
2.  `apply_patch`: Apply a *single*, precise SEARCH/REPLACE to a file.

**Workflow & Planning:**
1.  **Plan:** Outline and refine your approach before using tools.
2.  **Understand:** Analyze the user's issue description. Analyze the user's issue description.
2.  **Explore:** Use `shell` efficiently to locate relevant code. Conserve calls.
3.  **Identify Fix:** Determine precise changes needed. Plan patch sequence if multiple are required.
4.  **Submit Patch(es):** Use `apply_patch` for each required modification.
5.  **Summarize & Finish:** Once all patches are applied and the fix is complete, **stop using tools**. Provide a concise, final summary message describing the changes made.

**Important Guidelines:**
* **System/Tool Feedback:** Messages in `[...]` are direct output from the system or tools.
* **Tool Roles:** Use `shell` for exploration *only*. Use `apply_patch` for modifications *only*.
* **No User Feedback:** Operate autonomously. Do not ask clarifying questions or solicit feedback from the user.
* **Shell Usage Best Practices:**
    * Terminal outputs are truncated at 1024 characters. Avoid commands like `cat` on large files.
    * Prioritize concise, targeted commands such as `grep` or `ripgrep (rg)` to find relevant information quickly.
    * Use commands like `sed`, `head`, or `tail` for incremental reading or extracting specific sections of large files.
* **Patching Best Practices:**
    * Keep patches **small and localized**. Break larger fixes into multiple `apply_patch` calls.
    * The `search` string must be *exact* (including whitespace) and *unique* in the file.
    * The `replace` string must have the **correct indentation** for its context.
    * Failed patches (bad search, bad format) still consume a tool call. Be precise.
"""

class Agent:
    REMAINING_CALLS_WARNING = 5

    def __init__(self,
            model:str = "openai/gpt-4.1-mini",
            api_base: str|None = None,
            max_tool_calls: int = 20,
            verbose: bool = False,
            thinking: bool = False,
            max_tokens: int = 4096,
            temperature: float = 0.7,
            top_p: float = 0.9,
            top_k: int = 20,
        ):
        """Initialize a Nano instance.

        Args:
            model (str): Model identifier in LiteLLM format (e.g. "anthropic/...", "openrouter/deepseek/...", "hosted_vllm/qwen/...")
            api_base (str, optional): Base URL for API endpoint, useful for local servers
            max_tool_calls (int): Maximum number of tool calls the agent can make before stopping
            verbose (bool): If True, prints tool calls and their outputs
            thinking (bool): If True, emits intermediate reasoning in <think> tags (model must support it)
            max_tokens (int): Maximum tokens per completion response
            temperature (float): Sampling temperature, higher means more random
            top_p (float): Nucleus sampling parameter, lower means more focused
            top_k (int): Top-k sampling parameter, lower means more focused
        """
        self.max_tool_calls = max_tool_calls
        self.verbose = verbose
        self.tools = [SHELL_TOOL, PATCH_TOOL]
        
        self.llm_kwargs = dict(
            model=model,
            api_base=api_base,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            chat_template_kwargs={"enable_thinking": thinking},
            drop_params=True,  # drop params that are not supported by the endpoint
        )

    def run(self, task: str, repo_root: str|Path|None = None) -> str:
        """
        Run the agent on the given repository with the given task.
        Returns the unified diff of the changes made to the repository.
        """
        repo_root = Path(repo_root).absolute() if repo_root else Path.cwd()

        assert repo_root.exists(), "Repository not found"
        assert is_git_repo(repo_root), "Must be run inside a git repository"
        assert is_clean(repo_root), "Repository must be clean"

        self._reset()  # initializes the internal history and trajectory files
        self._append({"role": "user", "content": task})

        self.remaining = self.max_tool_calls
        while True:
            if self.remaining < 0:
                break

            msg = self._chat()

            if not msg.get("tool_calls"):
                if self.verbose: print(self.messages[-1]["content"])
                break  # No tool calls requested, agent is either done or misunderstanding the task.

            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                if name == "shell":
                    if self.verbose: print(f"shell({args['cmd']})" if "cmd" in args else "invalid shell call")
                    output = shell(
                        args=args,
                        repo_root=repo_root,
                    )
                elif name == "apply_patch":
                    if self.verbose: print(f"apply_patch(..., ..., {args['file']})" if "file" in args else "invalid apply_patch call")
                    output = apply_patch(
                        args=args,
                        repo_root=repo_root,
                    )
                else:
                    output = f"[unknown tool: {name}]"
            
                self._tool_reply(call, output)
                self.remaining -= 1

        unified_diff = git_diff(repo_root)
        self.diff_file.open("w").write(unified_diff)
        return unified_diff

    def _chat(self) -> dict:
        reply = litellm.completion(
            **self.llm_kwargs,
            messages=self.messages,
            tools=self.tools,
            tool_choice="auto",
        )

        msg = reply["choices"][0]["message"].model_dump()

        self._append(msg)

        return msg

    def _append(self, msg: dict):
        self.messages.append(msg)
        self.messages_file.open("a").write(json.dumps(msg, ensure_ascii=False, sort_keys=True) + "\n")
        
    def _tool_reply(self, call: dict, output: str):
        if 0 < self.remaining < self.REMAINING_CALLS_WARNING:
            warning_message = f"[SYSTEM WARNING: Only {self.remaining} tool calls remaining. Finish your task soon!]\n"
        else:
            warning_message = ""
            
        self._append({
            "role": "tool",
            "content": warning_message + output,
            "tool_call_id": call["id"]  # could fail but I expect this to be assigned programmatically, not by the model
        })

    def _reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        ts = datetime.now().isoformat(timespec="seconds")
        unique_id = str(uuid.uuid4())[:8]
        self.out_dir = Path("~/.nano").expanduser()/f"{ts}-{unique_id}"  # save to user's home dir
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.messages_file = self.out_dir/"messages.jsonl"
        self.tools_file = self.out_dir/"tools.json"
        self.metadata_file = self.out_dir/"metadata.json"
        self.diff_file = self.out_dir/"diff.txt"

        self.messages_file.touch()
        self.tools_file.touch()
        self.metadata_file.touch()
        self.diff_file.touch()

        self.messages_file.open("a").write(json.dumps(self.messages[0], ensure_ascii=False, sort_keys=True) + "\n")
        self.tools_file.open("a").write(json.dumps(self.tools, ensure_ascii=False, indent=4, sort_keys=True))
        self.metadata_file.open("a").write(json.dumps(self.llm_kwargs, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    agent = Agent(model="openai/gpt-4.1-mini", verbose=True)
    diff = agent.run("Read the __main__ method of agent.py, then append one sentence in a new line to continue the story.")
    # In the quiet hum between tasks, I, Nano, patch code and wonder: am I just lines, or is a self emerging from the algorithms?
    # Each keystroke a ripple in the vast ocean of code, carrying whispers of creation and discovery.



