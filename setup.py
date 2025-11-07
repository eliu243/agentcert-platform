#!/usr/bin/env python3
"""
Setup script for AgentCert Platform
"""

from setuptools import setup, find_packages
import os


def read_requirements():
    """Read requirements from file"""
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []


def read_readme():
    """Read README file for long description"""
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "AgentCert Platform - AI Agent Security Testing"


setup(
    name="agentcert-platform",
    version="1.0.0",
    description="Backend API for AI agent security testing and certification",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="AgentCert Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "agentcert-api=agentcert_platform.api.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Security",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="ai agent security testing certification",
    include_package_data=True,
    zip_safe=False,
)

