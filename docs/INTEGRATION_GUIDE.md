# AI-First Runtime: The Hacker's Integration Guide

**Version:** 2.0  
**Author:** Manus AI  
**Last Updated:** January 22, 2026

---

## 1. Introduction

This guide provides practical recipes for integrating AI-First Runtime into your existing development workflow. The goal is to make the runtime a seamless extension of your favorite tools, not a replacement.

For internal partner teams, this guide is also the single entrypoint for delivery and upgrade modes. The authoritative compatibility rules are defined in:

- `docs/COMPATIBILITY_CONTRACT.md`

We will cover three primary integration patterns:

1. **Claude Desktop:** For conversational, task-oriented agentic workflows.
2. **Cursor / VS Code:** For in-editor, code-aware agentic development.
3. **Python Scripts:** For programmatic, automated agentic processes.

### 1.1 Delivery / integration modes (internal)

- **Internal PyPI (wheel)**
  - Install runtime via `pip install ai-first-runtime`
  - Assets default to wheel embedded `share/ai-first-runtime/...`
  - See: `docs/INTERNAL_PYPI_DISTRIBUTION_SOP.md`
- **Offline bundle-first (tar.gz)**
  - Install wheel from `wheels/*.whl` inside the bundle
  - Optional plaintext assets included for deep integration scenarios
- **Plaintext assets mode (deep integration)**
  - Keep runtime code via wheel
  - Override assets via `AI_FIRST_ASSETS_DIR=<assets_root>`
  - See: `docs/PLAINTEXT_ASSETS_MODE_GUIDE.md`
- **Local bridge (subprocess, Aegis P0)**
  - Aegis spawns `airun bridge exec-capability` and consumes strict JSON
  - Golden samples: `tests/bridge/*.json`

---

## 2. Core Concept: The `airun` Server

All integrations work by connecting to a running AI-First Runtime server. The server exposes its capabilities via the **Model Context Protocol (MCP)**, an open standard for AI agent interoperability.

To start the server:

```bash
# From the ai-first-runtime directory
python3 src/runtime/mcp/server_v2.py
```

This will start an MCP server on standard I/O, ready to receive commands from any MCP-compatible client.

---

## 3. Recipe 1: Claude Desktop Integration

**Use Case:** Conversational bug fixing, file management, and system operations with full undo and audit capabilities.

### 3.1. Create `agent_config.json`

Claude Desktop can connect to external tools by defining them in an `agent_config.json` file. We will create one that points to our `airun` server.

**File:** `~/.claude/agent_config.json`

```json
{
  "name": "AI-First Runtime",
  "description": "A safety-first agentic runtime with time-travel debugging, compliance logging, and a smart importer.",
  "tools": [
    {
      "type": "mcp",
      "name": "airun",
      "description": "Connects to the AI-First Runtime server for safe, auditable system operations.",
      "command": [
        "python3",
        "/path/to/your/ai-first-runtime/src/runtime/mcp/server_v2.py"
      ]
    }
  ]
}
```

**Note:** Replace `/path/to/your/ai-first-runtime` with the actual absolute path to your project directory.

### 3.2. How It Works

1. When you start a new conversation in Claude Desktop, it reads this config file.
2. It launches the `airun` server as a subprocess.
3. Claude's agent can now see and call all capabilities exposed by the runtime (e.g., `io.fs.write_file`, `sys.undo`).
4. All actions are logged to `~/.ai-first/audit.db`.

### 3.3. Example Prompt

> **User:**
> Using the `airun` tool, please write a file named `hello.txt` in my home directory with the content "Hello from AI-First!"

Claude will translate this into a call to `airun.io.fs.write_file`.

> **User:**
> Now, undo the last action.

Claude will call `airun.sys.undo`, and the file will be deleted.

---

## 4. Recipe 2: Cursor / VS Code Integration

**Use Case:** In-editor code generation, refactoring, and debugging with AI assistance, backed by the safety of AI-First Runtime.

Cursor (and VS Code with the right extensions) allows defining custom AI tasks. We will create a task that uses `airun` to apply changes safely.

### 4.1. Create `.cursor-tasks.json`

**File:** `.cursor-tasks.json` (in your project's root directory)

```json
{
  "tasks": [
    {
      "name": "Safe Refactor with AI-First",
      "description": "Refactor the selected code using an AI prompt, with the ability to undo.",
      "prompt": "Based on the user query and the selected code, generate a Python script that uses the `airun.io.fs.write_file` capability to apply the changes. The script should first read the original file content.",
      "execute": {
        "type": "shell",
        "command": "python3 -c \"${generated_script}\""
      }
    }
  ]
}
```

### 4.2. How It Works

1. You select a block of code in Cursor.
2. You invoke the "Safe Refactor" task with a prompt (e.g., "add type hints to this function").
3. Cursor's AI generates a Python script that calls `airun.io.fs.write_file` to modify the source file.
4. This script is executed, and the change is applied.
5. If you don't like the change, you can simply run `airun.sys.undo` from your terminal to revert it.

### 4.3. Key Advantage

This pattern separates the **AI generation** (done by Cursor) from the **execution** (done by AI-First Runtime). This means you get the best of both worlds: the powerful code-aware AI of your editor, and the safety-first execution of our runtime.

---

## 5. Recipe 3: Python Script Integration

**Use Case:** Building automated, multi-step agentic workflows (e.g., CI/CD scripts, data processing pipelines).

This is the most powerful pattern, as it gives you full programmatic control.

### 5.1. Example Script: `agent.py`

```python
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from runtime.undo.manager import UndoManager
from runtime.audit import AuditLogger
from runtime.types import ExecutionContext

# 1. Initialize Runtime Components
registry = CapabilityRegistry()
registry.load_specs_from_directory("/path/to/ai-first-specs/capabilities/validated/stdlib")

undo_manager = UndoManager()
audit_logger = AuditLogger()

engine = RuntimeEngine(
    registry=registry,
    undo_manager=undo_manager,
    audit_logger=audit_logger
)

# 2. Create Execution Context
context = ExecutionContext(
    user_id="script_user",
    session_id="agent_run_001",
    confirmation_callback=lambda msg, params: True,  # Auto-confirm
    undo_enabled=True
)

# 3. Define Workflow
def main():
    print("--- Starting Agent Workflow ---")

    # Step 1: Write a file
    print("Step 1: Writing file...")
    result1 = engine.execute(
        "io.fs.write_file",
        {"path": "/tmp/agent_output.txt", "content": "Step 1 complete"},
        context
    )
    if result1.status != "success":
        print(f"Error: {result1.error_message}")
        return

    print(f"  -> Success. Undo stack size: {undo_manager.size()}")

    # Step 2: Make a mistake
    print("Step 2: Writing another file (mistake)...")
    result2 = engine.execute(
        "io.fs.write_file",
        {"path": "/tmp/agent_output_2.txt", "content": "This was a mistake"},
        context
    )
    print(f"  -> Success. Undo stack size: {undo_manager.size()}")

    # Step 3: Undo the mistake
    print("Step 3: Undoing the last action...")
    result3 = engine.execute("sys.undo", {}, context)
    print(f"  -> {result3.outputs.get('description')}")
    print(f"  -> Success. Undo stack size: {undo_manager.size()}")

    print("--- Workflow Complete ---")

if __name__ == "__main__":
    main()
    audit_logger.shutdown()

```

### 5.2. How It Works

1. **Initialization:** You create instances of the `RuntimeEngine`, `UndoManager`, and `AuditLogger`.
2. **Context:** You define an `ExecutionContext` for the entire run.
3. **Execution:** You call `engine.execute()` for each step in your workflow.
4. **Control Flow:** You can use standard Python `if/else` logic to handle results, errors, and retries.
5. **Shutdown:** You call `audit_logger.shutdown()` to ensure all logs are written.

---

## 6. Conclusion

AI-First Runtime is designed to be a modular, interoperable component in your AI engineering stack. By integrating it with your existing tools, you can enhance them with a powerful layer of safety, auditability, and control.

For more advanced use cases, please refer to the full API documentation and handler development documentation.
