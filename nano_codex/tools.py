import subprocess
from pathlib import Path

from diff import load_patches, apply_patches, git_diff


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
      "description":"Apply literal search/replace patch to one or more files",
      "parameters":{
         "type":"object",
         "properties":{
            "patches":{"type":"array","items":{"type":"object",
              "properties":{
                 "search":{"type":"string"},
                 "replace":{"type":"string"},
                 "file":{"type":"string"}
              },
              "required":["search","replace","file"]}}},
         "required":["patches"]}
}}

def shell(cmd: str, cwd: Path, remaining_tool_calls: int, timeout: int = 4, truncate: int = 1_024) -> str:
    """Run a shell command safely using rbash with timeout and output limits."""
    try:
        out = subprocess.check_output(
            ["bash", "-c", "-r", cmd], cwd=cwd,  # runs in readonly mode
            timeout=timeout, text=True, errors="ignore"
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    except subprocess.TimeoutExpired:
        out = "[command timed out]"
    except Exception as e:
        out = f"[command failed: {e}]"

    return (
        f"[SYSTEM WARNING: Only {remaining_tool_calls} tool calls remaining. Apply your patch soon!]\n" if remaining_tool_calls <= 5 else ""
        + out[:truncate]
    )


def apply_patch(repo_root: Path, patches_json: str) -> str:
    patches = load_patches(patches_json)
    apply_patches(repo_root, patches)
    d = git_diff(repo_root, {p["file"] for p in patches})
    return d or "[no changes]"
