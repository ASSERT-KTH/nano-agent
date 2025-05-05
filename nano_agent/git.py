import subprocess
from pathlib import Path

def is_git_repo(repo_root: Path) -> bool:
    return repo_root.joinpath(".git").exists()

def git_diff(repo_root: Path, rel_file: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "diff", "--", rel_file],
        text=True, errors="ignore"
    )