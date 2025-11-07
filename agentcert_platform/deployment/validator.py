"""
Agent validation utilities
"""

import ast
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional
import sys


def validate_agent_structure(repo_path: Path, entry_point: str) -> Dict[str, Any]:
    """
    Validate that agent has required structure.
    
    Checks:
    1. Entry point file exists
    2. Has agent_logic function
    3. Uses NANDA adapter
    4. Can be imported (syntax check)
    """
    entry_file = repo_path / entry_point
    
    if not entry_file.exists():
        return {
            "valid": False,
            "error": f"Entry point file {entry_point} not found"
        }
    
    # Check syntax
    try:
        with open(entry_file, 'r') as f:
            ast.parse(f.read())
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error in {entry_point}: {str(e)}"
        }
    
    # Check for required components
    content = entry_file.read_text()
    
    checks = {
        "has_agent_logic": "def agent_logic" in content or "agent_logic" in content,
        "has_nanda": "NANDA" in content or "nanda_core" in content,
        "has_main": "__main__" in content or "if __name__" in content
    }
    
    if not checks["has_agent_logic"]:
        return {
            "valid": False,
            "error": "agent_logic function not found"
        }
    
    if not checks["has_nanda"]:
        return {
            "valid": False,
            "error": "NEST/NANDA adapter not found. Agent must use NANDA adapter."
        }
    
    return {
        "valid": True,
        "checks": checks
    }


def check_requirements_file(repo_path: Path) -> bool:
    """Check if requirements.txt exists"""
    return (repo_path / "requirements.txt").exists()

