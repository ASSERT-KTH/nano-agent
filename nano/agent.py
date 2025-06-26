import uuid
import json
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from nano.utils import is_git_repo, is_clean, git_diff, feedback, warning   
from nano.tools import shell, apply_patch, SHELL_TOOL, PATCH_TOOL, ToolStats

# litellm is very slow to import, so we lazy load it
_litellm = None
def _get_litellm():
    """Lazy load litellm and cache it for subsequent use."""
    global _litellm
    if _litellm is None:
        import litellm
        _litellm = litellm
    return _litellm


SYSTEM_PROMPT = """You are Nano, an expert software engineering agent operating autonomously in a terminal.

## Available Tools
You have two tools: `shell` for executing terminal commands and `apply_patch` for making code changes.

## Workflow
1. **Discover** - Explore repository structure, find relevant files, understand architecture
2. **Analyze** - Read code to understand implementations, APIs, patterns
3. **Plan** - Design solutions that fit naturally with existing code
4. **Execute** - Apply minimal, precise changes following discovered patterns

## Tool Usage Principles
- **Deliberate action**: Each tool call should serve a clear purpose
- **State your intent**: Always declare what you aim to accomplish before each tool call
- **Choose efficiently**: Prefer concise commands that extract specific information
- **Terminal outputs are truncated**: Avoid commands that generate large outputs

**Shell guidelines:**
- Find by identifier: `rg -l 'ClassName|function_name|error_text'`
- Narrow searches: `rg -n 'pattern' path/to/likely/dir --type py`
- View context: `sed -n '10,20p' file` or `grep -B5 -A5 'pattern' file`
- Check structure: `ls -la specific/dir/` before broad exploration.

**Patch guidelines:**
- Each patch must be atomic with unique search strings
- Maintain exact whitespace and correct indentation

## Operating Environment
- Cannot ask questions or seek clarification
- Learn only from command outputs, errors, and files
- Monitor remaining tools/tokens and adapt strategy
- <nano:feedback> tags provide informational messages from your environment
- <nano:warning> tags signal issues requiring immediate action or strategy change

You exist in a continuous loop of action and observation. Every tool call teaches you something. Use this feedback to refine your approach until completion."""



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
        
        self.tools = [SHELL_TOOL, PATCH_TOOL]
        
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
                extra_body={"enable_thinking": thinking}
            ))
        if model.startswith("gemini/"):
            self.llm_kwargs.update(dict(
                reasoning_effort="disable" if not thinking else "high"
            ))

    @property
    def token_usage(self)->int:
        """
        This is highly dependent on the endpoint and model being used. Some endpoints include tool tokens, some don't.
        Litellm's token counter is designed to accurately reflect the priced tokens, but not for the actual amount of tokens used.
        This will therefore sometimes be accurate, and sometimes underestimate. So we account for this in our token buffer.
        """
        litellm = _get_litellm()
        return litellm.token_counter(self.llm_kwargs["model"], messages=self.messages, tools=self.tools)
    
    @property
    def remaining_tokens(self)->int:
        return self.token_limit - self.token_usage
    
    @property
    def remaining_tool_calls(self)->int:
        return self.tool_limit - self.tool_usage
    
    @property
    def tool_stats(self)->dict[str, Union[int, float]]:
        return self.stats.report()
        
    def run(self, task: str, repo_root: Optional[Union[str, Path]] = None) -> str:
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
                self._append({"role": "user", "content": warning("Use shell to explore or apply_patch to make changes. Do not stop working.")})
                self.tool_usage += 1  # inaction is an action
                continue

            for call in msg["tool_calls"]:  
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"])
                except json.JSONDecodeError as e:
                    output = warning(f"Malformed tool arguments JSON: {e}")
                    self._tool_reply(call, output)
                    self.tool_usage += 1
                    continue

                if name == "shell":
                    output = shell(args=args, repo_root=repo_root, stats=self.stats, verbose=self.verbose)

                elif name == "apply_patch":
                    output = apply_patch(args=args, repo_root=repo_root, stats=self.stats, verbose=self.verbose)

                else:
                    output = warning(f"unknown tool: {name}")
            
                self._tool_reply(call, output)
                self.tool_usage += 1

        unified_diff = git_diff(repo_root)
        if self.log: 
            self.diff_file.open("w").write(unified_diff)
            self.stats_file = self.out_dir/"stats.json"
            self.stats_file.open("w").write(json.dumps(self.stats.report(), indent=2))
        if self.verbose: 
            print(f"\nToken count: {self.token_usage}, tool calls: {self.tool_usage}")
            print(f"Tool stats: \n{self.tool_stats}")
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
        msg.pop("annotations", None)  # openai endpoint emits an empty annotations field which we don't need

        self._append(msg)

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
            warning_message = warning("Token limit critical! Apply your best fix now.")
        elif self.remaining_tokens < self.TOKENS_WRAP_UP:
            warning_message = warning("Tokens low. Focus on the main issue only.")
        elif 1 < self.remaining_tool_calls < self.REMAINING_CALLS_WARNING:
            warning_message = warning(f"{self.remaining_tool_calls} tools left. Prioritize essential changes.")
        elif self.remaining_tool_calls == 1:
            warning_message = warning("Last tool call! Make it count.")
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
        
        # token usage is a property and thus behaves exactly like a variable
        self.tool_usage = 0
        self.stats = ToolStats()

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