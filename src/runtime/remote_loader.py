"""
Remote Capability Loader - Load capabilities from GitHub.

This module provides functionality to load capability specifications
directly from the ai-first-specs GitHub repository when they are not
available locally.
"""

import json
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from urllib.parse import urljoin

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Default repository
DEFAULT_REPO = "gmood2008/ai-first-specs"
DEFAULT_BRANCH = "main"
DEFAULT_SPECS_PATH = "capabilities/validated/stdlib"


class RemoteSpecLoader:
    """
    Load capability specifications from GitHub repository.
    """
    
    def __init__(
        self,
        repo: str = DEFAULT_REPO,
        branch: str = DEFAULT_BRANCH,
        specs_path: str = DEFAULT_SPECS_PATH,
        timeout: float = 10.0,
    ):
        """
        Initialize remote spec loader.
        
        Args:
            repo: GitHub repository in format "owner/repo"
            branch: Branch name (default: "main")
            specs_path: Path to specs directory in repo
            timeout: Request timeout in seconds
        """
        self.repo = repo
        self.branch = branch
        self.specs_path = specs_path.rstrip("/")
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get_spec_url(self, capability_id: str) -> str:
        """
        Generate GitHub raw URL for a capability spec.
        
        Args:
            capability_id: Capability ID (e.g., "io.fs.read_file")
        
        Returns:
            URL to raw YAML file
        """
        # Convert capability_id to filename
        # e.g., "io.fs.read_file" -> "io_fs_read_file.yaml"
        filename = capability_id.replace(".", "_") + ".yaml"
        
        # Build URL
        url = f"{GITHUB_RAW_BASE}/{self.repo}/{self.branch}/{self.specs_path}/{filename}"
        return url
    
    def list_available_specs(self) -> list[str]:
        """
        List all available capability specs from GitHub.
        
        Returns:
            List of capability IDs
        """
        # Use GitHub API to list files in directory
        api_url = f"{GITHUB_API_BASE}/repos/{self.repo}/contents/{self.specs_path}"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(api_url)
                response.raise_for_status()
                
                files = response.json()
                capability_ids = []
                
                for file_info in files:
                    if file_info.get("type") == "file" and file_info.get("name", "").endswith(".yaml"):
                        # Convert filename to capability_id
                        # e.g., "io_fs_read_file.yaml" -> "io.fs.read_file"
                        filename = file_info["name"].replace(".yaml", "")
                        capability_id = filename.replace("_", ".")
                        capability_ids.append(capability_id)
                
                return sorted(capability_ids)
        
        except Exception as e:
            print(f"⚠️  Failed to list specs from GitHub: {e}")
            return []
    
    def load_spec(self, capability_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Load a capability specification from GitHub.
        
        Args:
            capability_id: Capability ID (e.g., "io.fs.read_file")
            use_cache: Whether to use cached version if available
        
        Returns:
            Parsed specification dictionary, or None if not found
        """
        # Check cache first
        if use_cache and capability_id in self._cache:
            return self._cache[capability_id]
        
        # Get URL
        url = self.get_spec_url(capability_id)
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                
                # Parse YAML
                spec_dict = yaml.safe_load(response.text)
                
                # Cache it
                if use_cache:
                    self._cache[capability_id] = spec_dict
                
                return spec_dict
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"⚠️  Capability '{capability_id}' not found in GitHub repository")
            else:
                print(f"⚠️  HTTP error loading '{capability_id}': {e}")
            return None
        
        except Exception as e:
            print(f"⚠️  Error loading '{capability_id}' from GitHub: {e}")
            return None
    
    def load_specs_batch(self, capability_ids: list[str]) -> Dict[str, Dict[str, Any]]:
        """
        Load multiple capability specifications.
        
        Args:
            capability_ids: List of capability IDs
        
        Returns:
            Dictionary mapping capability_id to spec_dict
        """
        results = {}
        for cap_id in capability_ids:
            spec = self.load_spec(cap_id)
            if spec:
                results[cap_id] = spec
        return results
    
    def clear_cache(self):
        """Clear the cache."""
        self._cache.clear()


# Global instance
_remote_loader: Optional[RemoteSpecLoader] = None


def get_remote_loader() -> RemoteSpecLoader:
    """Get or create global remote loader instance."""
    global _remote_loader
    if _remote_loader is None:
        _remote_loader = RemoteSpecLoader()
    return _remote_loader


def load_capability_from_github(capability_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to load a capability from GitHub.
    
    Args:
        capability_id: Capability ID
    
    Returns:
        Parsed specification dictionary, or None if not found
    """
    loader = get_remote_loader()
    return loader.load_spec(capability_id)
