# Smart Importer Architecture Design

**Version:** 1.0  
**Date:** January 21, 2026  
**Status:** Design Phase

---

## 1. Mission Statement

**Goal:** Zero-friction adoption of external tools into AI-First Runtime.

**Strategy:** Use LLM to analyze raw Python code or OpenAPI specs, and automatically generate AI-First YAML capability specifications.

**Key Requirement:** Automatically detect `side_effects` and flag them (e.g., `requests.post` → `network_write`).

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    forge import <source>                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │   Source Type Detection     │
         │  (Python / OpenAPI / URL)   │
         └──────────┬──────────────────┘
                    │
        ┏━━━━━━━━━━━┻━━━━━━━━━━━┓
        ▼                        ▼
┌───────────────┐        ┌──────────────┐
│ Python Parser │        │ OpenAPI      │
│ (AST Analysis)│        │ Parser       │
└───────┬───────┘        └──────┬───────┘
        │                       │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  LLM Spec Generator   │
        │  (GPT-4.1-mini)       │
        │                       │
        │  - Extract metadata   │
        │  - Infer parameters   │
        │  - Detect side effects│
        │  - Generate undo logic│
        └───────┬───────────────┘
                │
                ▼
        ┌───────────────────────┐
        │  Critic Agent         │
        │  (Validation Layer)   │
        │                       │
        │  - Schema validation  │
        │  - Safety checks      │
        │  - Undo strategy req. │
        └───────┬───────────────┘
                │
                ▼
        ┌───────────────────────┐
        │  YAML Generator       │
        │  (Structured Output)  │
        └───────┬───────────────┘
                │
                ▼
        ┌───────────────────────┐
        │  Handler Scaffolder   │
        │  (Python Code Gen)    │
        └───────┬───────────────┘
                │
                ▼
        ┌───────────────────────┐
        │  Output:              │
        │  - capability.yaml    │
        │  - handler.py         │
        │  - test_handler.py    │
        └───────────────────────┘
```

---

## 3. Component Design

### 3.1 Source Type Detection

**Input:** File path, URL, or raw code string  
**Output:** Source type enum (PYTHON_FILE, PYTHON_CODE, OPENAPI_SPEC, URL)

**Logic:**
```python
def detect_source_type(source: str) -> SourceType:
    if source.startswith("http://") or source.startswith("https://"):
        return SourceType.URL
    elif source.endswith(".yaml") or source.endswith(".json"):
        return SourceType.OPENAPI_SPEC
    elif source.endswith(".py"):
        return SourceType.PYTHON_FILE
    else:
        return SourceType.PYTHON_CODE
```

---

### 3.2 Python Parser (AST Analysis)

**Purpose:** Extract function signatures, docstrings, and detect side effects from Python code.

**Key Features:**
- Parse Python AST using `ast` module
- Extract function name, parameters, return type, docstring
- Detect side effects by analyzing:
  - Function calls: `requests.post`, `os.remove`, `shutil.move`
  - File operations: `open(..., 'w')`, `Path.write_text()`
  - System calls: `subprocess.run()`, `os.system()`
  - Network operations: `socket.connect()`, `urllib.request.urlopen()`

**Side Effect Detection Rules:**

| Pattern | Side Effect Type |
|---------|------------------|
| `requests.post/put/delete` | `network_write` |
| `requests.get` | `network_read` |
| `open(..., 'w'/'a')` | `filesystem_write` |
| `open(..., 'r')` | `filesystem_read` |
| `os.remove/unlink` | `filesystem_delete` |
| `shutil.move/copy` | `filesystem_write` |
| `subprocess.run/call` | `system_exec` |
| `os.system` | `system_exec` |

**Example:**
```python
def analyze_python_function(code: str) -> FunctionInfo:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return FunctionInfo(
                name=node.name,
                params=extract_params(node.args),
                docstring=ast.get_docstring(node),
                side_effects=detect_side_effects(node),
                return_type=extract_return_type(node),
            )
```

---

### 3.3 OpenAPI Parser

**Purpose:** Extract endpoint information from OpenAPI/Swagger specs.

**Key Features:**
- Parse YAML/JSON OpenAPI spec
- Extract paths, methods, parameters, responses
- Detect side effects by HTTP method:
  - `GET` → `network_read`
  - `POST/PUT/PATCH/DELETE` → `network_write`

**Example:**
```python
def analyze_openapi_endpoint(spec: dict, path: str, method: str) -> EndpointInfo:
    endpoint = spec["paths"][path][method]
    return EndpointInfo(
        path=path,
        method=method,
        summary=endpoint.get("summary", ""),
        parameters=extract_parameters(endpoint),
        side_effects=["network_write"] if method in ["POST", "PUT", "DELETE"] else ["network_read"],
    )
```

---

### 3.4 LLM Spec Generator

**Purpose:** Use LLM to generate AI-First YAML spec from extracted function/endpoint info.

**Model:** `gpt-4.1-mini` (fast, cheap, good for structured output)

**Prompt Template:**
```
You are a capability specification generator for AI-First Runtime.

Given the following function/endpoint information:
- Name: {name}
- Parameters: {params}
- Docstring: {docstring}
- Side Effects: {side_effects}
- Return Type: {return_type}

Generate a complete AI-First capability specification in YAML format.

Requirements:
1. Use the standard AI-First spec schema (meta, contracts, behavior, interface)
2. Automatically detect and list all side_effects
3. If side_effects include write operations, MUST provide an undo_strategy
4. Set requires_confirmation=true for destructive operations
5. Infer parameter types from function signature
6. Generate clear, concise descriptions

Output ONLY valid YAML, no explanations.
```

**Structured Output Schema (Pydantic):**
```python
class CapabilitySpec(BaseModel):
    meta: MetaInfo
    contracts: Contracts
    behavior: Behavior
    interface: Interface

class Contracts(BaseModel):
    side_effects: List[Literal[
        "filesystem_read", "filesystem_write", "filesystem_delete",
        "network_read", "network_write",
        "system_exec", "state_mutation"
    ]]
    requires_confirmation: bool
    idempotent: bool
    timeout_seconds: int = 30

class Behavior(BaseModel):
    undo_strategy: str  # REQUIRED if side_effects include write operations
    cost_model: Literal["free", "low_io", "high_io", "network", "compute"]
```

**Key Validation:**
- If `side_effects` contains write operations (`filesystem_write`, `network_write`, `system_exec`), `undo_strategy` MUST be non-empty
- If `requires_confirmation=true`, `undo_strategy` MUST be provided
- All `side_effects` values MUST be from the enum list

---

### 3.5 Critic Agent (Validation Layer)

**Purpose:** Validate LLM-generated spec for safety and completeness.

**Validation Rules:**

1. **Schema Validation**
   - Use Pydantic to validate YAML structure
   - Ensure all required fields are present
   - Check enum values for `side_effects`, `cost_model`

2. **Safety Checks**
   - If `side_effects` contains write operations, `undo_strategy` MUST exist
   - If `requires_confirmation=false` but has destructive side effects, reject
   - If `undo_strategy` is generic ("N/A", "None"), reject

3. **Completeness Checks**
   - All parameters must have `type`, `description`, `required`
   - All outputs must have `type`, `description`
   - `meta.description` must be non-empty

**Prompt Template for Critic:**
```
You are a safety critic for AI-First Runtime capability specifications.

Review the following generated spec:
{spec_yaml}

Check for the following issues:
1. Missing undo_strategy for write operations
2. Vague or generic undo_strategy ("N/A", "None")
3. Missing required fields (description, parameter types)
4. Invalid side_effects values
5. Safety concerns (destructive operations without confirmation)

If ANY issues are found, respond with:
{
  "valid": false,
  "issues": ["issue 1", "issue 2", ...]
}

If the spec is valid, respond with:
{
  "valid": true,
  "issues": []
}
```

**Retry Logic:**
- If Critic rejects, send feedback to LLM Spec Generator
- Max 3 retries
- If still invalid after 3 retries, ask user for manual intervention

---

### 3.6 Handler Scaffolder

**Purpose:** Generate Python handler code from validated YAML spec.

**Output Files:**
1. `{capability_id}_handler.py` - Handler implementation
2. `test_{capability_id}_handler.py` - Unit tests

**Handler Template:**
```python
from runtime.handler import ActionHandler
from runtime.types import ActionOutput
from typing import Dict, Any

class {ClassName}Handler(ActionHandler):
    """Handler for {capability_id}"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        # TODO: Implement capability logic
        {param_extraction}
        
        # Capture state for undo
        {state_capture}
        
        # Execute operation
        {operation_logic}
        
        # Create undo closure
        def undo():
            {undo_logic}
        
        return ActionOutput(
            result={result_dict},
            undo_closure=undo if {has_side_effects} else None,
            description="{description}"
        )
```

**Test Template:**
```python
import pytest
from {handler_module} import {ClassName}Handler
from runtime.types import ExecutionContext

def test_{capability_id}_basic():
    handler = {ClassName}Handler(spec_dict)
    context = ExecutionContext(...)
    
    result = handler.execute({test_params}, context)
    
    assert result.result["success"] == True
    assert result.undo_closure is not None  # if has side effects

def test_{capability_id}_undo():
    # TODO: Test undo functionality
    pass
```

---

## 4. CLI Interface

### 4.1 Command Syntax

```bash
# Import from Python file
forge import path/to/function.py --function my_function

# Import from Python code string
forge import --code "def my_func(x): return x * 2"

# Import from OpenAPI spec
forge import path/to/openapi.yaml --endpoint /users --method POST

# Import from URL (fetch and analyze)
forge import https://api.example.com/openapi.json --endpoint /users --method POST

# Batch import (all functions in a file)
forge import path/to/module.py --all

# Interactive mode (ask user for missing info)
forge import path/to/function.py --interactive
```

### 4.2 Output Options

```bash
# Output directory (default: ./capabilities/)
forge import ... --output ./my_capabilities/

# Generate handler code
forge import ... --generate-handler

# Generate tests
forge import ... --generate-tests

# Dry run (show spec without writing files)
forge import ... --dry-run

# Verbose mode (show LLM prompts and responses)
forge import ... --verbose
```

---

## 5. Example Workflow

### Example 1: Import Python Function

**Input:**
```python
# my_tool.py
import requests

def send_slack_message(channel: str, message: str, token: str) -> dict:
    """Send a message to a Slack channel.
    
    Args:
        channel: Slack channel ID or name
        message: Message text to send
        token: Slack API token
    
    Returns:
        dict: Response from Slack API
    """
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "text": message}
    )
    return response.json()
```

**Command:**
```bash
forge import my_tool.py --function send_slack_message --generate-handler
```

**Output:**

1. **Generated YAML (`net.slack.send_message.yaml`):**
```yaml
meta:
  id: net.slack.send_message
  version: 1.0.0
  author: Auto-generated by Smart Importer
  description: Send a message to a Slack channel

contracts:
  side_effects:
    - network_write
  requires_confirmation: false
  idempotent: false
  timeout_seconds: 30

behavior:
  undo_strategy: "Cannot undo message send, but can delete message using chat.delete API with returned message timestamp"
  cost_model: network

interface:
  inputs:
    channel:
      type: string
      description: Slack channel ID or name
      required: true
    message:
      type: string
      description: Message text to send
      required: true
    token:
      type: string
      description: Slack API token
      required: true
      sensitive: true
  outputs:
    success:
      type: boolean
      description: Whether message was sent successfully
    message_ts:
      type: string
      description: Timestamp of sent message (for undo)
```

2. **Generated Handler (`net_slack_send_message_handler.py`):**
```python
from runtime.handler import ActionHandler
from runtime.types import ActionOutput
from typing import Dict, Any
import requests

class SendMessageHandler(ActionHandler):
    """Handler for net.slack.send_message"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        channel = params["channel"]
        message = params["message"]
        token = params["token"]
        
        # Execute operation
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel, "text": message}
        )
        result = response.json()
        
        # Create undo closure
        message_ts = result.get("ts")
        def undo():
            if message_ts:
                requests.post(
                    "https://slack.com/api/chat.delete",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"channel": channel, "ts": message_ts}
                )
        
        return ActionOutput(
            result={
                "success": result.get("ok", False),
                "message_ts": message_ts,
            },
            undo_closure=undo,
            description=f"Sent message to {channel}"
        )
```

---

### Example 2: Import OpenAPI Endpoint

**Input:**
```yaml
# openapi.yaml
paths:
  /users:
    post:
      summary: Create a new user
      parameters:
        - name: username
          in: body
          required: true
          schema:
            type: string
        - name: email
          in: body
          required: true
          schema:
            type: string
      responses:
        201:
          description: User created
          schema:
            type: object
            properties:
              id:
                type: integer
              username:
                type: string
```

**Command:**
```bash
forge import openapi.yaml --endpoint /users --method POST --generate-handler
```

**Output:**

1. **Generated YAML (`api.users.create.yaml`):**
```yaml
meta:
  id: api.users.create
  version: 1.0.0
  author: Auto-generated by Smart Importer
  description: Create a new user

contracts:
  side_effects:
    - network_write
    - state_mutation
  requires_confirmation: false
  idempotent: false
  timeout_seconds: 30

behavior:
  undo_strategy: "Delete created user using DELETE /users/{id} endpoint"
  cost_model: network

interface:
  inputs:
    username:
      type: string
      description: Username for the new user
      required: true
    email:
      type: string
      description: Email address for the new user
      required: true
  outputs:
    id:
      type: integer
      description: ID of created user
    username:
      type: string
      description: Username of created user
```

2. **Generated Handler (`api_users_create_handler.py`):**
```python
from runtime.handler import ActionHandler
from runtime.types import ActionOutput
from typing import Dict, Any
import requests

class CreateUserHandler(ActionHandler):
    """Handler for api.users.create"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        username = params["username"]
        email = params["email"]
        
        # Execute operation
        response = requests.post(
            "https://api.example.com/users",
            json={"username": username, "email": email}
        )
        result = response.json()
        user_id = result["id"]
        
        # Create undo closure
        def undo():
            requests.delete(f"https://api.example.com/users/{user_id}")
        
        return ActionOutput(
            result={
                "id": user_id,
                "username": result["username"],
            },
            undo_closure=undo,
            description=f"Created user {username}"
        )
```

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure (Day 1-2)
- [ ] Implement `SourceType` detection
- [ ] Build Python AST parser
- [ ] Build OpenAPI parser
- [ ] Create `FunctionInfo` and `EndpointInfo` data structures

### Phase 2: LLM Integration (Day 3-4)
- [ ] Design LLM prompt templates
- [ ] Implement LLM Spec Generator with structured output
- [ ] Build Critic Agent validation layer
- [ ] Add retry logic with feedback loop

### Phase 3: Code Generation (Day 5)
- [ ] Build Handler Scaffolder
- [ ] Create handler and test templates
- [ ] Implement file output logic

### Phase 4: CLI Interface (Day 6)
- [ ] Build `forge import` command
- [ ] Add argument parsing
- [ ] Implement dry-run and verbose modes
- [ ] Add interactive mode

### Phase 5: Testing & Documentation (Day 7)
- [ ] Test with real-world examples (requests, OpenAPI specs)
- [ ] Write user guide
- [ ] Create video demo
- [ ] Update README

---

## 7. Safety Considerations

### 7.1 LLM Output Validation
- **Always** use Pydantic schema validation
- **Never** trust LLM output without validation
- **Always** run Critic Agent before accepting spec

### 7.2 Side Effect Detection
- Use **whitelist** approach (known safe patterns) rather than blacklist
- **Flag unknown patterns** for manual review
- **Require confirmation** for operations with unclear side effects

### 7.3 Undo Strategy Requirements
- **Enforce** non-empty undo_strategy for write operations
- **Reject** generic strategies ("N/A", "None", "Cannot undo")
- **Require** specific undo logic (e.g., "Delete file X", "Restore from backup Y")

### 7.4 User Confirmation
- **Always** show generated spec to user before writing files
- **Require** explicit confirmation for destructive operations
- **Provide** dry-run mode for review

---

## 8. Success Metrics

### 8.1 Functional Metrics
- [ ] Successfully import 10+ real-world Python functions
- [ ] Successfully import 5+ OpenAPI endpoints
- [ ] 100% of generated specs pass Pydantic validation
- [ ] 100% of write operations have valid undo_strategy

### 8.2 Quality Metrics
- [ ] Generated handlers compile without errors
- [ ] Generated tests run without errors
- [ ] Side effect detection accuracy > 95%
- [ ] Undo strategy quality (manual review) > 90%

### 8.3 User Experience Metrics
- [ ] Time to import: < 30 seconds per function
- [ ] User confirmation rate: > 80% (accept generated specs)
- [ ] Manual intervention rate: < 10%

---

## 9. Future Enhancements

### 9.1 Multi-Language Support
- JavaScript/TypeScript function analysis
- Go function analysis
- Rust function analysis

### 9.2 Advanced Side Effect Detection
- Static analysis with dataflow tracking
- Integration with security scanners (Bandit, Semgrep)
- Machine learning-based pattern detection

### 9.3 Undo Logic Generation
- Automatic undo code generation (not just strategy description)
- Undo testing framework
- Undo verification (prove correctness)

### 9.4 Ecosystem Integration
- GitHub Actions integration (auto-import on PR)
- VS Code extension (import from editor)
- Package registry (share imported capabilities)

---

## 10. References

- AI-First Runtime Spec Schema: `/specs/README.md`
- Handler Interface: `/src/runtime/handler.py`
- ActionOutput Pattern: `/src/runtime/types.py`
- Undo Mechanism: `/src/runtime/undo/manager.py`

---

**End of Design Document**
