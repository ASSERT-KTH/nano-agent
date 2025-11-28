import pytest
import shutil
from nano.env import ApptainerEnvironment
from nano.agent import Agent

def apptainer_available():
    return shutil.which("apptainer") is not None

@pytest.mark.skipif(not apptainer_available(), reason="Apptainer not available")
def test_apptainer_environment_lifecycle():
    # Use a small image with bash (docker:// URI works with apptainer)
    env = ApptainerEnvironment(image="docker://debian:stable-slim", workdir="/app")
    
    try:
        env.start()
        
        # Create workdir since it might not exist in the image
        # Use _exec directly to avoid cd-ing into non-existent dir
        env._exec(["mkdir", "-p", "/app"])

        # Test shell
        res = env.run_shell("echo hello")
        assert res.returncode == 0
        assert "hello" in res.stdout
        
        # Test file operations
        env.write_file("test.txt", "content")
        assert env.file_exists("test.txt")
        content = env.read_file("test.txt")
        assert content == "content"
        
        # Test git helpers (should fail as no git repo init)
        assert not env.is_git_repo()
        
        # Init git repo manually to test git helpers
        env.run_shell("rm test.txt")  # Clean up
        res = env.run_shell("apt-get update && apt-get install -y git")
        env.run_shell("git config --global user.email 'you@example.com'")
        env.run_shell("git config --global user.name 'Your Name'")
        env.run_shell("git init")
        assert env.is_git_repo()
        assert env.is_clean()  # empty is clean
        
        # Create a file and check status
        env.write_file("new.txt", "data")
        assert not env.is_clean()  # untracked file
        
    finally:
        env.stop()

@pytest.mark.skipif(not apptainer_available(), reason="Apptainer not available")
def test_agent_in_apptainer():
    # Verify that agent can accept the env and start/stop it.
    
    env = ApptainerEnvironment(image="docker://debian:stable-slim", workdir="/app")
    agent = Agent(env=env, verbose=True)
    
    try:
        env.start()
        # Create workdir
        env._exec(["mkdir", "-p", "/app"])
        
        # Verify agent can use tools with this env
        from nano.tools import shell, ToolStats
        
        # Agent usually calls shell(args, env, ...)
        stats = ToolStats()
        output = shell({"cmd": "echo 'agent test'"}, env, stats)
        assert "agent test" in output
        
    finally:
        env.stop()

