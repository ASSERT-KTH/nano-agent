import argparse
from pathlib import Path

from nano import Agent

def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="nano_agent", description="Minimal CLI for nano‑agent")
    p.add_argument("task", help="Natural‑language description of what the agent should do")
    p.add_argument("--path", default=".", type=Path,
                   help="Repo root (defaults to current directory)")
    p.add_argument("--model", default="openai/gpt-4.1-mini")
    p.add_argument("--api_base")
    p.add_argument("--thinking", action="store_true",
                   help="Emit <think> … </think> blocks (requires compatible models)")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max_tool_calls", type=int, default=20)
    p.add_argument("--verbose", action="store_true",
                   help="Stream tool calls as they happen")
    return p.parse_args()

def main():
    args = _parse()
    agent = Agent(
        model=args.model,
        api_base=args.api_base,
        thinking=args.thinking,
        temperature=args.temperature,
        max_tool_calls=args.max_tool_calls,
        verbose=args.verbose,
    )
    agent.run(args.task, args.path)

if __name__ == "__main__":
    main()
