"""
AI-First MCP Server - Official SDK Implementation.

This module implements an MCP server using the official mcp SDK,
with a generic dispatcher pattern that dynamically loads capabilities
from YAML specs without requiring manual function wrappers.

Architecture:
- list_tools: Returns schema-translated tool definitions
- call_tool: Generic dispatcher to RuntimeEngine
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
)

# Import AI-First runtime components (src must be on path so "from runtime.xxx" works)
import sys
_src_root = Path(__file__).resolve().parent.parent.parent  # src/
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from runtime.engine import RuntimeEngine
from runtime.types import ExecutionContext
from runtime.registry import CapabilityRegistry, SkillFacadeRegistry
from runtime.stdlib.loader import load_stdlib
from runtime.facade_loader import load_facades_from_directory
from runtime.facade_router import resolve_and_validate
from runtime.pack_loader import load_packs_from_directory
from src.registry.pack_registry import PackRegistry
from src.runtime.workflow.engine import WorkflowEngine
from src.runtime.workflow.spec_loader import load_workflow_spec_by_id
from runtime.undo.manager import UndoManager
from runtime.audit import AuditLogger
from runtime.security.sandbox import PathSandbox
from runtime.mcp.schema_translator import create_mcp_tools_from_stdlib
from runtime.session.persistence import SessionPersistence, PersistedUndoRecord
from runtime.mcp.specs_resolver import resolve_specs_dir
from runtime.paths import facades_dir as resolve_facades_dir, packs_dir as resolve_packs_dir


class AIFirstMCPServer:
    """
    MCP Server for AI-First capabilities using official SDK.
    
    This server uses a generic dispatcher pattern:
    - All capabilities are loaded from YAML specs
    - list_tools returns schema-translated definitions
    - call_tool dispatches to RuntimeEngine
    """
    
    def __init__(
        self,
        name: str = "ai-first-runtime",
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
        # Create MCP server
        self.server = Server(name)
        
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
        
        # Create undo manager first
        self.backup_dir = self.workspace_root / ".backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.undo_manager = UndoManager(self.backup_dir)
        
        # Create audit logger
        audit_db_path = self.workspace_root / ".ai-first" / "audit.db"
        self.audit_logger = AuditLogger(str(audit_db_path))
        
        # Initialize lifecycle_service and signal_bus (set to None for now)
        self.lifecycle_service = None
        self.signal_bus = None
        
        # Then create engine with undo manager, audit logger, and governance
        self.engine = RuntimeEngine(
            self.registry, 
            undo_manager=self.undo_manager, 
            audit_logger=self.audit_logger,
            lifecycle_service=self.lifecycle_service,
            signal_bus=self.signal_bus
        )
        self.sandbox = PathSandbox(self.workspace_root)
        
        # Session management (one MCP connection = one session)
        self.session_id = f"mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
        db_path = self.workspace_root / ".ai-first" / "sessions.db"
        self.persistence = SessionPersistence(db_path)
        self.persistence.create_session(
            self.session_id,
            {"type": "mcp", "workspace": str(self.workspace_root)}
        )
        
        # Load standard library handlers (no emoji output to avoid JSON parsing errors)
        load_stdlib(self.registry, self.specs_dir)
        
        # Load external capability proposals (if external directory exists)
        try:
            from runtime.external_loader import load_external_capabilities
            external_dir = self.specs_dir.parent / "external"
            if external_dir.exists():
                load_external_capabilities(self.registry, external_dir)
        except ImportError:
            # External loader not available, skip
            pass
        
        # Generate MCP tool definitions
        self.tool_definitions = create_mcp_tools_from_stdlib(self.specs_dir)
        
        # Skill Facade: NL -> workflow/pack route (no execution here)
        self.facade_registry = SkillFacadeRegistry()
        _facades_dir = resolve_facades_dir()
        if _facades_dir.exists():
            load_facades_from_directory(
                self.facade_registry, _facades_dir, activate=False, registered_by="mcp"
            )

        # Pack Registry: used for validating ACTIVE state and scoping workflow execution
        self.pack_registry = PackRegistry(capability_registry=None)
        _packs_dir = resolve_packs_dir()
        if _packs_dir.exists():
            load_packs_from_directory(
                self.pack_registry, _packs_dir, activate=False, registered_by="mcp"
            )

        # Workflow Engine: used for workflow execution path
        self.workflow_engine = WorkflowEngine(
            runtime_engine=self.engine,
            execution_context=None,
            pack_registry=self.pack_registry,
        )
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """
        Register MCP handlers.
        
        Only two handlers are needed:
        1. list_tools - Returns tool definitions
        2. call_tool - Dispatches to RuntimeEngine
        """
        @self.server.list_tools()
        async def list_tools(request: ListToolsRequest) -> ListToolsResult:
            """
            List all available tools.
            
            This handler returns the schema-translated tool definitions
            without requiring individual function registrations.
            """
            # Convert our tool definitions to MCP Tool objects
            tools = []
            for tool_def in self.tool_definitions:
                tools.append(
                    Tool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        inputSchema=tool_def["inputSchema"],
                    )
                )
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(request: CallToolRequest) -> CallToolResult:
            """
            Call a tool (generic dispatcher).
            
            This handler:
            1. Extracts capability_id and arguments
            2. Checks if confirmation is needed
            3. Dispatches to RuntimeEngine
            4. Returns result
            """
            capability_id = request.params.name
            arguments = request.params.arguments or {}
            
            try:
                # Execute capability
                result = await self._execute_capability(capability_id, arguments)
                
                # Format result as MCP TextContent
                result_text = json.dumps(result, indent=2)
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result_text)],
                    isError=result.get("status") == "error",
                )
            
            except Exception as e:
                # Return error
                error_result = {
                    "status": "error",
                    "capability_id": capability_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(error_result, indent=2))],
                    isError=True,
                )
    
    async def _execute_capability(
        self, 
        capability_id: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an AI-First capability.
        
        This method:
        1. Creates execution context
        2. Checks if confirmation is needed (dry-run pattern)
        3. Executes the capability
        4. Returns result
        
        Args:
            capability_id: Capability ID
            params: Tool parameters
        
        Returns:
            Execution result dictionary
        """
        # Handle special sys.undo tool
        if capability_id == "sys.undo":
            return await self._handle_undo(params)
        
        # Natural language / Facade: try Skill Facade match before capability
        route = resolve_and_validate(capability_id, self.facade_registry, self.pack_registry)
        if route is not None:
            if route.route_type == "workflow":
                try:
                    spec = load_workflow_spec_by_id(route.ref)
                    workflow_id = self.workflow_engine.submit_workflow(spec)
                    self.workflow_engine.start_workflow(workflow_id)
                    return {
                        "status": "workflow_started",
                        "facade_name": route.facade.name,
                        "workflow_id": workflow_id,
                        "workflow_name": spec.name,
                        "message": f"Workflow '{spec.name}' started via facade '{route.facade.name}'.",
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "facade_name": route.facade.name,
                        "route_type": route.route_type,
                        "ref": route.ref,
                    }

            if route.route_type == "pack":
                return {
                    "status": "pack_resolved",
                    "facade_name": route.facade.name,
                    "pack_ref": route.ref,
                    "allowed_workflows": route.allowed_workflows or [],
                    "message": "Resolved to pack. Choose a workflow within allowed_workflows.",
                }

            return {
                "status": "facade_resolved",
                "facade_name": route.facade.name,
                "route_type": route.route_type,
                "ref": route.ref,
            }
        
        # Create execution context
        # Note: We handle confirmation at the server level (dry-run pattern),
        # so we provide a callback that always returns True to skip RuntimeEngine's check
        def confirmation_callback(message: str, params: dict) -> bool:
            return True  # Already handled by server's dry-run pattern
        
        context = ExecutionContext(
            user_id="mcp_user",
            workspace_root=self.workspace_root,
            session_id=f"mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            confirmation_callback=confirmation_callback,
            undo_enabled=True,
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
            
            # Persist undo record to database if available
            # Note: RuntimeEngine already pushed to undo_manager
            if result.undo_record:
                from runtime.session.persistence import PersistedUndoRecord
                persisted_record = PersistedUndoRecord(
                    session_id=self.session_id,
                    operation_id=result.undo_record.operation_id,
                    capability_id=capability_id,
                    timestamp=datetime.now().isoformat(),
                    undo_function=result.undo_record.undo_function.__name__,
                    undo_args=result.undo_record.undo_args,
                    description=result.undo_record.description
                )
                self.persistence.save_undo_record(persisted_record)
            
            return {
                "status": "success",
                "capability_id": capability_id,
                "outputs": result.outputs,
                "execution_time_ms": result.execution_time_ms,
                "undo_available": result.undo_available,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "capability_id": capability_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def _handle_undo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle sys.undo special tool.
        
        Args:
            params: Parameters with 'steps' key
        
        Returns:
            Undo result dictionary
        """
        steps = params.get("steps", 1)
        
        try:
            if steps < 1:
                return {
                    "status": "error",
                    "error": "steps must be >= 1"
                }
            
            if steps > len(self.undo_manager.stack):
                return {
                    "status": "error",
                    "error": f"Cannot undo {steps} steps, only {len(self.undo_manager.stack)} operations in history"
                }
            
            # Perform undo (with signal bus for governance)
            signal_bus = getattr(self, 'signal_bus', None)
            undone = self.undo_manager.rollback(steps, signal_bus=signal_bus)
            
            # Also remove from database
            self.persistence.pop_undo_records(self.session_id, steps)
            
            return {
                "status": "success",
                "steps_undone": steps,
                "operations": [op.description for op in undone],
                "remaining_history": len(self.undo_manager.stack),
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def run(self):
        """
        Run the MCP server with stdio transport.
        
        This is the entry point for Claude Desktop integration.
        """
        # DO NOT print anything here - it will break MCP JSON protocol
        # All output must go to stderr, not stdout
        import sys
        sys.stderr.write(f"AI-First MCP Server starting...\n")
        sys.stderr.write(f"Workspace: {self.workspace_root}\n")
        sys.stderr.write(f"Specs: {self.specs_dir}\n")
        sys.stderr.write(f"Tools: {len(self.tool_definitions)}\n")
        sys.stderr.flush()
        
        # Run server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def create_server(
    workspace_root: Optional[Path] = None,
    specs_dir: Optional[Path] = None,
) -> AIFirstMCPServer:
    """
    Create an AI-First MCP server.
    
    Args:
        workspace_root: Root directory for file operations
        specs_dir: Directory containing capability YAML specs
    
    Returns:
        AIFirstMCPServer instance
    """
    return AIFirstMCPServer(
        name="ai-first-runtime",
        workspace_root=workspace_root,
        specs_dir=specs_dir,
    )


async def main():
    """Main entry point for running the server."""
    server = create_server()
    
    # Add sys.undo to tool definitions
    server.tool_definitions.append({
        "name": "sys.undo",
        "description": (
            "Undo previous operations. This special tool allows you to rollback "
            "previous operations that modified the filesystem or other resources. "
            "⚠️ Side Effects: Modifies filesystem to restore previous state. "
            "↩️ Undo Strategy: This operation itself cannot be undone."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "integer",
                    "description": "Number of operations to undo (default: 1)",
                    "default": 1,
                }
            },
            "required": [],
        }
    })
    
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
