import subprocess
from pathlib import Path

from nano.utils import feedback, warning

SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Run shell command. Use for: finding files (find, rg -l), reading files (head, grep -n), checking structure (ls -la). Output truncated to ~2000 chars.",
        "parameters": {
            "type": "object",
            "properties": {"cmd": {"type": "string", "description": "Command like: grep -n 'def function' file.py"}},
            "required": ["cmd"]
        }
    }
}

PATCH_TOOL = {
    "type": "function", 
    "function": {
        "name": "apply_patch",
        "description": "Replace exact text in file. The search string must appear exactly once. If patch fails, re-read the file and try again with corrected search.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Exact text to find (including whitespace/indentation)"},
                "replace": {"type": "string", "description": "New text to replace with"},
                "file": {"type": "string", "description": "Relative path like: src/main.py"}
            },
            "required": ["search", "replace", "file"]
        }
    }
}


def shell(args: dict, repo_root: Path, timeout: int = 4, verbose: bool = False) -> str:
    """Run a shell command using bash with timeout and output limits."""

    if "cmd" not in args:
        if verbose: print("invalid shell call")
        return warning("shell tool missing required 'cmd' parameter")
    
    cmd = args["cmd"]
    if verbose: print(f"shell({cmd})")
    
    try:
        res = subprocess.run(
            ["bash", "-rc", cmd], cwd=repo_root,
            timeout=timeout, text=True, errors="ignore", 
            stderr=subprocess.STDOUT, stdout=subprocess.PIPE  # merges stderr into stdout
        )
        
        output = res.stdout.strip() if res.stdout else ""
        
        if res.returncode == 0:  # success
            if output: return output
            else: return feedback("command succeeded")
        else:  # failure
            if output: return feedback(f"command failed with exit code {res.returncode}. Error output:") + "\n" + output
            else: return feedback(f"command failed with exit code {res.returncode}")
                
    except subprocess.TimeoutExpired:
        return warning(f"command timed out after {timeout}s")
    except:
        return warning(f"shell execution failed")


def apply_patch(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """Apply a literal search/replace to one file."""

    if "search" not in args or "replace" not in args or "file" not in args:
        if verbose: print("invalid apply_patch call")
        return warning("invalid `apply_patch` arguments")
    
    search, replace, file = args["search"], args["replace"], args["file"]
    if verbose: print(f"apply_patch(..., ..., {file})")

    try:
        target = (repo_root / file).resolve()
        if not str(target).startswith(str(repo_root.resolve())):
            return feedback("file must be inside the repository")
        
        if not target.exists():
            return feedback(f"file {file} not found")
        
        text = target.read_text()
        search_count = text.count(search)

        if search_count == 0:
            return feedback("search string not found - try using grep to find the exact text")
        
        if search_count > 1:
            return feedback(f"search ambiguous: {search_count} matches - add more context to make search unique")
        
        new_text = text.replace(search, replace, 1)
        target.write_text(new_text)
        return feedback("patch applied successfully")

    except:
        return feedback("patch operation failed")