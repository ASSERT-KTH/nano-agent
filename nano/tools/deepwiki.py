import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEEPWIKI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_wiki_structure",
            "description": "List wiki page paths for a GitHub repository via DeepWiki.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repository_url": {"type": "string"}
                },
                "required": ["repository_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_wiki_contents",
            "description": "Return the markdown contents of a DeepWiki page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repository_url": {"type": "string"},
                    "topic_path": {"type": "string", "description": "One path from read_wiki_structure"},
                },
                "required": ["repository_url", "topic_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_question",
            "description": "Ask a natural-language question about a repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repository_url": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["repository_url", "question"],
            },
        },
    },
]


DEEPWIKI_GUIDELINES = (
    "DeepWiki usage:\n"
    "- Start with 'read_wiki_structure' to map available docs\n"
    "- Use 'read_wiki_contents' to access specific docs\n"
    "- Use 'ask_question' for architectural questions\n"
)

def deepwiki(args: dict, verbose: bool = False) -> tuple[bool, str]:
    """
    Query repository documentation via DeepWiki MCP.
    Returns (success, message) tuple.
    """
    if "repo" not in args or "mode" not in args:
        if verbose: print("invalid deepwiki call")
        return (False, "[invalid `deepwiki` arguments]")
    
    repo, mode = args["repo"], args["mode"]
    if verbose: print(f"deepwiki({repo}, {mode})")

    # Extract repo format
    if "/" in repo and not repo.startswith("http"):
        repo_path = repo
    elif repo.startswith("https://github.com/"):
        repo_path = repo.replace("https://github.com/", "").rstrip("/")
    else:
        return (False, "[invalid repo format]")

    try:
        if mode == "structure":
            out = read_wiki_structure(repo_path)
        elif mode == "contents":
            out = read_wiki_contents(repo_path, args["path"])
        elif mode == "ask":
            out = ask_question(repo_path, args["question"])
        else:
            return False, "[unknown mode]"

        return True, out
    
    except Exception as e:
        return False, f"[deepwiki error: {e}]"


async def _call(tool_name: str, **params):
    async with streamablehttp_client("https://mcp.deepwiki.com/mcp") as (reader, writer, _):
        async with ClientSession(reader, writer) as sess:
            await sess.initialize()
            return (await sess.call_tool(tool_name, arguments=params))


def read_wiki_structure(repo: str) -> list[str]:
    """List every wiki page path for owner/repo."""
    return asyncio.run(_call("read_wiki_structure", repoName=repo))

def read_wiki_contents(repo: str, path: str) -> str:
    """Return the markdown for one wiki page."""
    return asyncio.run(
        _call("read_wiki_contents", repoName=repo, topicPath=path)
    )

def ask_question(repo: str, question: str) -> str:
    """Free-form Q&A about a repository."""
    return asyncio.run(_call("ask_question", repoName=repo, question=question))



if __name__ == "__main__":
    # res = read_wiki_structure("ASSERT-KTH/nano-agent")
    # print(len(res.model_dump()["content"]))
    # print(res.model_dump()["content"][0]["text"])

    # res = read_wiki_contents("ASSERT-KTH/nano-agent", "Core Concepts")
    # print(len(res.model_dump()["content"]))
    # print(res.model_dump()["content"][0]["text"])

    res = ask_question("BerriAI/litellm", "I am looking into why importing litellm is so slow. What is the reason?")
    print(len(res.model_dump()["content"]))
    print(res.model_dump()["content"][0]["text"])