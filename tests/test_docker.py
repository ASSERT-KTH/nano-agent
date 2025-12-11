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
    
    setup_completed = []
    
    def setup_env(env):
        """
        Mimics the R2E-Gym setup function with both swebench and non-swebench paths.
        Detects which type of image we're using and applies the appropriate setup.
        """
        repo_path = workdir
        alt_path = "/root"
        
        # Set the PATH for all subsequent commands
        DOCKER_PATH = "/root/.venv/bin:/root/.local/bin:/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        env.path = DOCKER_PATH
        
        # === setup_env_swebench path ===
        # Make run_tests.sh executable (if present)
        env.run_shell("chmod +x /run_tests.sh 2>/dev/null || true")
        
        # Create symlink of conda env to /root/.venv
        env.run_shell("ln -sf /opt/miniconda3/envs/testbed /root/.venv")
        
        # Install required packages
        env.run_shell("python -m pip install chardet -q")
        
        # === setup_env (non-swebench R2E-Gym) path ===
        # Create local bin directory if needed
        env.run_shell(f"mkdir -p {alt_path}/.local/bin")
        
        # Symlink python executables
        env.run_shell(f"ln -sf {repo_path}/.venv/bin/python {alt_path}/.local/bin/python")
        env.run_shell(f"ln -sf {repo_path}/.venv/bin/python {alt_path}/.local/bin/python3")
        
        # Symlink all executables from venv bin
        env.run_shell(f"find {repo_path}/.venv/bin -type f -executable -exec ln -sf {{}} {alt_path}/.local/bin/ \\;")
        
        # Clean up pycache files
        env.run_shell("find . -name '*.pyc' -delete 2>/dev/null || true")
        env.run_shell("find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        
        # Clean up pycache from r2e_tests (if present)
        env.run_shell("find /r2e_tests -name '*.pyc' -delete 2>/dev/null || true")
        env.run_shell("find /r2e_tests -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true")
        
        # Move r2e_tests to /root (if present)
        env.run_shell(f"mv /r2e_tests {alt_path}/r2e_tests 2>/dev/null || true")
        
        # Create symlink for r2e_tests in repo
        env.run_shell(f"ln -sf {alt_path}/r2e_tests {repo_path}/r2e_tests 2>/dev/null || true")
        
        # Install ripgrep
        env.run_shell("apt-get update && apt-get install -y ripgrep 2>/dev/null || true")
        
        setup_completed.append(True)
    
    env = DockerEnvironment(image=image_name, workdir=workdir, setup_fn=setup_env)
    
    try:
        env.start()
        
        # Verify setup was called
        assert len(setup_completed) == 1
        
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

