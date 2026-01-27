"""
Filesystem capability handlers (io.fs.* namespace).

This module implements the 8 core filesystem operations.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict

from ..handler import ActionHandler
from ..types import SecurityError, ActionOutput


class ReadFileHandler(ActionHandler):
    """Handler for io.fs.read_file"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        path_str = params["path"]
        encoding = params.get("encoding", "utf-8")
        
        # Resolve path within workspace
        full_path = self._resolve_path(path_str, context)
        
        try:
            with open(full_path, "r", encoding=encoding) as f:
                content = f.read()
            
            return {
                "content": content,
                "size": len(content),
                "success": True,
            }
        except FileNotFoundError:
            return {
                "content": "",
                "size": 0,
                "success": False,
                "error_message": f"File not found: {path_str}",
            }
        except Exception as e:
            return {
                "content": "",
                "size": 0,
                "success": False,
                "error_message": str(e),
            }
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        # Security check: ensure path is within workspace
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path


class WriteFileHandler(ActionHandler):
    """Handler for io.fs.write_file"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        path_str = params["path"]
        content = params["content"]
        encoding = params.get("encoding", "utf-8")
        create_dirs = params.get("create_dirs", False)
        
        full_path = self._resolve_path(path_str, context)
        
        try:
            # Create parent directories if requested
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Capture state for undo
            file_existed = full_path.exists()
            backup_content = None
            if file_existed:
                backup_content = full_path.read_text(encoding=encoding)
            
            # Write file
            with open(full_path, "w", encoding=encoding) as f:
                f.write(content)
            
            # Create undo closure
            def undo():
                if file_existed and backup_content is not None:
                    # Restore original content
                    full_path.write_text(backup_content, encoding=encoding)
                elif not file_existed:
                    # Delete file that didn't exist before
                    full_path.unlink(missing_ok=True)
            
            return ActionOutput(
                result={
                    "bytes_written": len(content.encode(encoding)),
                    "success": True,
                },
                undo_closure=undo,
                description=f"Wrote {len(content)} characters to {path_str}"
            )
        except Exception as e:
            return ActionOutput(
                result={
                    "bytes_written": 0,
                    "success": False,
                    "error_message": str(e),
                },
                undo_closure=None,
                description=f"Failed to write to {path_str}"
            )
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path
    
    def _backup_file(self, file_path: Path, context: Any) -> None:
        """Backup file for undo"""
        backup_dir = context.backup_dir
        backup_path = backup_dir / f"{file_path.name}.backup"
        shutil.copy2(file_path, backup_path)


class ListDirHandler(ActionHandler):
    """Handler for io.fs.list_dir"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        path_str = params["path"]
        recursive = params.get("recursive", False)
        include_hidden = params.get("include_hidden", False)
        
        full_path = self._resolve_path(path_str, context)
        
        try:
            entries = []
            
            if recursive:
                for root, dirs, files in os.walk(full_path):
                    root_path = Path(root)
                    for name in files + dirs:
                        entry_path = root_path / name
                        if not include_hidden and name.startswith("."):
                            continue
                        entries.append(self._get_entry_info(entry_path))
            else:
                for entry in full_path.iterdir():
                    if not include_hidden and entry.name.startswith("."):
                        continue
                    entries.append(self._get_entry_info(entry))
            
            return {
                "entries": entries,
                "success": True,
            }
        except Exception as e:
            return {
                "entries": [],
                "success": False,
                "error_message": str(e),
            }
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path
    
    def _get_entry_info(self, path: Path) -> Dict[str, Any]:
        """Get entry information"""
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path),
            "is_dir": path.is_dir(),
            "size": stat.st_size if path.is_file() else 0,
        }


class MakeDirHandler(ActionHandler):
    """Handler for io.fs.make_dir"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        path_str = params["path"]
        parents = params.get("parents", False)
        exist_ok = params.get("exist_ok", True)
        
        full_path = self._resolve_path(path_str, context)
        
        try:
            # Track if directory already existed
            dir_existed = full_path.exists()
            
            full_path.mkdir(parents=parents, exist_ok=exist_ok)
            
            # Create undo closure only if directory was created
            undo_closure = None
            if not dir_existed:
                def undo():
                    # Remove directory if it was created by this operation
                    if full_path.exists():
                        full_path.rmdir()
                undo_closure = undo
            
            return ActionOutput(
                result={
                    "created": not dir_existed,
                    "success": True,
                },
                undo_closure=undo_closure,
                description=f"Created directory {path_str}" if not dir_existed else f"Directory {path_str} already exists"
            )
        except FileExistsError:
            return ActionOutput(
                result={
                    "created": False,
                    "success": False,
                    "error_message": f"Directory already exists: {path_str}",
                },
                undo_closure=None,
                description=f"Failed to create directory {path_str}"
            )
        except Exception as e:
            return ActionOutput(
                result={
                    "created": False,
                    "success": False,
                    "error_message": str(e),
                },
                undo_closure=None,
                description=f"Failed to create directory {path_str}"
            )
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path


class DeleteHandler(ActionHandler):
    """Handler for io.fs.delete"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        path_str = params["path"]
        recursive = params.get("recursive", False)
        
        full_path = self._resolve_path(path_str, context)
        
        try:
            # Capture state for undo
            is_dir = full_path.is_dir()
            backup_path = context.backup_dir / f"delete_{full_path.name}_{id(self)}"
            
            # Backup entire file/directory
            if is_dir:
                shutil.copytree(full_path, backup_path)
            else:
                shutil.copy2(full_path, backup_path)
            
            # Delete
            if is_dir:
                if recursive:
                    shutil.rmtree(full_path)
                else:
                    full_path.rmdir()
            else:
                full_path.unlink()
            
            # Create undo closure
            def undo():
                if is_dir:
                    shutil.copytree(backup_path, full_path)
                else:
                    shutil.copy2(backup_path, full_path)
                # Clean up backup
                if backup_path.exists():
                    if backup_path.is_dir():
                        shutil.rmtree(backup_path)
                    else:
                        backup_path.unlink()
            
            return ActionOutput(
                result={
                    "deleted": True,
                    "success": True,
                },
                undo_closure=undo,
                description=f"Deleted {path_str}"
            )
        except Exception as e:
            return ActionOutput(
                result={
                    "deleted": False,
                    "success": False,
                    "error_message": str(e),
                },
                undo_closure=None,
                description=f"Failed to delete {path_str}"
            )
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path
    
    def _backup_for_undo(self, path: Path, context: Any) -> None:
        """Backup file/directory for undo"""
        backup_dir = context.backup_dir
        backup_path = backup_dir / path.name
        
        if path.is_dir():
            shutil.copytree(path, backup_path)
        else:
            shutil.copy2(path, backup_path)


class ExistsHandler(ActionHandler):
    """Handler for io.fs.exists"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        path_str = params["path"]
        
        full_path = self._resolve_path(path_str, context)
        
        exists = full_path.exists()
        is_dir = full_path.is_dir() if exists else False
        is_file = full_path.is_file() if exists else False
        
        return {
            "exists": exists,
            "is_dir": is_dir,
            "is_file": is_file,
        }
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path


class MoveHandler(ActionHandler):
    """Handler for io.fs.move"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        source_str = params["source"]
        destination_str = params["destination"]
        overwrite = params.get("overwrite", False)
        
        source_path = self._resolve_path(source_str, context)
        dest_path = self._resolve_path(destination_str, context)
        
        try:
            # Check if source exists
            if not source_path.exists():
                return ActionOutput(
                    result={
                        "moved": False,
                        "success": False,
                        "error_message": f"Source not found: {source_str}",
                    },
                    undo_closure=None,
                    description=f"Failed to move {source_str}"
                )
            
            # Check if destination exists
            dest_existed = dest_path.exists()
            dest_backup = None
            if dest_existed:
                if not overwrite:
                    return ActionOutput(
                        result={
                            "moved": False,
                            "success": False,
                            "error_message": f"Destination exists: {destination_str}",
                        },
                        undo_closure=None,
                        description=f"Failed to move {source_str}"
                    )
                # Backup destination before overwriting
                dest_backup = context.backup_dir / f"move_dest_{dest_path.name}_{id(self)}"
                shutil.copy2(dest_path, dest_backup)
            
            # Move
            shutil.move(str(source_path), str(dest_path))
            
            # Create undo closure
            def undo():
                # Move back to original location
                shutil.move(str(dest_path), str(source_path))
                # Restore destination if it was overwritten
                if dest_existed and dest_backup and dest_backup.exists():
                    shutil.copy2(dest_backup, dest_path)
                    dest_backup.unlink()
            
            return ActionOutput(
                result={
                    "moved": True,
                    "success": True,
                },
                undo_closure=undo,
                description=f"Moved {source_str} to {destination_str}"
            )
        except Exception as e:
            return ActionOutput(
                result={
                    "moved": False,
                    "success": False,
                    "error_message": str(e),
                },
                undo_closure=None,
                description=f"Failed to move {source_str}"
            )
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path


class CopyHandler(ActionHandler):
    """Handler for io.fs.copy"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        source_str = params["source"]
        destination_str = params["destination"]
        overwrite = params.get("overwrite", False)
        
        source_path = self._resolve_path(source_str, context)
        dest_path = self._resolve_path(destination_str, context)
        
        try:
            # Check if source exists
            if not source_path.exists():
                return {
                    "copied": False,
                    "success": False,
                    "error_message": f"Source not found: {source_str}",
                }
            
            # Check if destination exists
            if dest_path.exists() and not overwrite:
                return {
                    "copied": False,
                    "success": False,
                    "error_message": f"Destination exists: {destination_str}",
                }
            
            # Copy
            if source_path.is_dir():
                shutil.copytree(source_path, dest_path, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(source_path, dest_path)
            
            return {
                "copied": True,
                "success": True,
            }
        except Exception as e:
            return {
                "copied": False,
                "success": False,
                "error_message": str(e),
            }
    
    def _resolve_path(self, path_str: str, context: Any) -> Path:
        """Resolve path within workspace"""
        workspace_root = context.workspace_root
        full_path = (workspace_root / path_str).resolve()
        
        if not str(full_path).startswith(str(workspace_root.resolve())):
            raise SecurityError(f"Path '{path_str}' escapes workspace boundary")
        
        return full_path
