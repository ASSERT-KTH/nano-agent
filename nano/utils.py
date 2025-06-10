import git
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def feedback(message: str) -> str:
    return f"<nano:feedback>{message}</nano:feedback>"

def warning(message: str) -> str:
    return f"<nano:warning>{message}</nano:warning>"

def is_git_repo(repo_root: Path) -> bool:
    return repo_root.joinpath(".git").exists()

def is_clean(repo_root: Path) -> bool:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        text=True, errors="ignore"
    ) == ""

def git_diff(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "diff"],
        text=True, errors="ignore"
    )

def clone_repo_at_commit(repo_handle: str, commit_id: str, target_dir: Optional[str] = None) -> str:
    """Clone repository at specific commit."""
    if target_dir is None:
        target_dir = tempfile.mkdtemp()
    
    repo_url = f"https://github.com/{repo_handle}.git"
    repo = git.Repo.init(target_dir)
    origin = repo.create_remote('origin', repo_url)
    origin.fetch(commit_id, depth=1)
    repo.git.checkout(commit_id)
    
    return target_dir

def clean_repo_dir(repo_path: str):
    """Clean temporary repository directory."""
    path = Path(repo_path)
    # Safety check - only clean temp directories
    if not (str(path).startswith("/tmp/") or str(path).startswith("/var/folders/") or "tmp" in str(path)):
        raise ValueError(f"For safety, will only clean temp directories, got: {repo_path}")
    shutil.rmtree(repo_path)
