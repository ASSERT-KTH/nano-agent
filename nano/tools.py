import subprocess
from pathlib import Path
from typing import Dict, Any
from collections import Counter
from nano.env import Environment

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


def shell(args: dict, env: Environment, stats: "ToolStats", timeout: int = 120, verbose: bool = False) -> str:
    """Run a shell command using bash with timeout and output limits."""

    if "cmd" not in args:
        if verbose: print("invalid shell call")
        return "shell tool missing required 'cmd' parameter"
    
    cmd = args["cmd"]
    if verbose: print(f"\033[1mshell\033[0m({cmd})")
    
    try:
        res = env.run_shell(cmd, timeout=timeout)
        
        output = res.stdout.strip() if res.stdout else ""
        
        if res.returncode == 0:  # success
            stats.record_shell(cmd, success=True)
            if output: return output
            else: return "command succeeded"
        else:  # failure
            stats.record_shell(cmd, success=False)
            if output: return f"command failed with exit code {res.returncode}. Error output:" + "\n" + output
            else: return f"command failed with exit code {res.returncode}"
                
    except Exception as e:
        stats.record_shell(cmd, success=False)
        return f"shell execution failed: {e}"


def apply_patch(args: dict, env: Environment, stats: "ToolStats", verbose: bool = False) -> str:
    """Apply a literal search/replace to one file."""

    if "search" not in args or "replace" not in args or "file" not in args:
        if verbose: print("invalid apply_patch call")
        stats.record_patch(success=False)
        return "invalid `apply_patch` arguments"
    
    search, replace, file = args["search"], args["replace"], args["file"]
    if verbose: print(f"\033[1mapply_patch\033[0m(..., ..., {file})")

    try:
        if not env.file_exists(file):
            stats.record_patch(success=False)
            return f"file {file} not found"
        
        # Read file
        try:
            text = env.read_file(file)
        except ValueError as e:
            stats.record_patch(success=False)
            return str(e)  # "file must be inside the repository"
        
        search_count = text.count(search)

        if search_count == 0:
            stats.record_patch(success=False)
            return "search string not found - try using grep to find the exact text"
        
        if search_count > 1:
            stats.record_patch(success=False)
            return f"search ambiguous: {search_count} matches - add more context to make search unique"
        
        new_text = text.replace(search, replace, 1)
        env.write_file(file, new_text)
        
        stats.record_patch(success=True)
        return "patch applied successfully"

    except Exception as e:
        stats.record_patch(success=False)
        return f"patch operation failed: {e}"
    

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