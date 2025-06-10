import subprocess
from verl.tools.base_tool import BaseTool
from verl_tools import workspace
from nano.utils import feedback, warning
import pydantic
from typing import Any, Dict

class ShellTool(BaseTool):
    name = "shell"
    description = "Run shell command. Use for: finding files (find, rg -l), reading files (head, grep -n), checking structure (ls -la). Output truncated to ~2000 chars."
    
    class Args(pydantic.BaseModel):
        cmd: str = pydantic.Field(description="Command like: grep -n 'def function' file.py")

    def create(self, instance_id: str, meta: Dict[str, Any]):
        """Initialize workspace for this instance."""
        workspace.ensure(
            instance_id,
            repo=meta["repo"],
            base_commit=meta["base_commit"]
        )

    def call(self, instance_id: str, *, cmd: str, **_) -> str:
        """Execute shell command in the workspace - matches nano.tools.shell behavior."""
        repo_path = workspace._REPOS.get(instance_id)
        if not repo_path:
            return warning("shell tool missing required 'cmd' parameter")
        
        try:
            res = subprocess.run(
                ["bash", "-rc", cmd], 
                cwd=repo_path,
                timeout=4,  # Nano's default timeout
                text=True, 
                errors="ignore", 
                stderr=subprocess.STDOUT, 
                stdout=subprocess.PIPE
            )
            
            output = res.stdout.strip() if res.stdout else ""
            
            # Truncate to ~2000 chars like Nano does
            if len(output) > 2000:
                output = output[:2000] + "\n" + feedback("output truncated")
            
            if res.returncode == 0:
                return output if output else feedback("command succeeded")
            else:
                if output:
                    return feedback(f"command failed with exit code {res.returncode}. Error output:") + "\n" + output
                else:
                    return feedback(f"command failed with exit code {res.returncode}")
                    
        except subprocess.TimeoutExpired:
            return warning(f"command timed out after 4s")
        except:
            return warning(f"shell execution failed")

    def delete(self, instance_id: str):
        """Cleanup workspace and save diff."""
        workspace.cleanup(instance_id)