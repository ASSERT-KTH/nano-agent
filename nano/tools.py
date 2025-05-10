import subprocess
from pathlib import Path

SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Run a read-only shell command inside the repository. Terminal outputs longer than 1024 characters will be truncated. Prefer concise commands that produce manageable output lengths.",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string"}},
            "required": ["cmd"]
        }
    }
}

PATCH_TOOL = {
    "type":"function",
    "function":{
        "name":"apply_patch",
        "description": "Apply a single, exact, literal SEARCH/REPLACE operation to a file. The SEARCH string is matched exactly as given, without regex or pattern matching. Ensure the search string uniquely matches exactly one location in the file, including whitespace and indentation.",
        "parameters":{
            "type":"object",
            "properties":{
                "search":{"type":"string"},
                "replace":{"type":"string"},
                "file":{"type":"string"}
            },
            "required":["search","replace","file"]
        }
    }
}

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

def shell(args: dict, repo_root: Path, timeout: int = 4, truncate: int = 512 * 4) -> str:  # 4 characters ~= 1 token
    """Run a shell command safely using rbash with timeout and output limits."""
    if "cmd" not in args:
        return "[invalid `shell` arguments]"
    
    cmd = args["cmd"]

    try:
        out = subprocess.check_output(
            ["bash", "-rc", cmd], cwd=repo_root,
            timeout=timeout, text=True, errors="ignore", stderr=subprocess.STDOUT
        )
    except Exception as e:
        out = f"[command failed: {e}]"
    
    if len(out) > truncate:
        out = out[:truncate] + "\n[output truncated]"

    return out

def apply_patch(args: dict, repo_root: Path) -> str:
    """
    Apply a literal search/replace to one file.
    Returns (True, diff) if the patch was applied, (False, error) otherwise.
    """
    if "search" not in args or "replace" not in args or "file" not in args:
        return "[invalid `apply_patch` arguments]"
    
    search, replace, file = args["search"], args["replace"], args["file"]

    try:
        target = repo_root / file

        if not target.exists():
            return f"[file {target} not found]"
        
        text = target.read_text()
        search_count = text.count(search)

        if search_count == 0:
            return "[search string not found]"
        
        if search_count > 1:
            return f"[ambiguous search string: {search_count} occurrences]"
        
        new_text = text.replace(search, replace, 1)
        target.write_text(new_text)
        return "[patch applied successfully]"

    except Exception as e:
        return f"[failed to apply patch: {e}]"

def create(path: str, content: str) -> str:
    """Create a new file and write the given content to it."""
    path = Path(path)
    if path.exists():
        return f"[file {path} already exists]"
    
    try:
        path.touch()
        path.write_text(content)
        return f"[created {path}]"
    
    except Exception as e:
        return f"[failed to create {path}: {e}]"
