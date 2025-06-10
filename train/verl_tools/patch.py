from pathlib import Path
from typing import Any, Dict

import pydantic
from verl.tools.base_tool import BaseTool

from verl_tools import workspace
from nano.utils import feedback, warning

class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    description = "Replace exact text in file. The search string must appear exactly once. If patch fails, re-read the file and try again with corrected search."
    
    class Args(pydantic.BaseModel):
        search: str = pydantic.Field(description="Exact text to find (including whitespace/indentation)")
        replace: str = pydantic.Field(description="New text to replace with")
        file: str = pydantic.Field(description="Relative path like: src/main.py")

    def create(self, instance_id: str, meta: Dict[str, Any]):
        """Initialize workspace for this instance."""
        workspace.ensure(
            instance_id,
            repo=meta["repo"],
            base_commit=meta["base_commit"]
        )

    def call(self, instance_id: str, *, search: str, replace: str, file: str, **_) -> str:
        """Apply a literal search/replace to one file - matches nano.tools.apply_patch behavior."""
        repo_path = workspace._REPOS.get(instance_id)
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
        workspace.cleanup(instance_id)