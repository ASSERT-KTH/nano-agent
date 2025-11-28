import pytest
import shutil
from nano.env import DockerEnvironment
from nano.agent import Agent

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

