#!/data/data/com.termux/files/usr/bin/python3
from setuptools import setup, find_packages

setup(
    name="dynamic-docgen",
    version="1.0.0",
    description="Dynamic DocGen — Zero-Backend Living Architecture & Continuous AST Documentation Platform",
    author="Polymath Swarm / OmniSwarm",
    packages=find_packages(),
    py_modules=["docgen_cli"],
    entry_points={
        "console_scripts": [
            "docgen=docgen_cli:main",
        ],
    },
    python_requires=">=3.8",
)
