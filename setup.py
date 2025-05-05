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
    description="A Python package for the Nano Codex project",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)
