import argparse
from pathlib import Path

from nano.agent import Agent

def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="nano_agent", description="Minimal CLI for nano-agent")
    p.add_argument("task", help="Natural-language description of what the agent should do")
    p.add_argument("--path", default=".", type=Path, help="Repo root (defaults to current directory)")
    p.add_argument("--model", default="openai/gpt-4.1-mini", help="Model identifier in LiteLLM format")
    p.add_argument("--api_base", help="Base URL for API endpoint, useful for local servers")
    p.add_argument("--create_tool", action="store_true", help="Enable file creation tool")
    # p.add_argument("--deepwiki_tool", action="store_true", help="Enable DeepWiki tool")
    p.add_argument("--token_limit", type=int, default=32768, help="Size of the context window in tokens")
    p.add_argument("--tool_limit", type=int, default=50, help="Maximum number of tool calls the agent can make before stopping")
    p.add_argument("--response_limit", type=int, default=4096, help="Maximum tokens per completion response")
    p.add_argument("--thinking", action="store_true", help="Emit <think> … </think> blocks (requires compatible models)")
    p.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature, higher means more random")
    p.add_argument("--top_p", type=float, default=0.9, help="Nucleus-sampling cutoff; only tokens comprising the top `p` probability mass are kept.")
    p.add_argument("--min_p", type=float, default=0.0, help="Relative floor for nucleus sampling; tokens below `min_p * max_token_prob` are filtered out.")
    p.add_argument("--top_k", type=int, default=20, help="Top-k sampling cutoff; only the highest-probability `k` tokens are considered.")
    p.add_argument("--verbose", action="store_true", help="Stream tool calls as they happen")
    p.add_argument("--no-log", dest="log", action="store_false", help="Disable logging of agent activity to file")
    p.set_defaults(log=True)
    return p.parse_args()

def main():
    args = _parse()
    agent = Agent(
        model=args.model,
        api_base=args.api_base,
        create_tool=args.create_tool,
        # deepwiki_tool=args.deepwiki_tool,
        token_limit=args.token_limit,
        tool_limit=args.tool_limit,
        response_limit=args.response_limit,
        thinking=args.thinking,
        temperature=args.temperature,
        top_p=args.top_p,
        min_p=args.min_p,
        top_k=args.top_k,
        verbose=args.verbose,
        log=args.log,
    )
    agent.run(args.task, args.path)

if __name__ == "__main__":
    main()
