"""
System capability handlers (sys.* namespace).

This module implements system information and execution capabilities.
"""

import os
import platform
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..handler import ActionHandler
from ..types import SecurityError, ActionOutput


class GetOSHandler(ActionHandler):
    """Handler for sys.info.get_os"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        verbose = params.get("verbose", False)
        
        os_name = platform.system()
        
        # Map to enum values
        os_map = {
            "Linux": "linux",
            "Darwin": "macos",
            "Windows": "windows",
        }
        
        result = {
            "os_name": os_map.get(os_name, "other"),
            "version": platform.release(),
            "architecture": platform.machine(),
        }
        
        if verbose:
            result["platform"] = platform.platform()
            result["python_version"] = platform.python_version()
        
        return result


class GetEnvVarHandler(ActionHandler):
    """Handler for sys.info.get_env_var"""
    
    # Allowlist of safe environment variables
    ALLOWLIST = {
        "PATH", "HOME", "USER", "LANG", "LC_ALL",
        "SHELL", "TERM", "PWD", "EDITOR",
        "PYTHON_VERSION", "NODE_VERSION",
    }
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        var_name = params["var_name"]
        default_value = params.get("default_value")
        
        # Security check: only allow whitelisted variables
        if var_name not in self.ALLOWLIST:
            return {
                "value": default_value or "",
                "found": False,
                "error_message": f"Environment variable '{var_name}' not in allowlist",
            }
        
        value = os.getenv(var_name, default_value)
        found = var_name in os.environ
        
        return {
            "value": value or "",
            "found": found,
        }


class GetTimeHandler(ActionHandler):
    """Handler for sys.info.get_time"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        format_str = params.get("format", "iso8601")
        timezone = params.get("timezone", "utc")
        
        now = datetime.utcnow() if timezone == "utc" else datetime.now()
        
        if format_str == "iso8601":
            timestamp = now.isoformat() + "Z" if timezone == "utc" else now.isoformat()
        elif format_str == "unix":
            timestamp = str(int(now.timestamp()))
        elif format_str == "rfc3339":
            timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            timestamp = now.isoformat()
        
        return {
            "timestamp": timestamp,
            "timezone": timezone,
        }


class ExecRunHandler(ActionHandler):
    """Handler for sys.exec.run"""
    
    # Allowlist of safe commands
    ALLOWLIST = {
        "ls", "cat", "echo", "pwd", "whoami",
        "git", "python", "node", "npm",
        "grep", "find", "wc", "head", "tail",
    }
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        command = params["command"]
        args = params.get("args", [])
        timeout = params.get("timeout", 30)
        
        # Security check: only allow whitelisted commands
        if command not in self.ALLOWLIST:
            return {
                "stdout": "",
                "stderr": f"Command '{command}' not in allowlist",
                "exit_code": -1,
                "success": False,
            }
        
        try:
            # Run command
            result = subprocess.run(
                [command] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(context.workspace_root),
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "exit_code": -1,
                "success": False,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False,
            }


class ZipHandler(ActionHandler):
    """Handler for sys.archive.zip"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        source_paths = params["source_paths"]
        output_path = params["output_path"]
        compression_level = params.get("compression_level", 6)
        recursive = params.get("recursive", True)
        
        try:
            # Resolve paths
            workspace_root = context.workspace_root
            output_full = self._resolve_path(output_path, workspace_root)
            
            # Track if output file already existed
            output_existed = output_full.exists()
            
            # Create ZIP archive
            file_count = 0
            with zipfile.ZipFile(
                output_full, 
                "w", 
                zipfile.ZIP_DEFLATED, 
                compresslevel=compression_level
            ) as zf:
                for source_path_str in source_paths:
                    source_full = self._resolve_path(source_path_str, workspace_root)
                    
                    if source_full.is_file():
                        zf.write(source_full, source_full.name)
                        file_count += 1
                    elif source_full.is_dir() and recursive:
                        for file_path in source_full.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(source_full.parent)
                                zf.write(file_path, arcname)
                                file_count += 1
            
            compressed_size = output_full.stat().st_size
            
            # Create undo closure
            def undo():
                if not output_existed:
                    # Delete the ZIP file if it didn't exist before
                    output_full.unlink(missing_ok=True)
                # Note: If file existed before, we don't restore it (too complex)
            
            return ActionOutput(
                result={
                    "archive_path": str(output_full),
                    "file_count": file_count,
                    "compressed_size": compressed_size,
                    "success": True,
                },
                undo_closure=undo,
                description=f"Created ZIP archive {output_path} with {file_count} files"
            )
        except Exception as e:
            return ActionOutput(
                result={
                    "archive_path": "",
                    "file_count": 0,
                    "compressed_size": 0,
                    "success": False,
                    "error_message": str(e),
                },
                undo_closure=None,
                description=f"Failed to create ZIP archive {output_path}"
            )
    
    def _resolve_path(self, path_str: str, workspace_root: Path) -> Path:
        """Resolve path within workspace"""
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path
