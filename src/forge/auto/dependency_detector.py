"""
Dependency Detector - Automatically detects and tracks Python dependencies.

Analyzes generated code to identify required packages.
"""

import re
from typing import List, Set, Optional
from pathlib import Path


class DependencyDetector:
    """
    Detect Python dependencies from generated code.
    
    Analyzes import statements and common patterns to identify
    required third-party packages.
    """
    
    # Common import mappings
    IMPORT_MAPPINGS = {
        'httpx': 'httpx',
        'requests': 'requests',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'pydantic': 'pydantic',
        'yaml': 'pyyaml',
        'PIL': 'pillow',
        'PIL.Image': 'pillow',
        'bs4': 'beautifulsoup4',
        'lxml': 'lxml',
        'aiohttp': 'aiohttp',
        'redis': 'redis',
        'psycopg2': 'psycopg2',
        'sqlalchemy': 'sqlalchemy',
        'boto3': 'boto3',
        'google.cloud': 'google-cloud-storage',  # Example
    }
    
    def __init__(self):
        """Initialize dependency detector"""
        pass
    
    def detect_from_code(self, code: str) -> Set[str]:
        """
        Detect dependencies from Python code.
        
        Args:
            code: Python code string
        
        Returns:
            Set of package names
        """
        dependencies = set()
        
        # Extract import statements
        import_pattern = r'^(?:from|import)\s+([a-zA-Z0-9_.]+)'
        matches = re.findall(import_pattern, code, re.MULTILINE)
        
        for match in matches:
            # Get root package name
            root_package = match.split('.')[0]
            
            # Check if it's a standard library module
            if self._is_standard_library(root_package):
                continue
            
            # Map to package name
            package = self.IMPORT_MAPPINGS.get(root_package, root_package)
            dependencies.add(package)
        
        return dependencies
    
    def _is_standard_library(self, module_name: str) -> bool:
        """Check if module is part of Python standard library"""
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'json', 'yaml', 'csv', 'datetime',
            'time', 're', 'collections', 'itertools', 'functools',
            'typing', 'dataclasses', 'abc', 'enum', 'logging',
            'urllib', 'http', 'socket', 'ssl', 'hashlib', 'base64',
            'unittest', 'mock', 'pytest',  # pytest is common but might need to be in requirements
        }
        return module_name in stdlib_modules
    
    def generate_requirements_snippet(self, dependencies: Set[str], existing_requirements: Optional[Path] = None) -> str:
        """
        Generate requirements.txt snippet.
        
        Args:
            dependencies: Set of package names
            existing_requirements: Optional path to existing requirements.txt
        
        Returns:
            Requirements snippet as string
        """
        if not dependencies:
            return ""
        
        lines = ["# AutoForge detected dependencies"]
        for dep in sorted(dependencies):
            lines.append(f"{dep}  # Auto-detected")
        
        return "\n".join(lines) + "\n"
    
    def merge_with_existing(self, new_deps: Set[str], requirements_path: Path) -> str:
        """
        Merge new dependencies with existing requirements.txt.
        
        Args:
            new_deps: New dependencies to add
            requirements_path: Path to existing requirements.txt
        
        Returns:
            Updated requirements content
        """
        existing_deps = set()
        
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, etc.)
                        package = re.split(r'[<>=!]', line)[0].strip()
                        existing_deps.add(package)
        
        # Merge
        all_deps = existing_deps | new_deps
        
        # Generate updated requirements
        lines = []
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
        
        # Add new dependencies
        for dep in sorted(new_deps - existing_deps):
            lines.append(f"{dep}  # Auto-detected by AutoForge\n")
        
        return "".join(lines)
