"""Utilities for SWE-Bench testing."""

import re
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
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


def split_diff_by_files(diff_text: str) -> list[str]:
    """Split unified diff into individual file diffs."""
    # Split on "diff --git" but keep the delimiter
    parts = re.split(r'(?=^diff --git)', diff_text, flags=re.MULTILINE)
    return [part.strip() for part in parts if part.strip()]


def extract_filename_from_diff(file_diff: str) -> str:
    """Extract filename from a file diff."""
    lines = file_diff.splitlines()
    match = re.search(r'diff --git a/(.*) b/', lines[0]) if lines else None
    return match.group(1) if match else ""


def unified_diff_similarity(expected_patch: str, generated_diff: str) -> float:
    """Compare two unified diffs using file-aware sequence matching.
    
    This implementation follows CodeRepairRL's approach:
    1. Split diffs by file
    2. Match files by name
    3. Calculate similarity only for oracle files
    4. Normalize by oracle file count to prevent reward hacking
    """
    # Handle empty cases
    if not expected_patch.strip():
        return 1.0 if not generated_diff.strip() else 0.0
    if not generated_diff.strip():
        return 0.0
    
    # Split into individual file diffs
    oracle_file_diffs = split_diff_by_files(expected_patch)
    gen_file_diffs = split_diff_by_files(generated_diff)
    
    # Create filename to diff mapping
    oracle_files = {extract_filename_from_diff(diff): diff for diff in oracle_file_diffs}
    gen_files = {extract_filename_from_diff(diff): diff for diff in gen_file_diffs}
    
    # Calculate similarity for each oracle file
    file_scores = []
    for filename in oracle_files:
        if filename in gen_files:
            # Use SequenceMatcher to compare the raw file diffs
            matcher = SequenceMatcher(None, oracle_files[filename], gen_files[filename])
            file_scores.append(matcher.ratio())
        else:
            # Oracle file not attempted in generated diff
            file_scores.append(0.0)
    
    # Normalize by number of oracle files to prevent reward hacking
    return sum(file_scores) / len(oracle_files) if oracle_files else 0.0


def get_git_commit_hash() -> str:
    """Get current git commit hash for tracking baseline versions"""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except:
        return "unknown"