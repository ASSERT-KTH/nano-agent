from pathlib import Path


CREATE_TOOL = {
    "type":"function",
    "function":{
        "name":"create",
        "description":"Create a new file and write the given content to it",
        "parameters":{
            "type":"object",
            "properties":{
                "path":{"type":"string"},
                "content":{"type":"string"}
            },
            "required":["path","content"]
        }
    }
}

CREATE_GUIDELINES = (
    "Create guidelines:\n"
    "- Verify path doesn't exist first\n"
    "- Include complete, working content\n"
    "- Match project conventions (e.g., indentation, imports)\n"
)

def create(args: dict, repo_root: Path, verbose: bool = False) -> tuple[bool, str]:
    """Create a new file and write the given content to it.
    Returns (success, message) tuple."""

    if "path" not in args or "content" not in args:
        if verbose: print("invalid create call")
        return (False, "[invalid `create` arguments]")
    
    path, content = args["path"], args["content"]

    if verbose: print(f"create({path}, ...)")

    path = repo_root / path

    if path.exists():
        return (False, f"[file {path} already exists]")
    
    try:
        path.touch()
        path.write_text(content)
        return (True, f"[created {path}]")
    
    except Exception as e:
        path.unlink(missing_ok=True)  # if the touch succeeds, but the write fails, remove the file
        return (False, f"[failed to create {path}: {e}]")