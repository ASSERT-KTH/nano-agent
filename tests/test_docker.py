import pytest
import shutil
from nano.env import DockerEnvironment
from nano.agent import Agent
from tests.utils import setup_env_swebench

def docker_available():
    return shutil.which("docker") is not None

@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_docker_environment_lifecycle():
    # Use a small image with bash
    env = DockerEnvironment(image="debian:stable-slim", workdir="/app")
    
    try:
        env.start()
        
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
        env.run_shell("rm test.txt")  # Clean up previous test file
        env.run_shell("apt-get update && apt-get install -y git")
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

@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_agent_in_docker():
    # This test runs the agent against a real container
    # We mock the LLM to avoid API calls, or just test the env part
    # But to test Agent integration, we need to run it.
    # We can skip actual LLM call by mocking _chat or using a dummy model if we had one.
    # Since we don't have a mock setup easily available for Agent._chat, 
    # we will verify that the agent can accept the env and start/stop it.
    
    env = DockerEnvironment(image="debian:stable-slim", workdir="/app")
    agent = Agent(env=env, verbose=True)
    
    # We can't easily run agent.run() without an LLM. 
    # So we'll manually exercise what agent.run does with env.
    
    try:
        env.start()
        # Verify agent can use tools with this env
        from nano.tools import shell, ToolStats
        
        # Agent usually calls shell(args, env, ...)
        stats = ToolStats()
        output = shell({"cmd": "echo 'agent test'"}, env, stats)
        assert "agent test" in output
        
    finally:
        env.stop()

@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_docker_setup_fn():
    # Test that setup_fn is called during start()
    setup_called = []
    
    def my_setup(env):
        # Create a marker file to prove setup ran
        env.run_shell("echo 'setup_marker' > /tmp/setup_marker.txt")
        setup_called.append(True)
    
    env = DockerEnvironment(image="debian:stable-slim", workdir="/app", setup_fn=my_setup)
    
    try:
        env.start()
        
        # Verify setup_fn was called
        assert len(setup_called) == 1
        
        # Verify the marker file exists (setup actually ran inside container)
        res = env.run_shell("cat /tmp/setup_marker.txt")
        assert res.returncode == 0
        assert "setup_marker" in res.stdout
        
    finally:
        env.stop()

@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_docker_swebench_setup():
    """Test setup_fn with a real SWE-bench docker image and typical setup commands."""
    
    # Use a sample R2E-Gym SWE-bench image
    image_name = "slimshetty/swebench-verified:sweb.eval.x86_64.astropy__astropy-12907"
    workdir = "/testbed"

    env = DockerEnvironment(image=image_name, workdir=workdir, setup_fn=setup_env_swebench)
    
    try:
        env.start()
        
        # Verify PATH is correctly set
        res = env.run_shell("echo $PATH")
        assert res.returncode == 0
        assert "/root/.venv/bin" in res.stdout
        assert "/root/.local/bin" in res.stdout
        
        # Verify the symlink was created
        res = env.run_shell("ls -la /root/.venv")
        assert res.returncode == 0
        assert "miniconda3" in res.stdout or "testbed" in res.stdout or ".venv" in res.stdout
        
        # Verify chardet was installed
        res = env.run_shell("python -c 'import chardet; print(chardet.__version__)'")
        assert res.returncode == 0
        
        # Verify we're in a git repo
        assert env.is_git_repo()
        
        # Verify python works
        res = env.run_shell("python --version")
        assert res.returncode == 0
        assert "Python" in res.stdout
        
        # Verify ripgrep is installed
        res = env.run_shell("rg --version")
        assert res.returncode == 0
        assert "ripgrep" in res.stdout
        
        # Verify python is from the correct venv
        res = env.run_shell("which python")
        assert res.returncode == 0
        assert "/root/.venv/bin/python" in res.stdout or "/opt/miniconda3/envs/testbed" in res.stdout
        
    finally:
        env.stop()

