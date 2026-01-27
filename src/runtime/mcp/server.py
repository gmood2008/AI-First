"""
AI-First MCP Server - Bridge between MCP and AI-First Runtime.

This module implements an MCP server that exposes AI-First capabilities
as MCP tools, with built-in safety features including:
- Confirmation for dangerous operations
- Undo capability
- Session persistence
- Security sandbox
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# Import AI-First runtime components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.engine import RuntimeEngine
from runtime.types import ExecutionContext, ExecutionResult
from runtime.registry import CapabilityRegistry
from runtime.stdlib.loader import load_stdlib
from runtime.undo.manager import UndoManager
from runtime.security.sandbox import PathSandbox, ConfirmationGate
from runtime.mcp.schema_translator import create_mcp_tools_from_stdlib
from runtime.mcp.tool_generator import create_tool_function
from runtime.mcp.specs_resolver import resolve_specs_dir


class AIFirstMCPServer:
    """
    MCP Server for AI-First capabilities.
    
    This server exposes AI-First capabilities as MCP tools, with built-in
    safety features and undo support.
    """
    
    def __init__(
        self,
        name: str = "AI-First Runtime",
        workspace_root: Optional[Path] = None,
        specs_dir: Optional[Path] = None,
    ):
        """
        Initialize MCP server.
        
        Args:
            name: Server name
            workspace_root: Root directory for file operations (sandbox)
            specs_dir: Directory containing capability YAML specs
        """
        # Initialize FastMCP server
        self.mcp = FastMCP(name)
        
        # Set up workspace
        if workspace_root is None:
            workspace_root = Path.home() / ".ai-first" / "workspace"
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Set up specs directory with cross-platform resolution
        if specs_dir is None:
            # Use dynamic resolution (env var, relative path, or error)
            self.specs_dir = resolve_specs_dir()
        else:
            # Validate custom path
            self.specs_dir = resolve_specs_dir(custom_path=specs_dir)
        
        # Initialize runtime components
        self.registry = CapabilityRegistry()
        self.engine = RuntimeEngine(self.registry)
        self.backup_dir = self.workspace_root / ".backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.undo_manager = UndoManager(self.backup_dir)
        self.sandbox = PathSandbox(self.workspace_root)
        
        # Load standard library handlers
        load_stdlib(self.registry, self.specs_dir)
        
        # Track pending confirmations (for dry-run pattern)
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        
        # Register MCP tools
        self._register_tools()
        
        # Register sys.undo special tool
        self._register_undo_tool()
    
    def _register_tools(self):
        """
        Register all AI-First capabilities as MCP tools.
        
        This method:
        1. Translates YAML specs to MCP tool definitions
        2. Creates dynamic tool handlers
        3. Registers them with FastMCP
        """
        # Get MCP tool definitions
        tools = create_mcp_tools_from_stdlib(self.specs_dir)
        
        print(f"📦 Registering {len(tools)} AI-First capabilities as MCP tools...")
        
        for tool_def in tools:
            capability_id = tool_def["name"]
            
            # Create dynamic tool handler
            async def tool_handler(**kwargs):
                return await self._execute_capability(capability_id, kwargs)
            
            # Register with FastMCP
            # Note: We need to use a closure to capture capability_id
            self._register_single_tool(tool_def, capability_id)
        
        print(f"✅ Registered {len(tools)} tools")
    
    def _register_single_tool(self, tool_def: Dict[str, Any], capability_id: str):
        """
        Register a single tool with FastMCP.
        
        Args:
            tool_def: MCP tool definition
            capability_id: AI-First capability ID
        """
        # Get handler from registry
        handler = self.registry.get_handler(capability_id)
        
        if handler is None:
            print(f"⚠️  No handler found for {capability_id}, skipping...")
            return
        
        # Create dynamic tool function with explicit parameters
        tool_func = create_tool_function(
            capability_id,
            tool_def,
            self._execute_capability,
        )
        
        # Register with FastMCP
        self.mcp.tool(tool_func)
    
    async def _execute_capability(
        self, 
        capability_id: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an AI-First capability.
        
        This method:
        1. Creates execution context
        2. Checks if confirmation is needed
        3. Executes the capability
        4. Returns result
        
        Args:
            capability_id: Capability ID
            params: Tool parameters
        
        Returns:
            Execution result dictionary
        
        Raises:
            ToolError: If execution fails
        """
        # Create execution context
        context = ExecutionContext(
            user_id="mcp_user",
            workspace_root=self.workspace_root,
            session_id=f"mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            confirmation_callback=None,  # Will be handled by dry-run pattern
            undo_enabled=True,
            undo_manager=self.undo_manager,
            sandbox=self.sandbox,
            backup_dir=self.backup_dir,
        )
        
        # Check if this capability requires confirmation
        handler = self.registry.get_handler(capability_id)
        spec = handler.spec if handler else None
        
        if spec and spec.get("contracts", {}).get("requires_confirmation", False):
            # Check if this is a confirmed execution
            confirm_token = params.get("_confirm")
            
            if not confirm_token:
                # This is a dry-run request
                return {
                    "status": "confirmation_required",
                    "capability_id": capability_id,
                    "params": params,
                    "message": "⚠️ This operation requires confirmation. Please review and confirm.",
                    "side_effects": spec.get("contracts", {}).get("side_effects", []),
                    "undo_strategy": spec.get("behavior", {}).get("undo_strategy", ""),
                    "confirm_instructions": "To proceed, call this tool again with '_confirm': true in the parameters.",
                }
            
            # Confirmed, remove the token and proceed
            params = {k: v for k, v in params.items() if k != "_confirm"}
        
        # Execute capability
        try:
            result = self.engine.execute(capability_id, params, context)
            
            return {
                "status": "success",
                "capability_id": capability_id,
                "result": result.result,
                "execution_time_ms": result.execution_time_ms,
                "undo_available": result.undo_record is not None,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "capability_id": capability_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    def _register_undo_tool(self):
        """
        Register sys.undo special tool.
        
        This tool allows Claude to undo previous operations.
        """
        @self.mcp.tool
        async def sys_undo(steps: int = 1) -> str:
            """
            Undo previous operations.
            
            This special tool allows you to rollback previous operations
            that modified the filesystem or other resources.
            
            Args:
                steps: Number of operations to undo (default: 1)
            
            Returns:
                JSON string with undo results
            """
            try:
                if steps < 1:
                    return json.dumps({
                        "status": "error",
                        "error": "steps must be >= 1"
                    })
                
                if steps > len(self.undo_manager.stack):
                    return json.dumps({
                        "status": "error",
                        "error": f"Cannot undo {steps} steps, only {len(self.undo_manager.stack)} operations in history"
                    })
                
                # Perform undo
                undone = self.undo_manager.rollback(steps)
                
                return json.dumps({
                    "status": "success",
                    "steps_undone": steps,
                    "operations": undone,
                    "remaining_history": len(self.undo_manager.stack),
                }, indent=2)
            
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }, indent=2)
    
    def run(self, transport: str = "stdio", **kwargs):
        """
        Run the MCP server.
        
        Args:
            transport: Transport type ("stdio" or "http")
            **kwargs: Additional arguments for mcp.run()
        """
        print(f"🚀 Starting AI-First MCP Server...")
        print(f"📁 Workspace: {self.workspace_root}")
        print(f"📦 Specs: {self.specs_dir}")
        print(f"🔧 Transport: {transport}")
        
        self.mcp.run(transport=transport, **kwargs)


def create_server(
    workspace_root: Optional[Path] = None,
    specs_dir: Optional[Path] = None,
) -> AIFirstMCPServer:
    """
    Create an AI-First MCP server.
    
    This is a convenience function for creating a server instance.
    
    Args:
        workspace_root: Root directory for file operations
        specs_dir: Directory containing capability YAML specs
    
    Returns:
        AIFirstMCPServer instance
    """
    return AIFirstMCPServer(
        name="AI-First Runtime",
        workspace_root=workspace_root,
        specs_dir=specs_dir,
    )


# Create default server instance for FastMCP CLI
mcp_server = create_server()
mcp = mcp_server.mcp


if __name__ == "__main__":
    # Run server with stdio transport (for Claude Desktop)
    mcp_server.run(transport="stdio")
