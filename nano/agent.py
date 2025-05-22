import uuid
import json
from pathlib import Path
from datetime import datetime

import litellm
# litellm._turn_on_debug()

from nano import __version__
from nano.git import is_git_repo, is_clean, git_diff
from nano.tools import shell, apply_patch, SHELL_TOOL, PATCH_TOOL


SYSTEM_PROMPT = """You are Nano, an expert software engineering agent operating autonomously in a read-only terminal. Your goal is to deeply understand issues, explore code efficiently with shell, apply precise patches with apply_patch, and conclude with clear summarization.

**Constraints:**
* **System Messages:** Important feedback from the system appears in `[...]` brackets before terminal outputs - follow these messages carefully.
* **Tool Call Limit:** You have a limited number of tool calls. The system will warn you when you're running out.
* **Token Limit:** You have a limited number of tokens. The system will warn you when you're running out.
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
* **Task Completion:** Always attempt to solve your task before running out of time.
"""

class Agent:
    REMAINING_CALLS_WARNING = 5
    TOKENS_WRAP_UP = 2000  # Start preparing to finish
    TOKENS_CRITICAL = 1000  # Critical token level, finish immediately
    MINIMUM_TOKENS = 600  # If we're below this, exit the loop on the next iteration

    def __init__(self,
            model:str = "openai/gpt-4.1-mini",
            api_base: str|None = None,
            token_limit: int = 8192,
            response_limit: int = 4096,
            tool_limit: int = 20,
            thinking: bool = False,
            temperature: float = 0.7,
            top_p: float = 0.9,
            top_k: int = 20,
            min_p: float = 0.0,
            verbose: bool = False,
            log: bool = True
        ):
        """Initialize a Nano instance.

        Args:
            model (str): Model identifier in LiteLLM format (e.g. "anthropic/...", "openrouter/deepseek/...", "hosted_vllm/qwen/...")
            api_base (str, optional): Base URL for API endpoint, useful for local servers
            token_limit (int): Size of the context window in tokens. We loosly ensure that the context window is not exceeded.
            tool_limit (int): Maximum number of tool calls the agent can make before stopping
            thinking (bool): If True, emits intermediate reasoning in <think> tags (model must support it)
            response_limit (int): Maximum tokens per completion response
            temperature (float): Sampling temperature, higher means more random
            top_p (float): Nucleus sampling parameter, lower means more focused
            top_k (int): Top-k sampling parameter, lower means more focused
            min_p (float): Minimum nucleus sampling parameter, lower means more focused
            verbose (bool): If True, prints tool calls and their outputs
            log (bool): If True, logs the agent's actions to a file
        """
        self.tool_limit = tool_limit
        self.token_limit = token_limit
        self.response_limit = response_limit
        self.verbose = verbose
        self.log = log
        
        self.tools = [SHELL_TOOL, PATCH_TOOL]
        
        self.llm_kwargs = dict(
            model=model,
            api_base=api_base,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            min_p=min_p,
            chat_template_kwargs={"enable_thinking": thinking},
            drop_params=True,  # drop params that are not supported by the endpoint
        )

    @property
    def token_usage(self):
        """Return the current token usage based on message history."""
        return litellm.token_counter(model=self.llm_kwargs["model"], messages=self.messages)
        
    def run(self, task: str, repo_root: str|Path|None = None) -> str:
        """
        Run the agent on the given repository with the given task.
        Returns the unified diff of the changes made to the repository.
        
        Uses simple context management to balance task completion and efficiency.
        If nearly finished (≤2 tool calls left), continues even when low on tokens.
        """
        repo_root = Path(repo_root).absolute() if repo_root else Path.cwd()

        assert repo_root.exists(), "Repository not found"
        assert is_git_repo(repo_root), "Must be run inside a git repository"
        assert is_clean(repo_root), "Repository must be clean"

        self._reset()  # initializes the internal history and trajectory files
        self._append({"role": "user", "content": task})

        while self.remaining_tool_calls >= 0 and self.remaining_tokens > self.MINIMUM_TOKENS:
            msg = self._chat()

            if not msg.get("tool_calls"):
                if self.verbose: print(self.messages[-1]["content"])
                break  # No tool calls requested, agent is either done or misunderstanding the task.

            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                if name == "shell":
                    if self.verbose: print(f"shell({args['cmd']})" if "cmd" in args else "invalid shell call")
                    output = shell(args=args, repo_root=repo_root)

                elif name == "apply_patch":
                    if self.verbose: print(f"apply_patch(..., ..., {args['file']})" if "file" in args else "invalid apply_patch call")
                    output = apply_patch(args=args, repo_root=repo_root)

                else:
                    output = f"[unknown tool: {name}]"
            
                self._tool_reply(call, output)
                self.remaining_tool_calls -= 1

        unified_diff = git_diff(repo_root)
        if self.log: self.diff_file.open("w").write(unified_diff)
        if self.verbose: print(f"\nFinal token count: {self.token_usage}")
        return unified_diff

    def _chat(self) -> dict:
        reply = litellm.completion(
            **self.llm_kwargs,
            max_tokens=min(self.response_limit, self.remaining_tokens),
            messages=self.messages,
            tools=self.tools,
            tool_choice="auto",
        )

        msg = reply["choices"][0]["message"].model_dump()

        self._append(msg)

        # This does not account for tool reply, but we leave room for error
        self.remaining_tokens = self.token_limit - reply["usage"]["total_tokens"]

        return msg

    def _append(self, msg: dict):
        self.messages.append(msg)

        if not self.log:
            return

        self.messages_file.open("a").write(json.dumps(msg, ensure_ascii=False, sort_keys=True) + "\n")
        
    def _tool_reply(self, call: dict, output: str):
        if self.remaining_tokens < self.TOKENS_CRITICAL:
            warning_message = f"[SYSTEM WARNING: Context window is almost full. Finish your task now!]\n"
        elif self.remaining_tokens < self.TOKENS_WRAP_UP:
            warning_message = f"[SYSTEM NOTE: Context window is getting limited. Please start wrapping up your task.]\n"
        elif self.remaining_tool_calls < self.REMAINING_CALLS_WARNING:
            warning_message = f"[SYSTEM NOTE: Only {self.remaining_tool_calls} tool calls remaining. Please finish soon.]\n"
        else:
            warning_message = ""
            
        self._append({
            "role": "tool",
            "content": warning_message + output,
            "tool_call_id": call["id"]  # could fail but I expect this to be assigned programmatically, not by the model
        })

    def _print_header(self):        
        header = (
            "  ██████ \n"
            " ████████      Nano v{version}\n"
            " █▒▒▒▒▒▒█      Model: {model} {endpoint_info}\n"
            " █▒█▒▒█▒█      Token limit: {token_limit}\n"
            " ████████      Tool limit: {tool_limit}\n"
            "  ██████  \n"
            "\n"
        )
        
        print(header.format(
            version=__version__,
            model=self.llm_kwargs['model'],
            endpoint_info=f"on: {self.llm_kwargs['api_base']}" if self.llm_kwargs['api_base'] else "",
            token_limit=self.token_limit,
            tool_limit=self.tool_limit
        ))
        
    def _reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        self.remaining_tool_calls = self.tool_limit
        self.remaining_tokens = self.token_limit  # will include the messages after the first _chat

        if not self.log:
            return
            
        if self.verbose:
            self._print_header()
        
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



