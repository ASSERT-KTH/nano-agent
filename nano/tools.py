import subprocess
from pathlib import Path

from nano.utils import feedback, warning

SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Run read-only shell command. Output is truncated.",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string"}},
            "required": ["cmd"]
        }
    }
}

PATCH_TOOL = {
    "type": "function",
    "function": {
        "name": "apply_patch",
        "description": "Apply exact literal SEARCH/REPLACE to a file. Search must match exactly one location.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string"},
                "replace": {"type": "string"},
                "file": {"type": "string"}
            },
            "required": ["search", "replace", "file"]
        }
    }
}


def shell(args: dict, repo_root: Path, timeout: int = 4, verbose: bool = False) -> str:
    """Run a shell command using rbash with timeout and output limits."""

    if "cmd" not in args:
        if verbose: print("invalid shell call")
        return warning("invalid `shell` arguments")
    
    cmd = args["cmd"]
    
    if verbose: print(f"shell({cmd})")

    try:
        res = subprocess.run(
            ["bash", "-rc", cmd], cwd=repo_root,
            timeout=timeout, text=True, errors="ignore", stderr=subprocess.STDOUT, stdout=subprocess.PIPE
        )
    except Exception as e:
        return feedback(f"shell failed: {e}")

    out = res.stdout or ""

    if res.returncode != 0:
        return feedback(f"command failed: exit {res.returncode}") + "\n" + (out or feedback("no output"))
    
    return out.strip() or feedback("no output")


def apply_patch(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """Apply a literal search/replace to one file."""

    if "search" not in args or "replace" not in args or "file" not in args:
        if verbose: print("invalid apply_patch call")
        return warning("invalid `apply_patch` arguments")
    
    search, replace, file = args["search"], args["replace"], args["file"]

    if verbose: print(f"apply_patch(..., ..., {file})")

    try:
        target = repo_root / file

        if not target.exists():
            return feedback(f"file {target} not found")
        
        text = target.read_text()
        search_count = text.count(search)

        if search_count == 0:
            return feedback("search string not found")
        
        if search_count > 1:
            return feedback(f"ambiguous search string: {search_count} occurrences")
        
        new_text = text.replace(search, replace, 1)
        target.write_text(new_text)
        return feedback("patch applied successfully")

    except Exception as e:
        return feedback(f"failed to apply patch: {e}")