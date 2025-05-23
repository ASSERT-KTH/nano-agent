
import requests

DEEPWIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "deepwiki",
        "description": "Access repository documentation via DeepWiki. Use structure/contents/ask modes.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "mode": {"type": "string", "enum": ["structure", "contents", "ask"]},
                "path": {"type": "string"},
                "question": {"type": "string"}
            },
            "required": ["repo", "mode"]
        }
    }
}

DEEPWIKI_GUIDELINES = (
    # do this one for me... 
)

def deepwiki(args: dict, timeout: int = 20) -> tuple[bool, str]:
    """Invoke DeepWiki MCP to query repository documentation.
    Returns (success, message) tuple.
    """
    ...