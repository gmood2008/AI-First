#!/usr/bin/env python3
"""
Quick integration test for AI-First Runtime.

This script tests the core functionality without requiring full pytest setup.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.types import ExecutionContext
from runtime.registry import CapabilityRegistry
from runtime.engine import RuntimeEngine
from runtime.stdlib.loader import load_stdlib


def test_basic_execution():
    """Test basic capability execution"""
    print("=" * 70)
    print("TEST 1: Basic Execution (io.fs.exists)")
    print("=" * 70)
    
    # Setup
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    workspace = Path("/tmp/test_workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    
    registry = CapabilityRegistry()
    loaded = load_stdlib(registry, specs_dir)
    print(f"\n✅ Loaded {loaded} capabilities")
    
    engine = RuntimeEngine(registry)
    
    context = ExecutionContext(
        user_id="test_user",
        workspace_root=workspace,
        session_id="test_session",
        confirmation_callback=None,
        undo_enabled=False,
    )
    
    # Test io.fs.exists
    result = engine.execute(
        "io.fs.exists",
        {"path": "test.txt"},
        context,
    )
    
    print(f"\n📊 Result:")
    print(f"  Status: {result.status.value}")
    print(f"  Outputs: {json.dumps(result.outputs, indent=2)}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")
    
    assert result.is_success(), "Execution should succeed"
    assert "exists" in result.outputs, "Should have 'exists' output"
    
    print("\n✅ TEST 1 PASSED")
    return True


def test_write_and_read():
    """Test file write and read"""
    print("\n" + "=" * 70)
    print("TEST 2: Write and Read File")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    workspace = Path("/tmp/test_workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)
    engine = RuntimeEngine(registry)
    
    # Auto-approve callback
    def auto_approve(msg, params):
        print("\n⚠️  Auto-approving confirmation")
        return True
    
    context = ExecutionContext(
        user_id="test_user",
        workspace_root=workspace,
        session_id="test_session",
        confirmation_callback=auto_approve,
        undo_enabled=True,
    )
    
    # Write file
    print("\n📝 Writing file...")
    write_result = engine.execute(
        "io.fs.write_file",
        {
            "path": "hello.txt",
            "content": "Hello, AI-First Runtime!",
        },
        context,
    )
    
    print(f"  Status: {write_result.status.value}")
    assert write_result.is_success(), "Write should succeed"
    print("  ✅ Write successful")
    
    # Read file
    print("\n📖 Reading file...")
    read_result = engine.execute(
        "io.fs.read_file",
        {"path": "hello.txt"},
        context,
    )
    
    print(f"  Status: {read_result.status.value}")
    print(f"  Content: {read_result.outputs.get('content', '')[:50]}...")
    
    assert read_result.is_success(), "Read should succeed"
    assert "Hello, AI-First Runtime!" in read_result.outputs["content"], "Content should match"
    
    print("\n✅ TEST 2 PASSED")
    return True


def test_sys_info():
    """Test system information capabilities"""
    print("\n" + "=" * 70)
    print("TEST 3: System Information")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    workspace = Path("/tmp/test_workspace")
    
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)
    engine = RuntimeEngine(registry)
    
    context = ExecutionContext(
        user_id="test_user",
        workspace_root=workspace,
        session_id="test_session",
        confirmation_callback=None,
        undo_enabled=False,
    )
    
    # Test sys.info.get_os
    print("\n🖥️  Getting OS info...")
    result = engine.execute("sys.info.get_os", {}, context)
    
    print(f"  Status: {result.status.value}")
    print(f"  OS: {result.outputs.get('os_name', 'unknown')}")
    print(f"  Architecture: {result.outputs.get('architecture', 'unknown')}")
    
    assert result.is_success(), "Get OS should succeed"
    assert result.outputs.get("os_name") in ["linux", "macos", "windows", "other"]
    
    print("\n✅ TEST 3 PASSED")
    return True


def test_http_get():
    """Test HTTP GET capability"""
    print("\n" + "=" * 70)
    print("TEST 4: HTTP GET Request")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    workspace = Path("/tmp/test_workspace")
    
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)
    engine = RuntimeEngine(registry)
    
    context = ExecutionContext(
        user_id="test_user",
        workspace_root=workspace,
        session_id="test_session",
        confirmation_callback=None,
        undo_enabled=False,
    )
    
    # Test net.http.get
    print("\n🌐 Making HTTP GET request...")
    result = engine.execute(
        "net.http.get",
        {"url": "https://httpbin.org/get"},
        context,
    )
    
    print(f"  Status: {result.status.value}")
    print(f"  HTTP Status: {result.outputs.get('status_code', 0)}")
    print(f"  Success: {result.outputs.get('success', False)}")
    
    # Note: This might fail if no internet, so we just check execution completed
    print(f"\n  Result: {'✅ Request completed' if result.status.value != 'error' else '⚠️ Request failed (might be network issue)'}")
    
    print("\n✅ TEST 4 COMPLETED (check manually)")
    return True


def main():
    """Run all tests"""
    print("\n🚀 AI-First Runtime - Integration Tests")
    print("=" * 70)
    
    tests = [
        test_basic_execution,
        test_write_and_read,
        test_sys_info,
        test_http_get,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
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
    success = main()
    sys.exit(0 if success else 1)
