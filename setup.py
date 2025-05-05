from setuptools import setup, find_packages

setup(
    name="nano-codex",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "litellm>=1.68.0",
    ],
    author="Bjarni Haukur",
    author_email="bjarnihaukur11@gmail.com",
    description="A minimal, zero-frills coding-agent scaffold for research on agent-in-the-loop training",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ASSERT-KTH/nano-codex",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
