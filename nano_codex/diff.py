"""
diff.py
Minimal search/replace patch utilities for nano‑codex.
Only standard‑library modules; no regex, no external diff libs.
"""

from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Set


class PatchError(Exception):
    """Raised on malformed or unappliable patches."""


def _validate_patch(p: Dict[str, str]) -> None:
    for key in ("search", "replace", "file"):
        if key not in p:
            raise PatchError(f"patch missing required key '{key}'")
        if not isinstance(p[key], str):
            raise PatchError(f"patch key '{key}' must be a string")
    if p["search"] == "":
        raise PatchError("'search' string may not be empty")


# ---------- public helpers ------------------------------------------------- #

def load_patches(json_str: str) -> List[Dict[str, str]]:
    """
    Parse JSON string coming from the model and perform basic validation.
    Returns a list of patch dicts.
    """
    try:
        patches = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise PatchError(f"invalid JSON: {e}") from None

    if not isinstance(patches, list):
        raise PatchError("top‑level JSON must be an array")

    for p in patches:
        _validate_patch(p)

    return patches


def apply_patches(repo_root: Path, patches: List[Dict[str, str]], dry: bool) -> Set[str]:
    """
    Apply each validated patch exactly once.
    Returns the set of files that were modified.
    """
    touched: Set[str] = set()

    for p in patches:
        file_path = repo_root / p["file"]
        if not file_path.exists():
            raise PatchError(f"file not found: {p['file']}")

        src = file_path.read_text()
        if src.count(p["search"]) != 1:
            raise PatchError(
                f"expected exactly one occurrence of search string in {p['file']} "
                f"(found {src.count(p['search'])})"
            )

        new_src = src.replace(p["search"], p["replace"], 1)

        if not dry:
            file_path.write_text(new_src)

        touched.add(p["file"])

    return touched


def git_diff(repo_root: Path, files: Set[str]) -> str:
    """
    Return a unified diff as produced by `git diff -- <files…>`.
    If git is not available or repo_root is not a git repo, fall back to empty string.
    """
    if not files:
        return ""

    try:
        cmd = ["git", "-C", str(repo_root), "diff", "--"] + list(files)
        return subprocess.check_output(cmd, text=True, errors="ignore")
    except (subprocess.SubprocessError, FileNotFoundError):
        # Either git isn't installed or directory isn't a repo – tolerate
        return ""
