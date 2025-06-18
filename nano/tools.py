import subprocess
from pathlib import Path
from typing import Dict, Any
from collections import Counter

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


def shell(args: dict, repo_root: Path, stats: "ToolStats", timeout: int = 4, verbose: bool = False) -> str:
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
            stats.record_shell(cmd, success=True)
            if output: return output
            else: return feedback("command succeeded")
        else:  # failure
            stats.record_shell(cmd, success=False)
            if output: return feedback(f"command failed with exit code {res.returncode}. Error output:") + "\n" + output
            else: return feedback(f"command failed with exit code {res.returncode}")
                
    except subprocess.TimeoutExpired:
        stats.record_shell(cmd, success=False)
        return warning(f"command timed out after {timeout}s")
    except:
        stats.record_shell(cmd, success=False)
        return warning(f"shell execution failed")


def apply_patch(args: dict, repo_root: Path, stats: "ToolStats", verbose: bool = False) -> str:
    """Apply a literal search/replace to one file."""

    if "search" not in args or "replace" not in args or "file" not in args:
        if verbose: print("invalid apply_patch call")
        stats.record_patch(success=False)
        return warning("invalid `apply_patch` arguments")
    
    search, replace, file = args["search"], args["replace"], args["file"]
    if verbose: print(f"apply_patch(..., ..., {file})")

    try:
        target = (repo_root / file).resolve()
        if not str(target).startswith(str(repo_root.resolve())):
            stats.record_patch(success=False)
            return feedback("file must be inside the repository")
        
        if not target.exists():
            stats.record_patch(success=False)
            return feedback(f"file {file} not found")
        
        text = target.read_text()
        search_count = text.count(search)

        if search_count == 0:
            stats.record_patch(success=False)
            return feedback("search string not found - try using grep to find the exact text")
        
        if search_count > 1:
            stats.record_patch(success=False)
            return feedback(f"search ambiguous: {search_count} matches - add more context to make search unique")
        
        new_text = text.replace(search, replace, 1)
        target.write_text(new_text)
        stats.record_patch(success=True)
        return feedback("patch applied successfully")

    except:
        stats.record_patch(success=False)
        return feedback("patch operation failed")
    

MONITORED_COMMANDS = {
    "rg", "grep", "find", "ls", "cat", "head", "tail", "sed", "awk",
    "echo", "cd", "pwd", "mkdir", "rm", "mv", "cp", "touch",
    "python", "pip", "npm", "git", "curl", "wget", "diff", "wc"
}   

class ToolStats:
    """Lightweight tool usage statistics tracker."""
    
    def __init__(self):
        self.tool_calls = {"shell": 0, "apply_patch": 0}
        self.tool_success = {"shell": 0, "apply_patch": 0}
        self.shell_commands = Counter()
        # Pre-initialize all monitored commands
        for cmd in MONITORED_COMMANDS:
            self.shell_commands[cmd] = 0
    
    def _extract_and_count_commands(self, cmd: str):
        """Extract and count commands from a shell command. Only searches the first 10 words are searched"""
        for word in cmd.split(" ")[:10]:  # smaller models can "doomspiral", e.g. "grep pattern grep pattern grep pattern..."
            clean = word.split('/')[-1].rstrip('0123456789.')  # /bin/python3 -> python
            if clean in MONITORED_COMMANDS:
                self.shell_commands[clean] += 1    
    
    def record_shell(self, cmd: str, success: bool):
        self.tool_calls["shell"] += 1
        if success:
            self.tool_success["shell"] += 1
        
        self._extract_and_count_commands(cmd)

    def record_patch(self, success: bool):
        self.tool_calls["apply_patch"] += 1
        if success:
            self.tool_success["apply_patch"] += 1
    
    def report(self) -> Dict[str, Any]:
        """Generate flat usage report suitable for averaging and logging."""
        flat_report = {}
        
        # Tool calls
        for tool, count in self.tool_calls.items():
            flat_report[f"tool_calls_{tool}"] = count
        
        # Success rates
        for tool in self.tool_calls:
            rate = self.tool_success[tool] / self.tool_calls[tool] if self.tool_calls[tool] > 0 else 0.0
            flat_report[f"tool_success_rate_{tool}"] = rate
        
        # Shell commands
        for cmd, count in self.shell_commands.items():
            flat_report[f"shell_cmd_{cmd}"] = count
        
        return flat_report