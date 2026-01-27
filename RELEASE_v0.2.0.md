# AI-First Runtime v0.2.0 - "The Bridge"

**Release Date:** January 21, 2026  
**Status:** ✅ Production Ready

---

## 🚀 Major Features

### 1. MCP Server Integration

- **Generic Dispatcher:** A single `call_tool` handler now supports all 20+ capabilities, eliminating the need for manual function wrappers. This data-driven architecture means adding new capabilities requires **zero code changes** to the MCP server.
- **Official SDK:** Switched from FastMCP to the official `mcp` SDK for greater flexibility and control over the tool lifecycle.
- **21 Tools Exposed:** All 20 StdLib capabilities plus the special `sys.undo` tool are now available to any MCP client (e.g., Claude Desktop).

### 2. Safety & Confirmation

- **Dry-Run Confirmation Pattern:** A two-phase execution model for dangerous operations. The first call returns a confirmation request, and the second call (with `_confirm: true`) executes the operation. This is ideal for background agents like Claude Desktop.
- **Safety Metadata:** All tool descriptions are now automatically annotated with safety information (⚠️ Side Effects, 🔒 Requires Confirmation, ↩️ Undo Strategy).

### 3. `sys.undo` Special Tool

- **Self-Healing:** For the first time, an AI agent can now undo its own mistakes. The `sys.undo` tool allows Claude to roll back the last operation, providing a critical safety net for complex workflows.

### 4. Session Persistence

- **SQLite Backend:** Session state, including the undo stack, is now persisted to a local SQLite database (`.ai-first/sessions.db`).
- **Connection Isolation:** Each MCP connection is treated as a separate session, preventing cross-talk between different AI conversations.
- **History Recovery:** If the MCP connection drops or the client restarts, the undo history is automatically recovered.

---

## 🧪 Hero Scenario

We successfully tested a complex, multi-step workflow that demonstrates all key features:

1. **List files** (`io.fs.list_dir`)
2. **Read files** (`io.fs.read_file`)
3. **Write incorrect format** (`io.fs.write_file` to `stats.json`)
4. **Undo the mistake** (`sys.undo`)
5. **Write correct format** (`io.fs.write_file` to `stats.csv`)
6. **Verify the result** (`io.fs.exists`)

This proves the runtime is robust enough to handle real-world, error-prone scenarios.

---

## 📚 Documentation

- **Troubleshooting Guide:** Added a section for common Claude Desktop connection issues.
- **Dry-Run Explained:** Clearly documented the two-phase confirmation pattern for end-users.
- **Architecture Deep-Dive:** Updated `ARCHITECTURE.md` with details on the Generic Dispatcher and Session Persistence.

---

## 🔧 How to Use with Claude Desktop

1.  **Install:** `pip install -r requirements.txt`
2.  **Configure Claude Desktop:** Add the following to your `claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "ai-first-runtime": {
          "command": "python3",
          "args": [
            "/path/to/ai-first-runtime/src/runtime/mcp/server_v2.py"
          ]
        }
      }
    }
    ```

3.  **Start Claude Desktop:** The AI-First Runtime will automatically start and expose 21 safe, undoable tools.

---

## 🏆 Conclusion

**v0.2.0 marks the completion of the core AI-First architecture.**

- **The Law:** `ai-first-specs` (v0.1.0)
- **The Executive:** `ai-first-runtime` (v0.2.0)

We have successfully built a system where AI agents can safely and reliably interact with the local environment. The bridge is built.
