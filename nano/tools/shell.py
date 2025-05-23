import subprocess
from pathlib import Path

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

SHELL_GUIDELINES = (
    "Shell primitives:\n"
    "- Find files: `find . -name '*.py'`\n"
    "- Search content: `grep -n 'pattern' file` | `rg 'pattern'`\n" 
    "- View portions: `head -20 file` | `tail -20 file` | `sed -n '10,20p' file`\n"
    "- File info: `ls -la` | `wc -l file`\n"
    "Shell guidelines:\n"
    "- Terminal outputs are truncated to prevent overflow\n"
    "- Avoid large outputs (e.g., `cat` on large files)\n"
    "- Prefer concise commands (e.g., `grep` over `cat`)\n"
)

def shell(args: dict, repo_root: Path, timeout: int = 4, verbose: bool = False) -> tuple[bool, str]:
    """Run a shell command using rbash with timeout and output limits.
    Returns (success, output) tuple."""

    if "cmd" not in args:
        if verbose: print("invalid shell call")
        return (False, "[invalid `shell` arguments]")
    
    cmd = args["cmd"]
    
    if verbose: print(f"shell({cmd})")

    try:
        res = subprocess.run(
            ["bash", "-rc", cmd], cwd=repo_root,
            timeout=timeout, text=True, errors="ignore", stderr=subprocess.STDOUT, stdout=subprocess.PIPE
        )
    except Exception as e:
        return (False, f"[shell failed: {e}]")

    out = res.stdout or ""

    if res.returncode != 0:
        return (False, f"[command failed: exit {res.returncode}]\n{out or '[no output]'}")
    
    return (True, out.strip() or "[no output]")
