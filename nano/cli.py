import argparse
from pathlib import Path

from nano import Agent

def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="nano_agent", description="Minimal CLI for nano‑agent")
    p.add_argument("task", help="Natural‑language description of what the agent should do")
    p.add_argument("--path", default=".", type=Path, help="Repo root (defaults to current directory)")
    p.add_argument("--model", default="openai/gpt-4.1-mini", help="Model identifier in LiteLLM format")
    p.add_argument("--api_base", help="Base URL for API endpoint, useful for local servers")
    p.add_argument("--context_window", type=int, default=8192, help="Size of the context window in tokens")
    p.add_argument("--max_tool_calls", type=int, default=20, help="Maximum number of tool calls the agent can make before stopping")
    p.add_argument("--thinking", action="store_true", help="Emit <think> … </think> blocks (requires compatible models)")
    p.add_argument("--max_tokens", type=int, default=4096, help="Maximum tokens per completion response")
    p.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature, higher means more random")
    p.add_argument("--top_p", type=float, default=0.9, help="Nucleus sampling parameter, lower means more focused")
    p.add_argument("--top_k", type=int, default=20, help="Top-k sampling parameter, lower means more focused")
    p.add_argument("--verbose", action="store_true", help="Stream tool calls as they happen")
    p.add_argument("--no-log", dest="log", action="store_false", help="Disable logging of agent activity to file")
    p.set_defaults(log=True)
    return p.parse_args()

def main():
    args = _parse()
    agent = Agent(
        model=args.model,
        api_base=args.api_base,
        context_window=args.context_window,
        max_tool_calls=args.max_tool_calls,
        thinking=args.thinking,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        verbose=args.verbose,
        log=args.log,
    )
    agent.run(args.task, args.path)

if __name__ == "__main__":
    main()
