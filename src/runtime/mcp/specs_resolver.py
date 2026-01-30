"""
Specs Directory Resolution Utility.

This module provides cross-platform resolution of the ai-first-specs directory
to avoid hardcoded paths that break on macOS/Windows.

Resolution Strategy:
1. Environment variable AI_FIRST_SPECS_DIR (highest priority)
2. Relative path assuming ai-first-specs is a sibling to ai-first-runtime
3. Error message with clear instructions (no silent fallback)
"""

import os
import sys
from pathlib import Path
from typing import Optional

from runtime.paths import stdlib_specs_dir


def resolve_specs_dir(custom_path: Optional[Path] = None) -> Path:
    """
    Resolve the ai-first-specs directory using a cross-platform strategy.
    
    Resolution Order:
    1. If custom_path is provided, use it (and validate it exists)
    2. Check environment variable AI_FIRST_SPECS_DIR
    3. Try relative path (assuming ai-first-specs is sibling to ai-first-runtime)
    4. Raise clear error if none found
    
    Args:
        custom_path: Optional custom path to specs directory
    
    Returns:
        Resolved Path to specs directory
    
    Raises:
        FileNotFoundError: If specs directory cannot be found
    """
    # Priority 1: Custom path provided by caller
    if custom_path is not None:
        specs_path = Path(custom_path)
        if specs_path.exists():
            return specs_path
        else:
            raise FileNotFoundError(
                f"❌ Custom specs directory not found: {specs_path}\n\n"
                f"Please choose one of the following solutions:\n\n"
                f"Option 1: Ensure the custom path exists\n"
                f"  mkdir -p {specs_path}\n\n"
                f"Option 2: Set environment variable instead\n"
                f"  export AI_FIRST_SPECS_DIR=/path/to/ai-first-specs/capabilities/validated/stdlib\n\n"
                f"Option 3: Clone ai-first-specs repository\n"
                f"  git clone https://github.com/gmood2008/ai-first-specs.git\n"
            )
    
    # Priority 2: Environment variable
    env_specs_dir = os.environ.get("AI_FIRST_SPECS_DIR")
    if env_specs_dir:
        specs_path = Path(env_specs_dir)
        if specs_path.exists():
            return specs_path
        else:
            raise FileNotFoundError(
                f"AI_FIRST_SPECS_DIR environment variable points to non-existent directory: {specs_path}\n"
                f"Please update the environment variable or clone ai-first-specs repository."
            )

    # Priority 3: Installed package assets (share/ai-first-runtime)
    packaged_stdlib = stdlib_specs_dir()
    if packaged_stdlib.exists():
        return packaged_stdlib
    
    # Priority 4: Relative path (sibling directory)
    # Assuming structure:
    # parent/
    #   ai-first-runtime/
    #     src/runtime/mcp/specs_resolver.py  <- we are here
    #   ai-first-specs/
    #     capabilities/validated/stdlib/
    
    # Get the root of ai-first-runtime (4 levels up from this file)
    runtime_root = Path(__file__).parent.parent.parent.parent
    sibling_specs = runtime_root.parent / "ai-first-specs" / "capabilities" / "validated" / "stdlib"
    in_repo_stdlib = runtime_root / "capabilities" / "validated" / "stdlib"

    if sibling_specs.exists():
        return sibling_specs
    if in_repo_stdlib.exists():
        return in_repo_stdlib

    # Priority 5: Clear error message
    raise FileNotFoundError(
        "❌ AI-First specs directory not found!\n\n"
        "The ai-first-specs repository is required but could not be located.\n\n"
        "Please choose one of the following solutions:\n\n"
        "Option 1: Set environment variable (recommended)\n"
        "  export AI_FIRST_SPECS_DIR=/path/to/ai-first-specs/capabilities/validated/stdlib\n\n"
        "Option 2: Clone ai-first-specs as a sibling directory\n"
        "  cd ..\n"
        "  git clone https://github.com/gmood2008/ai-first-specs.git\n\n"
        "Option 3: Pass specs_dir parameter when creating server\n"
        "  server = AIFirstMCPServer(specs_dir='/path/to/specs')\n\n"
        f"Searched locations:\n"
        f"  - Environment variable AI_FIRST_SPECS_DIR: {env_specs_dir or '(not set)'}\n"
        f"  - Sibling directory: {sibling_specs}\n"
    )


def get_default_specs_dir() -> Path:
    """
    Get the default specs directory for stdlib capabilities.
    
    This is a convenience wrapper around resolve_specs_dir()
    that returns the stdlib subdirectory.
    
    Returns:
        Path to stdlib specs directory
    
    Raises:
        FileNotFoundError: If specs directory cannot be found
    """
    return resolve_specs_dir()
