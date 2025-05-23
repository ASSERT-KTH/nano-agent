import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEEPWIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "deepwiki",
        "description": "Ask a natural-language question about a repo.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "The GitHub repository in owner/repo format"},
                "question": {"type": "string"},
            },
            "required": ["repo", "question"],
        },
    },
}

DEEPWIKI_GUIDELINES = (
    "DeepWiki guidelines:\n"
    "- Use 'deepwiki' when you need extra information about a repo / dependency.\n"
    "- Only use 'deepwiki' on popular repositories since smaller repos may not have a wiki.\n"
)

def deepwiki(args: dict, verbose: bool = False) -> tuple[bool, str]:
    """
    Query repository documentation via DeepWiki MCP.
    Returns (success, message) tuple.
    """
    if "repo" not in args or "question" not in args:
        if verbose: print("invalid deepwiki call")
        return (False, "[invalid `deepwiki` arguments]")
    
    repo, question = args["repo"], args["question"]
    if verbose: print(f"deepwiki({repo}, {question[:20]}...)")

    
    if "/" in repo and not repo.startswith("http"):
        repo_path = repo
    elif repo.startswith("https://github.com/"):
        repo_path = repo.replace("https://github.com/", "").rstrip("/")
    else:
        return (False, "[invalid repo format]")

    try:
        out = asyncio.run(_call("ask_question", repoName=repo_path, question=question))
        return True, out.model_dump()["content"][0]["text"]
    
    except Exception as e:
        return False, f"[deepwiki error: {e}]"

async def _call(tool_name: str, **params):
    async with streamablehttp_client("https://mcp.deepwiki.com/mcp") as (reader, writer, _):
        async with ClientSession(reader, writer) as sess:
            await sess.initialize()
            return (await sess.call_tool(tool_name, arguments=params))


if __name__ == "__main__":
    print(deepwiki({"repo": "ASSERT-KTH/nano-agent", "question": "What is the purpose of the nano-agent?"}, verbose=True))


# The following are tools we could also use:
# {
#     "type": "function",
#     "function": {
#         "name": "read_wiki_structure",
#         "description": "List wiki page paths for a GitHub repository via DeepWiki.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "repository_url": {"type": "string"}
#             },
#             "required": ["repository_url"],
#         },
#     },
# },
# {
#     "type": "function",
#     "function": {
#         "name": "read_wiki_contents",
#         "description": "Return the markdown contents of a DeepWiki page.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "repository_url": {"type": "string"},
#                 "topic_path": {"type": "string", "description": "One path from read_wiki_structure"},
#             },
#             "required": ["repository_url", "topic_path"],
#         },
#     },
# },


# DEEPWIKI_GUIDELINES = (
#     "DeepWiki usage:\n"
#     "- Start with 'read_wiki_structure' to map available docs\n"
#     "- Use 'read_wiki_contents' to access specific docs\n"
#     "- Use 'ask_question' for architectural questions\n"
# )


# def read_wiki_structure(repo: str) -> list[str]:
#     """List every wiki page path for owner/repo."""
#     return asyncio.run(_call("read_wiki_structure", repoName=repo))

# def read_wiki_contents(repo: str, path: str) -> str:
#     """Return the markdown for one wiki page."""
#     return asyncio.run(_call("read_wiki_contents", repoName=repo, topicPath=path))
