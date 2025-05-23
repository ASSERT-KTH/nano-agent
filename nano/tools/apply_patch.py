from pathlib import Path


PATCH_TOOL = {
    "type": "function",
    "function": {
        "name": "apply_patch",
        "description": "Apply exact literal SEARCH/REPLACE to a file. Search must match exactly one location.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string"},
                "replace": {"type": "string"},
                "file": {"type": "string"}
            },
            "required": ["search", "replace", "file"]
        }
    }
}

PATCH_GUIDELINES = (
    "Patch guidelines:\n"
    "- Each patch must be atomic and unambiguous\n"
    "- Search strings must be unique with exact whitespace\n"
    "- Replace strings must maintain correct indentation\n"
)

def apply_patch(args: dict, repo_root: Path, verbose: bool = False) -> tuple[bool, str]:
    """
    Apply a literal search/replace to one file.
    Returns (success, message) tuple.
    """
    if "search" not in args or "replace" not in args or "file" not in args:
        if verbose: print("invalid apply_patch call")
        return (False, "[invalid `apply_patch` arguments]")
    
    search, replace, file = args["search"], args["replace"], args["file"]

    if verbose: print(f"apply_patch(..., ..., {file})")

    try:
        target = repo_root / file

        if not target.exists():
            return (False, f"[file {target} not found]")
        
        text = target.read_text()
        search_count = text.count(search)

        if search_count == 0:
            return (False, "[search string not found]")
        
        if search_count > 1:
            return (False, f"[ambiguous search string: {search_count} occurrences]")
        
        new_text = text.replace(search, replace, 1)
        target.write_text(new_text)
        return (True, "[patch applied successfully]")

    except Exception as e:
        return (False, f"[failed to apply patch: {e}]")