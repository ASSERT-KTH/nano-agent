from pathlib import Path
from typing import Dict

from nano.utils import git_diff, clean_repo_dir, clone_repo_at_commit

_REPOS: Dict[str, Path] = {}
_DIFFS: Dict[str, str] = {}

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