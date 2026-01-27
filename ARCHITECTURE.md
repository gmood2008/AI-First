# AI-First Runtime Architecture

**Version:** 0.1.0  
**Status:** 🚧 Under Development  
**Code Name:** Operation Pulse

---

## 🎯 Mission

Transform static YAML capability specifications into **executable, safe, auditable** Python functions that AI models can invoke through standardized protocols (MCP, OpenAI Function Calling).

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Model (Claude/GPT)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ MCP Protocol / Function Calling
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    MCP Adapter Layer                         │
│  - Schema Translation (YAML → MCP JSON)                      │
│  - Request Routing                                           │
│  - Response Formatting                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Runtime Kernel                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Registry: id → ActionHandler mapping                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Security Middleware                                 │   │
│  │  - Confirmation Gate                                 │   │
│  │  - Path Sandbox                                      │   │
│  │  - Permission Check                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Execution Engine                                    │   │
│  │  - Parameter Validation                              │   │
│  │  - Handler Invocation                                │   │
│  │  - Error Handling                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Undo Manager (Time Machine)                         │   │
│  │  - Operation Stack                                   │   │
│  │  - Backup Creation                                   │   │
│  │  - Rollback Execution                                │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 Action Handlers (StdLib)                     │
│  - io.fs.* (8 handlers)                                      │
│  - sys.info.* (3 handlers)                                   │
│  - net.http.* (3 handlers)                                   │
│  - sys.* (2 handlers)                                        │
│  - data.json.* (2 handlers)                                  │
│  - text.* (2 handlers)                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 📦 Module Breakdown

### 1. Runtime Kernel (`src/runtime/kernel.py`)

**Responsibility:** Core execution engine

**Key Components:**

#### 1.1 CapabilityRegistry
```python
class CapabilityRegistry:
    """Maps capability IDs to ActionHandler instances"""
    
    def register(self, spec: CapabilitySpec, handler: ActionHandler)
    def get_handler(self, capability_id: str) -> ActionHandler
    def list_capabilities(self) -> List[CapabilitySpec]
```

#### 1.2 RuntimeEngine
```python
class RuntimeEngine:
    """Main execution orchestrator"""
    
    def execute(
        self, 
        capability_id: str, 
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult
```

#### 1.3 ExecutionContext
```python
@dataclass
class ExecutionContext:
    """Execution environment and state"""
    
    user_id: str
    workspace_root: Path
    confirmation_callback: Optional[Callable[[str], bool]]
    undo_enabled: bool = True
```

---

### 2. Action Handler Interface (`src/runtime/handler.py`)

**Responsibility:** Abstract base class for all capability implementations

```python
from abc import ABC, abstractmethod

class ActionHandler(ABC):
    """Base class for all capability implementations"""
    
    def __init__(self, spec: CapabilitySpec):
        self.spec = spec
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the capability with given parameters"""
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate parameters against spec.interface.inputs"""
        pass
    
    def requires_confirmation(self) -> bool:
        """Check if this capability requires user confirmation"""
        return self.spec.contracts.requires_confirmation
    
    def get_undo_strategy(self) -> str:
        """Get the undo strategy description"""
        return self.spec.behavior.undo_strategy
```

---

### 3. Security Middleware (`src/runtime/security.py`)

**Responsibility:** Enforce safety constraints

#### 3.1 ConfirmationGate
```python
class ConfirmationGate:
    """Intercepts dangerous operations and requests user approval"""
    
    def check(
        self, 
        spec: CapabilitySpec, 
        params: Dict[str, Any],
        callback: Callable[[str], bool]
    ) -> bool:
        """Returns True if operation is approved"""
        pass
```

#### 3.2 PathSandbox
```python
class PathSandbox:
    """Restricts filesystem operations to workspace directory"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
    
    def validate_path(self, path: str) -> Path:
        """Raises SecurityError if path escapes workspace"""
        resolved = (self.workspace_root / path).resolve()
        if not resolved.is_relative_to(self.workspace_root):
            raise SecurityError(f"Path {path} escapes workspace")
        return resolved
```

#### 3.3 PermissionChecker
```python
class PermissionChecker:
    """Validates that operations match declared side effects"""
    
    def check(self, spec: CapabilitySpec, operation: str) -> None:
        """Raises PermissionError if operation not declared"""
        pass
```

---

### 4. Undo Manager (`src/runtime/undo.py`)

**Responsibility:** Time machine for operation rollback

```python
@dataclass
class UndoRecord:
    """Record of a reversible operation"""
    
    capability_id: str
    timestamp: datetime
    params: Dict[str, Any]
    backup_data: Optional[Dict[str, Any]]
    undo_handler: Callable[[], None]

class UndoManager:
    """Manages operation history and rollback"""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.stack: List[UndoRecord] = []
    
    def record(
        self, 
        capability_id: str, 
        params: Dict[str, Any],
        undo_handler: Callable[[], None]
    ) -> None:
        """Add operation to undo stack"""
        pass
    
    def rollback(self, steps: int = 1) -> List[str]:
        """Undo last N operations"""
        pass
    
    def clear(self) -> None:
        """Clear undo history"""
        pass
```

---

### 5. StdLib Handlers (`src/runtime/stdlib/`)

**Responsibility:** Concrete implementations of 20 core capabilities

#### Directory Structure:
```
src/runtime/stdlib/
├── __init__.py
├── fs_handlers.py      # 8 handlers: io.fs.*
├── sys_handlers.py     # 4 handlers: sys.info.*, sys.exec.run
├── net_handlers.py     # 3 handlers: net.http.*
├── data_handlers.py    # 2 handlers: data.json.*
├── text_handlers.py    # 2 handlers: text.*
└── archive_handlers.py # 1 handler: sys.archive.zip
```

#### Example Implementation:
```python
# fs_handlers.py
class ReadFileHandler(ActionHandler):
    """Implementation of io.fs.read_file"""
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        encoding = params.get("encoding", "utf-8")
        
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            
            return {
                "content": content,
                "size": len(content),
                "success": True
            }
        except Exception as e:
            return {
                "content": "",
                "size": 0,
                "success": False,
                "error_message": str(e)
            }
```

---

### 6. MCP Adapter (`src/mcp/adapter.py`)

**Responsibility:** Bridge between AI-First Runtime and MCP protocol

```python
class MCPAdapter:
    """Converts AI-First specs to MCP format"""
    
    def __init__(self, runtime: RuntimeEngine):
        self.runtime = runtime
    
    def list_tools(self) -> List[Dict]:
        """Convert capabilities to MCP tool definitions"""
        pass
    
    def execute_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute capability via MCP protocol"""
        pass
```

---

### 7. CLI Executor (`src/cli/executor.py`)

**Responsibility:** Command-line interface for testing

```bash
# Execute a capability
airun execute io.fs.read_file --params '{"path": "test.txt"}'

# List all capabilities
airun list

# Show capability details
airun inspect io.fs.read_file

# Undo last operation
airun undo

# Start MCP server
airun serve --port 8080
```

---

## 🔒 Security Model

### 1. Defense in Depth

```
Layer 1: Schema Validation (Pydantic)
  ↓
Layer 2: Permission Check (declared side effects)
  ↓
Layer 3: Path Sandbox (workspace restriction)
  ↓
Layer 4: Confirmation Gate (user approval)
  ↓
Layer 5: Execution (actual operation)
  ↓
Layer 6: Undo Recording (time machine)
```

### 2. Workspace Isolation

All filesystem operations are restricted to:
```
~/.ai-first/workspaces/<user_id>/<session_id>/
```

Attempting to access `/etc/passwd` or `../../../` will raise `SecurityError`.

### 3. Confirmation Flow

For capabilities with `requires_confirmation: true`:

```
1. Runtime detects dangerous operation
2. Pause execution
3. Show user:
   - Capability ID
   - Operation description
   - Parameters
   - Undo strategy
4. Wait for [Y/n] input
5. If denied: abort and return error
6. If approved: proceed with execution
```

---

## 🔄 Undo Mechanism

### Backup Strategy

For each write operation:

1. **Before execution:**
   ```python
   backup_path = backup_dir / f"{timestamp}_{capability_id}.backup"
   shutil.copy(original_file, backup_path)
   ```

2. **Record undo handler:**
   ```python
   def undo():
       shutil.copy(backup_path, original_file)
   
   undo_manager.record(capability_id, params, undo)
   ```

3. **On rollback:**
   ```python
   undo_manager.rollback(steps=1)  # Restores from backup
   ```

---

## 📊 Data Flow

### Execution Flow

```
1. AI Model sends request via MCP
   ↓
2. MCP Adapter translates to internal format
   ↓
3. Runtime Kernel validates capability ID
   ↓
4. Security Middleware checks permissions
   ↓
5. Confirmation Gate (if needed)
   ↓
6. Undo Manager prepares backup
   ↓
7. Action Handler executes
   ↓
8. Undo Manager records operation
   ↓
9. Result returned to AI Model
```

### Rollback Flow

```
1. User issues undo command
   ↓
2. Undo Manager pops operation from stack
   ↓
3. Execute undo handler (restore backup)
   ↓
4. Remove backup file
   ↓
5. Return success message
```

---

## 🧪 Testing Strategy

### Unit Tests
- Each ActionHandler independently
- Security middleware components
- Undo Manager operations

### Integration Tests
- Full execution flow
- Confirmation gate interaction
- Rollback scenarios

### Security Tests
- Path traversal attempts
- Permission violations
- Unauthorized access

### MCP Tests
- Schema translation accuracy
- Protocol compliance
- Claude Desktop integration

---

## 📦 Dependencies

```toml
[dependencies]
pyyaml = "^6.0"
pydantic = "^2.0"
click = "^8.1"
rich = "^13.0"
httpx = "^0.27"
mcp = "^1.0"  # Model Context Protocol SDK
```

---

## 🚀 Deployment Models

### 1. Local CLI
```bash
pip install ai-first-runtime
airun serve
```

### 2. MCP Server (Claude Desktop)
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "ai-first": {
      "command": "airun",
      "args": ["serve", "--mcp"]
    }
  }
}
```

### 3. Docker Container (Future)
```bash
docker run -v ./workspace:/workspace ai-first/runtime
```

---

## 🎯 Design Principles

### 1. Spec-Driven
- Runtime is "dumb" - it only executes what YAML defines
- No hardcoded logic beyond what specs declare

### 2. Security First
- Every operation goes through security layers
- Fail-safe defaults (deny by default)
- Audit trail for all operations

### 3. Undo Everything
- Every write operation is reversible
- Backup before modify
- Clear rollback path

### 4. Protocol Agnostic
- Core runtime independent of MCP
- Easy to add OpenAI Function Calling adapter
- Easy to add REST API adapter

---

## 📈 Success Metrics

### Week 1 Goals
- ✅ 20 ActionHandlers implemented
- ✅ Security middleware functional
- ✅ Undo Manager operational
- ✅ CLI executor working

### Week 2 Goals
- ✅ MCP Adapter complete
- ✅ Claude Desktop integration
- ✅ Demo video recorded

---

## 🔮 Future Enhancements

### Phase 2
- Web UI for operation monitoring
- REST API server
- Multi-user support

### Phase 3
- Distributed execution
- Cloud deployment
- Capability marketplace integration

---

**Architecture Version:** 0.1.0  
**Last Updated:** January 21, 2026  
**Status:** 🚧 Under Active Development
