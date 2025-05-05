import subprocess
from pathlib import Path

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