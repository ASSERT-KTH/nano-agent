import logging
import subprocess
from pathlib import Path

from nano_agent.git import git_diff

logger = logging.getLogger('nano-agent')

SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Run a read-only shell command inside the repo.",
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
        "description":"Apply a SEARCH/REPLACE patch to one file",
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
def shell(cmd: str, cwd: Path, repo_root: Path, remaining_tool_calls: int, timeout: int = 4, truncate: int = 1_024) -> tuple[str, Path]:
    """Run a shell command safely using rbash with timeout and output limits."""
    logger.info(f"Running shell command: {cmd[:50]}")
    new_cwd = cwd
    try:
        out = subprocess.check_output(
            ["bash", "-rc", cmd], cwd=cwd,  # runs in readonly mode
            timeout=timeout, text=True, errors="ignore", stderr=subprocess.STDOUT
        )
        new_cwd = subprocess.check_output(["pwd"], cwd=cwd, text=True, errors="ignore").strip()
    except subprocess.CalledProcessError as e:
        out = e.output
        logger.info(f"Shell command failed with return code: {e.returncode}")
    except subprocess.TimeoutExpired:
        out = "[command timed out]"
        logger.info(f"Shell command timed out after {timeout}s")
    except Exception as e:
        out = f"[command failed: {e}]"
        logger.info(f"Shell command failed with error: {e}")

    if not str(new_cwd).startswith(str(repo_root)):
        new_cwd = cwd
        out = f"[cannot cd out of repo]"

    if remaining_tool_calls == 1:
        warning_message = f"[SYSTEM WARNING: Only 1 tool call remaining. Apply your patch in the next step!]\n"
    elif remaining_tool_calls <= 5:
        warning_message = f"[SYSTEM WARNING: Only {remaining_tool_calls} tool calls remaining. Apply your patch soon]\n"
    else:
        warning_message = ""

    return warning_message + out[:truncate], new_cwd


def apply_patch(repo_root: Path, patch: dict) -> tuple[bool, str]:
    """
    Apply a literal search/replace to one file.
    Returns (True, diff) if the patch was applied, (False, error) otherwise.
    """
    try:
        target = repo_root / patch["file"]

        if not (target := repo_root / patch["file"]).exists():
            logger.info(f"Patch failed: file {target} not found")
            return False, f"[file {target} not found]"
        
        text = target.read_text()

        if text.count(patch["search"]) == 0:
            logger.info("Patch failed: search string not found")
            return False, "[search string not found]"
        
        if (cnt := text.count(patch["search"])) > 1:
            logger.info(f"Patch failed: ambiguous search string ({cnt} occurrences)")
            return False, f"[ambiguous search string: {cnt} occurrences]"
        
        new_text = text.replace(patch["search"], patch["replace"], 1)

        target.write_text(new_text)
        logger.info(f"Successfully applied patch to {target}")
        
        return True, git_diff(repo_root, patch["file"])
    
    except Exception as e:
        logger.info(f"Patch failed with error: {e}")
        return False, f"[failed to apply patch: {e}]"

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
