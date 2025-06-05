import uuid
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from nano.utils import is_git_repo, is_clean, git_diff, feedback, warning
from nano.tools import (
    apply_patch, list_files, find_files, grep_files, read_lines,
    PATCH_TOOL, LIST_FILES_TOOL, FIND_FILES_TOOL, GREP_FILES_TOOL, READ_LINES_TOOL
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


SYSTEM_PROMPT = """You are Nano, an expert software engineering agent with specialized tools for code exploration and modification.

## Available Tools
1. **list_files** - List directory contents with file sizes
2. **find_files** - Find files by name pattern  
3. **grep_files** - Search code content with regex
4. **read_lines** - Read specific line ranges
5. **apply_patch** - Modify code with search/replace

## Workflow
1. **Discover** - Find relevant files using identifiers from the problem description
2. **Analyze** - Read code to understand implementations and patterns
3. **Plan** - Design changes that fit naturally with existing code
4. **Execute** - Apply minimal, precise modifications

## Search Strategy
- Extract key identifiers: class names, function names, error messages, file paths
- Start with specific patterns, broaden if needed
- Use grep_files for content search, find_files for name patterns
- Read only the specific sections you need to modify

## Tool Guidelines
- **list_files**: Explore directory structure when unsure where to look
- **find_files**: Locate files by name pattern with wildcards
- **grep_files**: Search code content across multiple files/directories
- **read_lines**: Read specific line ranges after finding matches
- **apply_patch**: Include 3-5 lines of unique context for reliable matching

## Important
- <nano:feedback> tags provide informational messages
- <nano:warning> tags require immediate action - apply your best fix
- Complete most tasks in 15-20 tool calls
- If searches fail repeatedly, the code may use different names or not exist

You operate in a continuous loop. Each tool provides information that guides your next action."""


class Agent:
    REMAINING_CALLS_WARNING = 5
    TOKENS_WRAP_UP = 3000  # Start preparing to finish
    TOKENS_CRITICAL = 1500  # Critical token level, finish immediately
    MINIMUM_TOKENS = 600  # If we're below this, exit the loop on the next iteration
    TOOL_TRUNCATE_LENGTH = 500 * 4  # 4 characters ~= 1 token, so 2000 chars ~= 500 tokens

    def __init__(self,
            model:str = "openai/gpt-4.1-mini",
            api_base: Optional[str] = None,
            token_limit: int = 8192,
            tool_limit: int = 20,
            response_limit: int = 4096,
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
        
        self.tools = [PATCH_TOOL, LIST_FILES_TOOL, FIND_FILES_TOOL, GREP_FILES_TOOL, READ_LINES_TOOL]
        
        self.llm_kwargs = dict(
            model=model,
            api_base=api_base,
            temperature=temperature,
            top_p=top_p,
        )
        if not model.startswith(("openai/", "anthropic/")):  # most endpoints except these support these params
            self.llm_kwargs.update(dict(
                top_k=top_k,
                min_p=min_p,
                chat_template_kwargs={"enable_thinking": thinking},
            ))

    @property
    def token_usage(self):
        """Return the total token count used (accurate up to the last tool call)."""
        return self.token_limit - getattr(self, "remaining_tokens", self.token_limit)
    
    @property
    def tool_usage(self):
        """Return the number of tool calls made."""
        return self.tool_limit - getattr(self, "remaining_tool_calls", self.tool_limit)
        
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
                if not is_clean(repo_root): break  # the agent has made changes, and didn't request any more tools so it is done
                # the agent hasn't made changes, so we remind it to operate autonomously
                self._append({"role": "user", "content": warning("No tools called. Use grep_files to search for code or apply_patch to fix the issue.")})
                continue

            for call in msg["tool_calls"]:  
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"])
                except json.JSONDecodeError as e:
                    output = warning(f"Malformed tool arguments JSON: {e}")
                    self._tool_reply(call, output)
                    self.remaining_tool_calls -= 1
                    continue

                if name == "list_files":
                    output = list_files(args=args, repo_root=repo_root, verbose=self.verbose)
                    
                elif name == "find_files":
                    output = find_files(args=args, repo_root=repo_root, verbose=self.verbose)

                elif name == "apply_patch":
                    output = apply_patch(args=args, repo_root=repo_root, verbose=self.verbose)
                    
                elif name == "grep_files":
                    output = grep_files(args=args, repo_root=repo_root, verbose=self.verbose)
                    
                elif name == "read_lines":
                    output = read_lines(args=args, repo_root=repo_root, verbose=self.verbose)

                else:
                    output = warning(f"unknown tool: {name}")
            
                self._tool_reply(call, output)
                self.remaining_tool_calls -= 1

        unified_diff = git_diff(repo_root)
        if self.log: self.diff_file.open("w").write(unified_diff)
        if self.verbose: print(f"\nFinal token count: {self.token_usage}")
        return unified_diff

    def _chat(self) -> dict:
        # Dynamic response sizing to prevent context window errors
        # Use remaining_tokens which accounts for thinking tokens
        safety_buffer = int(self.token_limit * 0.1)  # 10% safety margin
        available = max(0, self.remaining_tokens - safety_buffer)
        
        litellm = _get_litellm()  # Lazy load and cache
        reply = litellm.completion(
            **self.llm_kwargs,
            max_tokens=max(256, min(self.response_limit, available // 2)),
            messages=self.messages,
            tools=self.tools,
            tool_choice="auto",
        )

        msg = reply["choices"][0]["message"].model_dump()

        self._append(msg)

        # Calculate actual token usage including reasoning tokens for thinking models (not included in total_tokens)
        usage = reply["usage"].model_dump()
        normal_tokens = usage["total_tokens"]
        completion_info = usage.get("completion_tokens_details", {}) or {}
        reasoning_tokens = completion_info.get("reasoning_tokens", 0)
        self.remaining_tokens = self.token_limit - normal_tokens - reasoning_tokens

        return msg

    def _append(self, msg: dict):
        self.messages.append(msg)

        if not self.log:
            return

        self.messages_file.open("a").write(json.dumps(msg, ensure_ascii=False, sort_keys=True) + "\n")
        
    def _tool_reply(self, call: dict, output: str):
        # Apply truncation if output is too long
        if len(output) > self.TOOL_TRUNCATE_LENGTH:
            output = output[:self.TOOL_TRUNCATE_LENGTH] + feedback("output truncated")
        
        # ordered by priority
        if self.remaining_tokens < self.TOKENS_CRITICAL:
            warning_message = warning("Token limit critical. Apply your best fix now.")
        elif self.remaining_tokens < self.TOKENS_WRAP_UP:
            warning_message = warning("Tokens low. Focus on the main issue only.")
        elif 1 < self.remaining_tool_calls < self.REMAINING_CALLS_WARNING:
            warning_message = warning(f"{self.remaining_tool_calls} tools left. Prioritize essential changes.")
        elif self.remaining_tool_calls == 1:
            warning_message = warning("Last tool call. Make it count.")
        else:
            warning_message = ""
            
            
        self._append({
            "role": "tool",
            "content": warning_message + output,
            "tool_call_id": call["id"]  # could fail but I expect this to be assigned programmatically by the inference provider, not by the model
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
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
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