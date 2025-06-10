"""Reimplements Nano's tools for training in VERL."""

import subprocess
from pathlib import Path
from typing import Any, Dict

import pydantic
from verl.tools.base_tool import BaseTool

from nano.utils import feedback, warning, git_diff, clean_repo_dir, clone_repo_at_commit


_REPOS: Dict[str, Path] = {}
_DIFFS: Dict[str, str] = {}  # grows indefinitely, but it is in the order of 1000s of diffs, not a problem

def ensure(instance_id: str, *, repo: str, base_commit: str) -> Path:
    """Clone once per rollout; subsequent calls just return the path."""
    if instance_id in _REPOS:
        return _REPOS[instance_id]
    
    repo_path = clone_repo_at_commit(repo, base_commit)
    repo_path_obj = Path(repo_path)
    
    _REPOS[instance_id] = repo_path_obj
    return repo_path_obj

def cleanup(instance_id: str):
    """Cleanup workspace and save diff."""
    repo = _REPOS.pop(instance_id, None)
    if repo and repo.exists():
        diff = git_diff(repo)
        _DIFFS[instance_id] = diff
        clean_repo_dir(str(repo))

def get_diff(instance_id: str) -> str:
    """Get the saved diff for an instance."""
    return _DIFFS.get(instance_id, "")

def clear_all():
    """Clear all workspaces (useful for cleanup)."""
    for instance_id in list(_REPOS.keys()):
        cleanup(instance_id)
    _DIFFS.clear()

class ShellTool(BaseTool):
    name = "shell"
    description = "Run shell command. Use for: finding files (find, rg -l), reading files (head, grep -n), checking structure (ls -la). Output truncated to ~2000 chars."
    
    class Args(pydantic.BaseModel):
        cmd: str = pydantic.Field(description="Command like: grep -n 'def function' file.py")

    def create(self, instance_id: str, meta: Dict[str, Any]):
        """Initialize workspace for this instance."""
        ensure(instance_id, repo=meta["repo"], base_commit=meta["base_commit"])

    def call(self, instance_id: str, *, cmd: str, **_) -> str:
        """Execute shell command in the workspace - matches nano.tools.shell behavior."""
        repo_path = _REPOS.get(instance_id)
        if not repo_path:
            return warning("shell tool missing required 'cmd' parameter")
        
        try:
            res = subprocess.run(
                ["bash", "-rc", cmd], 
                cwd=repo_path,
                timeout=4,  # Nano's default timeout
                text=True, 
                errors="ignore", 
                stderr=subprocess.STDOUT, 
                stdout=subprocess.PIPE
            )
            
            output = res.stdout.strip() if res.stdout else ""
            
            # Truncate to ~2000 chars like Nano does
            if len(output) > 2000:
                output = output[:2000] + "\n" + feedback("output truncated")
            
            if res.returncode == 0:
                return output if output else feedback("command succeeded")
            else:
                if output:
                    return feedback(f"command failed with exit code {res.returncode}. Error output:") + "\n" + output
                else:
                    return feedback(f"command failed with exit code {res.returncode}")
                    
        except subprocess.TimeoutExpired:
            return warning(f"command timed out after 4s")
        except:
            return warning(f"shell execution failed")

    def delete(self, instance_id: str):
        """Cleanup workspace and save diff."""
        cleanup(instance_id)

class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    description = "Replace exact text in file. The search string must appear exactly once. If patch fails, re-read the file and try again with corrected search."
    
    class Args(pydantic.BaseModel):
        search: str = pydantic.Field(description="Exact text to find (including whitespace/indentation)")
        replace: str = pydantic.Field(description="New text to replace with")
        file: str = pydantic.Field(description="Relative path like: src/main.py")

    def create(self, instance_id: str, meta: Dict[str, Any]):
        """Initialize workspace for this instance."""
        ensure(instance_id, repo=meta["repo"], base_commit=meta["base_commit"])

    def call(self, instance_id: str, *, search: str, replace: str, file: str, **_) -> str:
        """Apply a literal search/replace to one file - matches nano.tools.apply_patch behavior."""
        repo_path = _REPOS.get(instance_id)
        if not repo_path:
            return warning("invalid `apply_patch` arguments")
        
        try:
            target = (repo_path / file).resolve()
            if not str(target).startswith(str(repo_path.resolve())):
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

    def delete(self, instance_id: str):
        """Cleanup workspace and save diff."""
        cleanup(instance_id)