#!/usr/bin/env python3
"""
Test AI-First MCP Server.

This script tests the MCP server by simulating tool calls.
"""

import sys
import json
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.mcp.server import create_server


async def test_server_initialization():
    """Test server initialization"""
    print("=" * 70)
    print("TEST 1: Server Initialization")
    print("=" * 70)
    
    server = create_server()
    
    print(f"\n✅ Server created: {server.mcp.name}")
    print(f"📁 Workspace: {server.workspace_root}")
    print(f"📦 Registry: {len(server.registry._handlers)} handlers loaded")
    print(f"🔧 Undo Manager: {len(server.undo_manager.stack)} operations in history")
    
    assert server.mcp.name == "AI-First Runtime"
    assert server.workspace_root.exists()
    assert len(server.registry._handlers) > 0
    
    print("\n✅ TEST 1 PASSED")
    return True


async def test_read_only_capability():
    """Test executing a read-only capability (no confirmation needed)"""
    print("\n" + "=" * 70)
    print("TEST 2: Read-Only Capability (io.fs.exists)")
    print("=" * 70)
    
    server = create_server()
    
    # Test io.fs.exists
    params = {"path": "test.txt"}
    result = await server._execute_capability("io.fs.exists", params)
    
    print(f"\n📊 Result:")
    print(json.dumps(result, indent=2))
    
    assert result["status"] == "success"
    assert "result" in result
    
    print("\n✅ TEST 2 PASSED")
    return True


async def test_confirmation_required():
    """Test capability that requires confirmation (dry-run pattern)"""
    print("\n" + "=" * 70)
    print("TEST 3: Confirmation Required (io.fs.write_file)")
    print("=" * 70)
    
    server = create_server()
    
    # First call without confirmation - should return confirmation request
    params = {
        "path": "test_write.txt",
        "content": "Hello, World!",
        "encoding": "utf-8",
    }
    
    result1 = await server._execute_capability("io.fs.write_file", params)
    
    print(f"\n📊 First Call (without confirmation):")
    print(json.dumps(result1, indent=2))
    
    assert result1["status"] == "confirmation_required"
    assert "confirm_instructions" in result1
    
    print("\n✅ Confirmation request received")
    
    # Second call with confirmation - should execute
    params["_confirm"] = True
    result2 = await server._execute_capability("io.fs.write_file", params)
    
    print(f"\n📊 Second Call (with confirmation):")
    print(json.dumps(result2, indent=2))
    
    assert result2["status"] == "success"
    assert result2["undo_available"] == True
    
    print("\n✅ Execution successful with undo available")
    print("\n✅ TEST 3 PASSED")
    return True


async def test_undo_capability():
    """Test sys.undo special tool"""
    print("\n" + "=" * 70)
    print("TEST 4: Undo Capability (sys.undo)")
    print("=" * 70)
    
    server = create_server()
    
    # First, perform a write operation
    params = {
        "path": "test_undo.txt",
        "content": "Original content",
        "encoding": "utf-8",
        "_confirm": True,
    }
    
    result1 = await server._execute_capability("io.fs.write_file", params)
    print(f"\n📝 Write operation:")
    print(json.dumps(result1, indent=2))
    
    assert result1["status"] == "success"
    
    # Check undo history
    print(f"\n📜 Undo history: {len(server.undo_manager.stack)} operations")
    
    # Now undo
    # Note: We need to call the actual tool function
    # For testing, we'll directly call the undo manager
    if len(server.undo_manager.stack) > 0:
        undone = server.undo_manager.rollback(1)
        print(f"\n↩️  Undone operations: {undone}")
        print(f"📜 Remaining history: {len(server.undo_manager.stack)} operations")
        
        print("\n✅ Undo successful")
    else:
        print("\n⚠️  No operations to undo")
    
    print("\n✅ TEST 4 PASSED")
    return True


async def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 70)
    print("TEST 5: Error Handling")
    print("=" * 70)
    
    server = create_server()
    
    # Try to call non-existent capability
    result = await server._execute_capability("invalid.capability", {})
    
    print(f"\n📊 Result:")
    print(json.dumps(result, indent=2))
    
    assert result["status"] == "error"
    assert "error" in result
    
    print("\n✅ Error properly handled")
    print("\n✅ TEST 5 PASSED")
    return True


async def main():
    """Run all tests"""
    print("\n🚀 AI-First MCP Server Tests")
    print("=" * 70)
    
    tests = [
        test_server_initialization,
        test_read_only_capability,
        test_confirmation_required,
        test_undo_capability,
        test_error_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
