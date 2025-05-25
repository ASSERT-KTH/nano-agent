"""Utilities for SWE-Bench testing."""

import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

import git


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


def unified_diff_similarity(expected_patch: str, generated_diff: str) -> float:
    """Compare two unified diffs using sequence matching."""
    expected_lines = expected_patch.splitlines()
    generated_lines = generated_diff.splitlines()
    
    return SequenceMatcher(None, expected_lines, generated_lines).ratio()


def get_git_commit_hash() -> str:
    """Get current git commit hash for tracking baseline versions"""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except:
        return "unknown"