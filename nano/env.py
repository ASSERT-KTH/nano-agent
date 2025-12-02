from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import subprocess
import uuid
from typing import Optional

@dataclass
class ShellResult:
    stdout: str
    returncode: int
    timed_out: bool = False

class Environment(ABC):
    """Abstract base class for execution environments."""

    @abstractmethod
    def start(self):
        """Setup the environment (e.g. start container)."""
        pass

    @abstractmethod
    def stop(self):
        """Teardown the environment."""
        pass

    @abstractmethod
    def run_shell(self, cmd: str, timeout: int = 120) -> ShellResult:
        """Run a shell command in the environment."""
        pass

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read content of a file."""
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write content to a file."""
        pass

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def is_git_repo(self) -> bool:
        """Check if the environment root is a git repository."""
        pass

    @abstractmethod
    def is_clean(self) -> bool:
        """Check if the git repository is clean."""
        pass

    @abstractmethod
    def get_diff(self) -> str:
        """Get the current git diff."""
        pass


class LocalEnvironment(Environment):
    """Execution environment running on the local machine."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def start(self):
        if not self.root.exists():
            raise FileNotFoundError(f"Root directory {self.root} does not exist")

    def stop(self):
        pass

    def run_shell(self, cmd: str, timeout: int = 120) -> ShellResult:
        try:
            res = subprocess.run(
                ["bash", "-rc", cmd], 
                cwd=self.root,
                timeout=timeout, 
                text=True, 
                errors="ignore",
                stderr=subprocess.STDOUT, 
                stdout=subprocess.PIPE
            )
            return ShellResult(
                stdout=res.stdout if res.stdout else "",
                returncode=res.returncode
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout=f"Command timed out after {timeout}s",
                returncode=124, # Standard timeout exit code
                timed_out=True
            )
        except Exception as e:
            return ShellResult(
                stdout=f"Execution failed: {str(e)}",
                returncode=1
            )

    def read_file(self, path: str) -> str:
        target = (self.root / path).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Path must be inside the repository")
        return target.read_text()

    def write_file(self, path: str, content: str) -> None:
        target = (self.root / path).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Path must be inside the repository")
        target.write_text(content)

    def file_exists(self, path: str) -> bool:
        target = (self.root / path).resolve()
        if not str(target).startswith(str(self.root)):
            return False
        return target.exists()

    def is_git_repo(self) -> bool:
        return self.root.joinpath(".git").exists()

    def is_clean(self) -> bool:
        try:
            output = subprocess.check_output(
                ["git", "-C", str(self.root), "status", "--porcelain"],
                text=True, errors="ignore"
            )
            return output.strip() == ""
        except subprocess.CalledProcessError:
            return False

    def get_diff(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "-C", str(self.root), "diff"],
                text=True, errors="ignore"
            )
        except subprocess.CalledProcessError:
            return ""


class DockerEnvironment(Environment):
    """Execution environment running inside a Docker container."""
    
    def __init__(self, image: str, workdir: str = "/testbed"):
        self.image = image
        self.workdir = workdir
        self.container_id = None

    def start(self):
        if self.container_id:
            return
        # Start a detached container that stays alive
        cmd = ["docker", "run", "-d", "-w", self.workdir, "--rm", self.image, "tail", "-f", "/dev/null"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        self.container_id = res.stdout.strip()
        
    def stop(self):
        if self.container_id:
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)
            self.container_id = None

    def _exec(self, cmd: list, input: Optional[str] = None, timeout: int = 120) -> ShellResult:
        if not self.container_id:
            raise RuntimeError("Container not started")
        
        full_cmd = ["docker", "exec", "-i", self.container_id] + cmd
        
        try:
            res = subprocess.run(
                full_cmd,
                input=input,
                timeout=timeout,
                text=True,
                errors="ignore",
                capture_output=True
            )
            # merge stdout and stderr for simpler handling, similar to LocalEnvironment
            output = res.stdout
            if res.stderr:
                output += "\n" + res.stderr
                
            return ShellResult(
                stdout=output,
                returncode=res.returncode
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout=f"Command timed out after {timeout}s",
                returncode=124,
                timed_out=True
            )

    def run_shell(self, cmd: str, timeout: int = 120) -> ShellResult:
        # We run inside bash for shell features
        return self._exec(["bash", "-c", cmd], timeout=timeout)

    def read_file(self, path: str) -> str:
        res = self._exec(["cat", path])
        if res.returncode != 0:
            raise FileNotFoundError(f"File {path} not found or readable: {res.stdout}")
        return res.stdout

    def write_file(self, path: str, content: str) -> None:
        # Use tee to write to file
        res = self._exec(["tee", path], input=content)
        if res.returncode != 0:
            raise IOError(f"Failed to write to {path}: {res.stdout}")

    def file_exists(self, path: str) -> bool:
        res = self._exec(["test", "-f", path])
        return res.returncode == 0

    def is_git_repo(self) -> bool:
        res = self._exec(["test", "-d", ".git"])
        return res.returncode == 0

    def is_clean(self) -> bool:
        res = self.run_shell("git status --porcelain")
        if res.returncode != 0:
            return False
        return res.stdout.strip() == ""

    def get_diff(self) -> str:
        res = self.run_shell("git diff")
        return res.stdout if res.returncode == 0 else ""


class ApptainerEnvironment(Environment):
    """Execution environment running inside an Apptainer container."""
    
    def __init__(self, image: str, workdir: str = "/testbed"):
        self.image = image
        self.workdir = workdir
        self.instance_name = f"nano-{str(uuid.uuid4())[:8]}"
        self.started = False

    def start(self):
        if self.started:
            return
        # Check if instance is already running (in case we're re-attaching or something)
        # But here we rely on internal state for now.
        # Start an instance with writable tmpfs to allow file modifications
        cmd = ["apptainer", "instance", "start", "--writable-tmpfs", "--fakeroot", self.image, self.instance_name]
        subprocess.run(cmd, check=True, capture_output=True)
        self.started = True
        
    def stop(self):
        if self.started:
            subprocess.run(["apptainer", "instance", "stop", self.instance_name], capture_output=True)
            self.started = False

    def _exec(self, cmd: list, input: Optional[str] = None, timeout: int = 120) -> ShellResult:
        # apptainer exec instance://name cmd
        full_cmd = ["apptainer", "exec", f"instance://{self.instance_name}"] + cmd
        
        try:
            res = subprocess.run(
                full_cmd,
                input=input,
                timeout=timeout,
                text=True,
                errors="ignore",
                capture_output=True
            )
            
            output = res.stdout
            if res.stderr:
                output += "\n" + res.stderr
                
            return ShellResult(
                stdout=output,
                returncode=res.returncode
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout=f"Command timed out after {timeout}s",
                returncode=124,
                timed_out=True
            )

    def run_shell(self, cmd: str, timeout: int = 120) -> ShellResult:
        return self._exec(["bash", "-c", f"cd {self.workdir} && {cmd}"], timeout=timeout)

    def read_file(self, path: str) -> str:
        # Need to handle absolute/relative paths wrt workdir
        # Simplest is to assume path is relative to workdir if not absolute
        # But for now, let's rely on bash context or absolute paths?
        # Using run_shell for simplicity with cd
        res = self.run_shell(f"cat {path}")
        if res.returncode != 0:
            raise FileNotFoundError(f"File {path} not found or readable: {res.stdout}")
        return res.stdout

    def write_file(self, path: str, content: str) -> None:
        # writing with tee via run_shell might get tricky with quoting
        # better to use _exec with full path if possible, or careful piping
        # Let's try to resolve path relative to workdir if needed
        
        # Ideally we use `apptainer exec` directly but we need to be in the right dir
        # We can chain cd.
        
        # For write, we use input.
        # apptainer exec instance://... bash -c "cd workdir && tee path"
        full_cmd = ["apptainer", "exec", f"instance://{self.instance_name}", "bash", "-c", f"cd {self.workdir} && tee {path}"]
        
        try:
            res = subprocess.run(
                full_cmd,
                input=content,
                text=True,
                errors="ignore",
                capture_output=True
            )
             
            if res.returncode != 0:
                raise IOError(f"Failed to write to {path}: {res.stdout}\n{res.stderr}")
                
        except Exception as e:
            raise IOError(f"Failed to write to {path}: {e}")

    def file_exists(self, path: str) -> bool:
        res = self.run_shell(f"test -f {path}")
        return res.returncode == 0

    def is_git_repo(self) -> bool:
        res = self.run_shell("test -d .git")
        return res.returncode == 0

    def is_clean(self) -> bool:
        res = self.run_shell("git status --porcelain")
        if res.returncode != 0:
            return False
        return res.stdout.strip() == ""

    def get_diff(self) -> str:
        res = self.run_shell("git diff")
        return res.stdout if res.returncode == 0 else ""
