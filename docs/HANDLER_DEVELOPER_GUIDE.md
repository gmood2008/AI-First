# AI-First Runtime: Handler Developer Guide

**Version:** 1.0  
**Date:** January 21, 2026  
**Audience:** Developers building capabilities for AI-First Runtime

---

## 1. The New Paradigm: Safe, Reliable, Undoable Operations

Welcome to the new era of AI agent development. In AI-First Runtime, safety and reliability are not afterthoughts—they are the foundation. The key to this foundation is the **`ActionOutput` and Closure-Based Undo Pattern**.

This pattern is our primary competitive advantage—our moat—against other agentic frameworks like LangChain or LlamaIndex. It enables agents to perform complex, real-world operations with a safety net, allowing them to experiment, make mistakes, and automatically roll back, without causing irreversible harm to the system.

This guide explains how to build handlers that fully leverage this powerful new paradigm.

---

## 2. Core Concepts

### 2.1 `ActionOutput`: The Structured Return Type

All handler `execute` methods **must** now return an `ActionOutput` object. This is a structured data class that standardizes the output of every capability.

**Definition (`src/runtime/types.py`):**
```python
@dataclass
class ActionOutput:
    result: Dict[str, Any]
    description: str
    undo_closure: Optional[Callable[[], None]] = None
```

| Field | Type | Description |
|---|---|---|
| `result` | `Dict[str, Any]` | The actual output of the capability, matching the `outputs` defined in the YAML spec. |
| `description` | `str` | A human-readable sentence describing what the operation did (e.g., "Wrote 1,024 bytes to /home/ubuntu/file.txt"). Used for logging and undo history. |
| `undo_closure` | `Optional[Callable]` | A **closure** function that reverses the operation. This is the core of the undo mechanism. **Required for all write operations.** |

### 2.2 The `undo_closure`: Self-Contained Reversal Logic

A closure is a function that remembers the environment in which it was created. In our pattern, the `undo_closure` is a nested function defined inside your `execute` method. This is incredibly powerful because it **captures the state of the system *at the moment of execution***.

**Why Closures are a Game-Changer:**

- **Stateful:** The closure automatically has access to variables from its parent `execute` function (e.g., `backup_content`, `file_existed`). You don't need to pass state around.
- **Self-Contained:** All logic and data required to perform the undo are packaged together. The `UndoManager` doesn't need to know *how* to undo an operation; it just needs to execute the closure.
- **Robust:** It avoids the brittleness of file-based backups or re-calculating the previous state. The exact state is preserved.

---

## 3. The Old Way vs. The New Way

### The Old Way (Deprecated)

Previously, handlers returned a simple dictionary. This was ambiguous and unsafe.

```python
# OLD WAY - DO NOT DO THIS
def execute(self, params: Dict[str, Any], context: Any) -> dict:
    # ... logic ...
    # No standard for undo, no clear description
    return {"success": True, "bytes_written": 100}
```

**Problems:**
- No enforced structure.
- No standard way to provide undo logic.
- Undo mechanism was complex and external to the handler (relying on file backups).

### The New Way: The `ActionOutput` Pattern

All handlers now follow a clear, safe, and standardized pattern.

```python
# NEW WAY - THE CORRECT PATTERN
from runtime.types import ActionOutput

def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
    # 1. Capture pre-state
    file_path = Path(params["path"])
    file_existed = file_path.exists()
    backup_content = file_path.read_text() if file_existed else None

    # 2. Perform the operation
    file_path.write_text(params["content"])

    # 3. Define the undo closure
    def undo():
        if file_existed:
            file_path.write_text(backup_content)  # Restore
        else:
            file_path.unlink()  # Delete

    # 4. Return the structured output
    return ActionOutput(
        result={"success": True, "bytes_written": len(params["content"])},
        description=f"Wrote content to {file_path}",
        undo_closure=undo
    )
```

---

## 4. Step-by-Step Guide to Building a Handler with Undo

Follow these steps for any capability that modifies state (writes files, makes API calls, etc.).

### Step 1: Define the `execute` Method

Ensure your method signature correctly type-hints the return value as `ActionOutput`.

```python
from runtime.handler import ActionHandler
from runtime.types import ActionOutput
from typing import Dict, Any

class MyWriteHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        # ... your logic here
```

### Step 2: Capture Pre-State

Before you make any changes, capture all the information needed to reverse them. Store this in local variables.

```python
# Inside execute()
path_str = params["path"]
full_path = Path(path_str)

# Capture state BEFORE the operation
file_existed = full_path.exists()
original_content = full_path.read_text() if file_existed else None
```

### Step 3: Perform the Write Operation

Now, execute the core logic of your capability.

```python
# Inside execute()
try:
    full_path.write_text(params["content"])
except Exception as e:
    # Handle errors and return an ActionOutput with no undo_closure
    return ActionOutput(
        result={"success": False, "error": str(e)},
        description=f"Failed to write to {path_str}",
        undo_closure=None
    )
```

### Step 4: Define the `undo` Closure

Create a nested function, typically named `undo`, that uses the variables captured in Step 2 to reverse the operation.

```python
# Inside execute(), after the write operation
def undo():
    """Reverses the write operation."""
    if file_existed:
        # If the file existed, restore its original content
        full_path.write_text(original_content)
    else:
        # If the file was newly created, delete it
        full_path.unlink(missing_ok=True)
```

### Step 5: Return `ActionOutput`

Finally, package everything into an `ActionOutput` object. For write operations, the `undo_closure` field is **mandatory**.

```python
# Inside execute(), at the end
return ActionOutput(
    result={
        "success": True,
        "bytes_written": len(params["content"])
    },
    description=f"Wrote {len(params["content"])} characters to {path_str}",
    undo_closure=undo
)
```

For **read-only** operations, simply set `undo_closure=None`.

---

## 5. Full Example: `io.fs.write_file` Handler

This is the complete, production-ready implementation of the `WriteFileHandler`. Study it carefully.

```python
from runtime.handler import ActionHandler
from runtime.types import ActionOutput
from typing import Dict, Any
from pathlib import Path

class WriteFileHandler(ActionHandler):
    """Handler for io.fs.write_file"""

    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        path_str = params["path"]
        content = params["content"]
        encoding = params.get("encoding", "utf-8")
        create_dirs = params.get("create_dirs", False)

        try:
            full_path = Path(path_str)

            # --- Step 1: Capture Pre-State ---
            file_existed = full_path.exists()
            backup_content = full_path.read_bytes() if file_existed else None

            # --- Step 2: Perform Operation ---
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            
            full_path.write_text(content, encoding=encoding)

            # --- Step 3: Define Undo Closure ---
            def undo():
                """Undo the write operation by restoring the original state."""
                if file_existed:
                    # If the file existed, restore its original content
                    full_path.write_bytes(backup_content)
                else:
                    # If the file was newly created by this operation, delete it
                    full_path.unlink(missing_ok=True)

            # --- Step 4: Return ActionOutput ---
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
                    "error": str(e),
                },
                undo_closure=None,
                description=f"Failed to write to {path_str}: {e}"
            )
```

---

## 6. Best Practices for Undo Closures

1.  **Handle All Cases:** Your undo logic should correctly handle both creation (file didn't exist) and modification (file existed).
2.  **Be Atomic:** The pre-state capture and the operation should be as close together as possible to minimize race conditions.
3.  **Use `missing_ok=True`:** When deleting a file in an undo operation (e.g., `unlink()`), use `missing_ok=True` to prevent errors if the file was already deleted by another process.
4.  **Think Idempotently:** While not always possible, strive to make your undo operations idempotent. Running `undo()` twice should have the same effect as running it once.
5.  **Test Your Undos:** Always write a `pytest` test case specifically for the undo functionality of your handler. Execute the operation, then call the returned `undo_closure()` and assert that the system has returned to its original state.

By following this guide, you will contribute to a more robust, safe, and powerful AI-First Runtime ecosystem. Welcome to the future of agentic of agentic computing.
