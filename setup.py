import re
from setuptools import setup, find_packages


with open('nano/__init__.py', 'r') as f:
    version = re.search(r'__version__ = [\'"]([^\'"]*)[\'"]', f.read()).group(1)

setup(
    name="nano-agent",
    version=version,
    packages=find_packages(),
    install_requires=[
        "litellm>=1.68.0",
    ],
    entry_points={
        "console_scripts": [
            "nano_agent=nano.cli:main",  # we shouldn't overload "nano"
        ],
    },
    author="Bjarni Haukur",
    author_email="bjarnihaukur11@gmail.com",
    description="Nano: A minimal, zero-frills coding-agent for research on agent-in-the-loop training",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ASSERT-KTH/nano-agent",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
