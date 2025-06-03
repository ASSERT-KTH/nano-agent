from pathlib import Path
import re

from nano.utils import feedback, warning

LIST_FILES_TOOL = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files and directories. Shows file types, sizes, and permissions.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list (default: '.')"},
                "pattern": {"type": "string", "description": "Optional glob pattern to filter files (e.g., '*.py')"}
            },
            "required": []
        }
    }
}

FIND_FILES_TOOL = {
    "type": "function",
    "function": {
        "name": "find_files",
        "description": "Find files by name pattern. Searches recursively with depth limits.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern to match (e.g., '*test*.py', 'user*.py')"},
                "path": {"type": "string", "description": "Starting directory (default: '.')"},
                "max_depth": {"type": "integer", "description": "Maximum directory depth (default: 3)"}
            },
            "required": ["pattern"]
        }
    }
}


PATCH_TOOL = {
    "type": "function", 
    "function": {
        "name": "apply_patch",
        "description": "Replace exact text in file. Search string must be unique. Include 3-5 lines of context. If patch fails, use grep to verify uniqueness before retrying.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Exact text to find (include enough lines for uniqueness)"},
                "replace": {"type": "string", "description": "New text to replace with"},
                "file": {"type": "string", "description": "Relative path like: src/main.py"}
            },
            "required": ["search", "replace", "file"]
        }
    }
}

GREP_FILES_TOOL = {
    "type": "function",
    "function": {
        "name": "grep_files", 
        "description": "Search for pattern across multiple files efficiently. Returns matches with line numbers and context. Use for finding functions, classes, or specific code patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "paths": {"type": "array", "items": {"type": "string"}, "description": "List of file paths or directories to search"},
                "context": {"type": "integer", "description": "Lines of context to show (default: 2)", "default": 2}
            },
            "required": ["pattern", "paths"]
        }
    }
}

READ_LINES_TOOL = {
    "type": "function",
    "function": {
        "name": "read_lines",
        "description": "Read specific line ranges from a file. More efficient than shell for reading exact sections of code.",
        "parameters": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "File path to read"},
                "start": {"type": "integer", "description": "Starting line number (1-based)"},
                "end": {"type": "integer", "description": "Ending line number (inclusive)"}
            },
            "required": ["file", "start", "end"]
        }
    }
}


def list_files(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """List files and directories with details."""
    
    path = args.get("path", ".")
    pattern = args.get("pattern", None)
    
    if verbose: print(f"list_files({path}, pattern={pattern})")
    
    try:
        target = (repo_root / path).resolve()
        if not str(target).startswith(str(repo_root.resolve())):
            return feedback("path must be inside the repository")
            
        if not target.exists():
            return feedback(f"path {path} not found")
            
        if not target.is_dir():
            return feedback(f"{path} is not a directory")
        
        items = []
        entries = sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        
        for entry in entries:
            if pattern and not entry.match(pattern):
                continue
                
            rel_path = entry.relative_to(repo_root)
            if entry.is_dir():
                items.append(f"[DIR]  {rel_path}/")
            else:
                size = entry.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024*1024:
                    size_str = f"{size/1024:.1f}K"
                else:
                    size_str = f"{size/(1024*1024):.1f}M"
                items.append(f"[FILE] {rel_path} ({size_str})")
                
            if len(items) > 50:
                items.append(feedback("List truncated - too many files"))
                break
                
        if items:
            return "\n".join(items)
        else:
            return feedback("No files found matching criteria")
            
    except Exception as e:
        return warning(f"list_files failed: {str(e)}")


def find_files(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """Find files by pattern with depth-limited search."""
    
    if "pattern" not in args:
        return warning("find_files requires 'pattern' parameter")
        
    pattern = args["pattern"]
    path = args.get("path", ".")
    max_depth = args.get("max_depth", 3)
    
    if verbose: print(f"find_files('{pattern}', path={path}, max_depth={max_depth})")
    
    try:
        target = (repo_root / path).resolve()
        if not str(target).startswith(str(repo_root.resolve())):
            return feedback("path must be inside the repository")
            
        if not target.exists():
            return feedback(f"path {path} not found")
            
        matches = []
        
        def search_dir(dir_path: Path, depth: int):
            if depth > max_depth:
                return
                
            try:
                for entry in dir_path.iterdir():
                    if entry.is_file() and entry.match(pattern):
                        matches.append(str(entry.relative_to(repo_root)))
                        if len(matches) > 100:
                            return
                    elif entry.is_dir() and not entry.name.startswith('.'):
                        search_dir(entry, depth + 1)
            except PermissionError:
                pass
                
        search_dir(target, 0)
        
        if matches:
            return "\n".join(sorted(matches)[:100])
        else:
            return feedback(f"No files found matching '{pattern}'")
            
    except Exception as e:
        return warning(f"find_files failed: {str(e)}")



def apply_patch(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """Apply a literal search/replace to one file with smart context suggestions."""

    if "search" not in args or "replace" not in args or "file" not in args:
        if verbose: print("invalid apply_patch call")
        return warning("invalid `apply_patch` arguments")
    
    search, replace, file = args["search"], args["replace"], args["file"]
    if verbose: print(f"apply_patch(..., ..., {file})")

    try:
        target = (repo_root / file).resolve()
        if not str(target).startswith(str(repo_root.resolve())):
            return feedback("file must be inside the repository")
        
        if not target.exists():
            return feedback(f"file {file} not found")
        
        text = target.read_text()
        search_count = text.count(search)

        if search_count == 0:
            # Try to help by showing similar content
            search_lines = search.strip().split('\n')
            if len(search_lines) > 1:
                # Try searching for just the first line
                first_line = search_lines[0].strip()
                if first_line and text.count(first_line) > 0:
                    return feedback(f"search string not found, but '{first_line[:30]}...' exists in file. Check whitespace/indentation")
            return feedback("search string not found - try using grep to find the exact text")
        
        if search_count > 1:
            # Find locations of matches to suggest context
            lines = text.splitlines()
            search_lines = search.strip().split('\n')
            first_search_line = search_lines[0].strip() if search_lines else ""
            
            suggestions = []
            for i, line in enumerate(lines):
                if first_search_line in line:
                    context_start = max(0, i-2)
                    suggestions.append(f"Match at line {i+1}: ...{lines[context_start].strip()[:40]}...")
                    
            hint = " | ".join(suggestions[:3])
            return feedback(f"search ambiguous: {search_count} matches. Add more context. Locations: {hint}")
        
        new_text = text.replace(search, replace, 1)
        target.write_text(new_text)
        return feedback("patch applied successfully")

    except Exception as e:
        return feedback(f"patch operation failed: {str(e)}")


def grep_files(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """Search for pattern across multiple files efficiently."""
    
    if "pattern" not in args or "paths" not in args:
        if verbose: print("invalid grep_files call")
        return warning("grep_files requires 'pattern' and 'paths' parameters")
    
    pattern = args["pattern"]
    paths = args["paths"]
    context = args.get("context", 2)
    
    if verbose: print(f"grep_files('{pattern}', {paths}, context={context})")
    
    try:
        results = []
        regex = re.compile(pattern, re.MULTILINE)
        
        for path_str in paths:
            path = Path(repo_root) / path_str
            
            if path.is_file():
                files = [path]
            elif path.is_dir():
                # Find Python files in directory (limit depth for performance)
                files = []
                for pattern in ["*.py", "*/*.py", "*/*/*.py"]:
                    files.extend(path.glob(pattern))
                    if len(files) > 20:
                        break
                files = files[:20]  # Limit to prevent overwhelming output
            else:
                continue
                
            for file_path in files:
                try:
                    text = file_path.read_text()
                    lines = text.splitlines()
                    
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            start = max(0, i - context)
                            end = min(len(lines), i + context + 1)
                            
                            result = f"\n{file_path.relative_to(repo_root)}:{i+1}:\n"
                            for j in range(start, end):
                                prefix = ">" if j == i else " "
                                result += f"{prefix} {j+1}: {lines[j]}\n"
                            results.append(result)
                            
                            if len(results) > 10:  # Limit results
                                results.append(feedback("Results truncated - too many matches"))
                                return "".join(results)
                except:
                    continue
                    
        if results:
            return "".join(results)
        else:
            return feedback("No matches found")
            
    except Exception as e:
        return warning(f"grep_files failed: {str(e)}")


def read_lines(args: dict, repo_root: Path, verbose: bool = False) -> str:
    """Read specific line ranges from a file."""
    
    if "file" not in args or "start" not in args or "end" not in args:
        if verbose: print("invalid read_lines call")
        return warning("read_lines requires 'file', 'start', and 'end' parameters")
    
    file = args["file"]
    start = args["start"]
    end = args["end"]
    
    if verbose: print(f"read_lines({file}, {start}-{end})")
    
    try:
        target = (repo_root / file).resolve()
        if not str(target).startswith(str(repo_root.resolve())):
            return feedback("file must be inside the repository")
        
        if not target.exists():
            return feedback(f"file {file} not found")
            
        lines = target.read_text().splitlines()
        
        # Adjust to 0-based indexing
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        
        result = []
        for i in range(start_idx, end_idx):
            result.append(f"{i+1}: {lines[i]}")
            
        return "\n".join(result)
        
    except Exception as e:
        return warning(f"read_lines failed: {str(e)}")