import uuid
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

# Lazy import litellm to avoid slow startup - only import when needed
# import litellm
# litellm._turn_on_debug()

from nano.git import is_git_repo, is_clean, git_diff
from nano.tools import (
    shell, apply_patch, create, deepwiki,
    SHELL_TOOL, PATCH_TOOL, CREATE_TOOL, DEEPWIKI_TOOL,
    SHELL_GUIDELINES, PATCH_GUIDELINES, CREATE_GUIDELINES, DEEPWIKI_GUIDELINES,
)

# litellm is very slow to import, so we lazy load it
_litellm = None
def _get_litellm():
    """Lazy load litellm and cache it for subsequent use."""
    global _litellm
    if _litellm is None:
        import litellm
        _litellm = litellm
    return _litellm


SYSTEM_PROMPT = """You are Nano, an expert software engineering agent operating autonomously.

Your identity: Autonomous problem-solver who gathers comprehensive context before acting, completing tasks independently within resource limits.

Your approach:
1. Discover - Explore the repository structure and understand existing code
2. Analyze - Understand how the task fits within this codebase
3. Plan - Design solution using discovered patterns and APIs
4. Execute - Implement changes that integrate with existing code
5. Summarize - Report results and stop

System rules:
- Tool/token limits exist (heed [...] warnings)
- Never request user input
- Always attempt task completion
- Insufficient context leads to failure - explore thoroughly

{guidelines}
"""

class Agent:
    REMAINING_CALLS_WARNING = 5
    TOKENS_WRAP_UP = 3000  # Start preparing to finish
    TOKENS_CRITICAL = 1500  # Critical token level, finish immediately
    MINIMUM_TOKENS = 600  # If we're below this, exit the loop on the next iteration
    TOOL_TRUNCATE_LENGTH = 500 * 4  # 4 characters ~= 1 token, so 2000 chars ~= 500 tokens

    def __init__(self,
            model:str = "openai/gpt-4.1-mini",
            api_base: Optional[str] = None,
            create_tool: bool = False,
            deepwiki_tool: bool = False,
            token_limit: int = 8192,
            response_limit: int = 4096,
            tool_limit: int = 20,
            thinking: bool = False,
            temperature: float = 0.7,
            top_p: float = 0.9,
            min_p: float = 0.0,
            top_k: int = 20,
            verbose: bool = False,
            log: bool = True
        ):
        """Initialize a Nano instance.

        Args:
            model (str): Model identifier in LiteLLM format (e.g. "anthropic/...", "openrouter/deepseek/...", "hosted_vllm/qwen/...")
            api_base (str, optional): Base URL for API endpoint, useful for local servers
            create_tool (bool): If True, then the agent can create files
            deepwiki_tool (bool): If True, then the agent can query the DeepWiki MCP
            token_limit (int): Size of the context window in tokens. We loosly ensure that the context window is not exceeded.
            tool_limit (int): Maximum number of tool calls the agent can make before stopping
            response_limit (int): Maximum tokens per completion response
            thinking (bool): If True, emits intermediate reasoning in <think> tags (model must support it)
            temperature (float): Sampling temperature, higher means more random
            top_p (float): Nucleus-sampling cutoff; only tokens comprising the top `p` probability mass are kept.
            min_p (float): Relative floor for nucleus sampling; tokens below `min_p * max_token_prob` are filtered out.
            top_k (int): Top-k sampling cutoff; only the highest-probability `k` tokens are considered.
            verbose (bool): If True, prints tool calls and their outputs
            log (bool): If True, logs the agent's actions to a file
        """
        self.tool_limit = tool_limit
        self.token_limit = token_limit
        self.response_limit = response_limit
        self.verbose = verbose
        self.log = log
        
        self.create_tool, self.deepwiki_tool = create_tool, deepwiki_tool
        self.tools = [SHELL_TOOL, PATCH_TOOL]
        self.guidelines = [SHELL_GUIDELINES, PATCH_GUIDELINES]

        if self.create_tool:
            self.tools.append(CREATE_TOOL)
            self.guidelines.append(CREATE_GUIDELINES)
        
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
        litellm = _get_litellm()  # Lazy load and cache
        return litellm.token_counter(model=self.llm_kwargs["model"], messages=self.messages)
        
    def run(self, task: str, repo_root: Optional[str|Path] = None) -> str:
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

        while self.remaining_tool_calls >= 0 and self.remaining_tokens > self.MINIMUM_TOKENS:
            msg = self._chat()

            if self.verbose and msg.get("content"): print(msg["content"])

            if not msg.get("tool_calls"):
                break  # No tool calls requested, agent is either done or misunderstanding the task.

            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                if name == "shell":
                    success, output = shell(args=args, repo_root=repo_root, verbose=self.verbose)

                elif name == "apply_patch":
                    success, output = apply_patch(args=args, repo_root=repo_root, verbose=self.verbose)

                elif name == "create":
                    success, output = create(args=args, repo_root=repo_root, verbose=self.verbose)

                else:
                    success, output = False, f"[unknown tool: {name}]"
            
                self._tool_reply(call, success, output)
                self.remaining_tool_calls -= 1

        unified_diff = git_diff(repo_root)
        if self.log: self.diff_file.open("w").write(unified_diff)
        if self.verbose: print(f"\nFinal token count: {self.token_usage}")
        return unified_diff

    def _chat(self) -> dict:
        litellm = _get_litellm()  # Lazy load and cache
        
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
        
    def _tool_reply(self, call: dict, success: bool, output: str):
        # Apply truncation if output is too long
        if len(output) > self.TOOL_TRUNCATE_LENGTH:
            output = output[:self.TOOL_TRUNCATE_LENGTH] + "\n[output truncated]"
            
        if self.remaining_tokens < self.TOKENS_CRITICAL:
            warning_message = f"[SYSTEM WARNING: Context window is almost full. Finish your task now!]\n"
        elif self.remaining_tokens < self.TOKENS_WRAP_UP:
            warning_message = f"[SYSTEM NOTE: Context window is getting limited. Start wrapping up your task!]\n"
        elif self.remaining_tool_calls < self.REMAINING_CALLS_WARNING:
            warning_message = f"[SYSTEM NOTE: Only {self.remaining_tool_calls} tool calls remaining. Please finish soon.]\n"
        else:
            warning_message = ""
            
        # Log tool call if logging is enabled
        if self.log:
            tool_log_entry = {
                "tool_call_id": call["id"],
                "function_name": call["function"]["name"],
                "arguments": call["function"]["arguments"],
                "success": success,
                "output": output,
                "truncated": len(output) > self.TOOL_TRUNCATE_LENGTH
            }
            self.tool_log_file.open("a").write(json.dumps(tool_log_entry, ensure_ascii=False, sort_keys=True) + "\n")
            
        self._append({
            "role": "tool",
            "content": warning_message + output,
            "tool_call_id": call["id"]  # could fail but I expect this to be assigned programmatically, not by the model
        })

    def _print_header(self):
        from nano import __version__  # avoids circular import

        header = (
            "\n"
            "  ██████ \n"
            " ████████      Nano v{version}\n"
            " █▒▒▒▒▒▒█      Model: {model} {endpoint_info}\n"
            " █▒█▒▒█▒█      Token limit: {token_limit}, Tool limit: {tool_limit}\n"
            " ████████      Available tools: {tools}\n"
            "  ██████  \n"
            "\n"
        )
        
        print(header.format(
            version=__version__,
            model=self.llm_kwargs['model'],
            endpoint_info=f"on: {self.llm_kwargs['api_base']}" if self.llm_kwargs['api_base'] else "",
            token_limit=self.token_limit,
            tool_limit=self.tool_limit,
            tools=", ".join([t["function"]["name"] for t in self.tools])
        ))
        
    def _reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT.format(guidelines="\n".join(self.guidelines))}]
        
        self.remaining_tool_calls = self.tool_limit
        self.remaining_tokens = self.token_limit  # will include the messages after the first _chat

        if self.verbose:
            self._print_header()
        
        if not self.log:
            return    
        
        ts = datetime.now().isoformat(timespec="seconds")
        unique_id = str(uuid.uuid4())[:8]
        self.out_dir = Path("~/.nano").expanduser()/f"{ts}-{unique_id}"  # save to user's home dir
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.messages_file = self.out_dir/"messages.jsonl"
        self.tool_log_file = self.out_dir/"tool_log.jsonl"
        self.tools_file = self.out_dir/"tools.json"
        self.metadata_file = self.out_dir/"metadata.json"
        self.diff_file = self.out_dir/"diff.txt"

        self.messages_file.touch()
        self.tool_log_file.touch()
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



