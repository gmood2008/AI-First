#!/usr/bin/env python3
"""
Test schema translation from AI-First YAML to MCP JSON Schema.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.mcp.schema_translator import SchemaTranslator, create_mcp_tools_from_stdlib


def test_single_translation():
    """Test translating a single capability"""
    print("=" * 70)
    print("TEST 1: Single Capability Translation (io.fs.read_file)")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    translator = SchemaTranslator()
    
    # Translate io.fs.read_file
    tool_def = translator.translate_from_file(specs_dir / "io_fs_read_file.yaml")
    
    print(f"\n✅ Translated: {tool_def['name']}")
    print(f"📝 Title: {tool_def['title']}")
    print(f"📄 Description: {tool_def['description'][:100]}...")
    
    print(f"\n📥 Input Schema:")
    print(json.dumps(tool_def["inputSchema"], indent=2))
    
    print(f"\n📤 Output Schema:")
    print(json.dumps(tool_def["outputSchema"], indent=2))
    
    # Validate structure
    assert "name" in tool_def
    assert "description" in tool_def
    assert "inputSchema" in tool_def
    assert tool_def["inputSchema"]["type"] == "object"
    assert "properties" in tool_def["inputSchema"]
    
    print("\n✅ TEST 1 PASSED")
    return True


def test_multiple_translation():
    """Test translating all stdlib capabilities"""
    print("\n" + "=" * 70)
    print("TEST 2: Multiple Capabilities Translation (All StdLib)")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    tools = create_mcp_tools_from_stdlib(specs_dir)
    
    print(f"\n✅ Translated {len(tools)} capabilities")
    
    # Group by namespace
    namespaces = {}
    for tool in tools:
        parts = tool["name"].split(".")
        namespace = ".".join(parts[:-1])
        
        if namespace not in namespaces:
            namespaces[namespace] = []
        namespaces[namespace].append(tool["name"])
    
    print(f"\n📦 Namespaces:")
    for namespace, caps in sorted(namespaces.items()):
        print(f"  {namespace}: {len(caps)} capabilities")
        for cap in sorted(caps):
            print(f"    - {cap}")
    
    # Validate all tools
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
    
    print(f"\n✅ TEST 2 PASSED")
    return True


def test_dangerous_operation_annotation():
    """Test that dangerous operations are properly annotated"""
    print("\n" + "=" * 70)
    print("TEST 3: Dangerous Operation Annotation")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    translator = SchemaTranslator()
    
    # Test io.fs.delete (dangerous operation)
    tool_def = translator.translate_from_file(specs_dir / "io_fs_delete.yaml")
    
    print(f"\n🔍 Checking: {tool_def['name']}")
    print(f"📄 Description:\n{tool_def['description']}")
    
    # Should contain warnings
    assert "Side Effects" in tool_def["description"]
    assert "Requires Confirmation" in tool_def["description"]
    assert "Undo Strategy" in tool_def["description"]
    
    print("\n✅ Dangerous operation properly annotated")
    print("✅ TEST 3 PASSED")
    return True


def test_output_to_file():
    """Test exporting MCP tools to JSON file"""
    print("\n" + "=" * 70)
    print("TEST 4: Export to JSON File")
    print("=" * 70)
    
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
    tools = create_mcp_tools_from_stdlib(specs_dir)
    
    # Export to file
    output_path = Path("/tmp/mcp_tools.json")
    with open(output_path, "w") as f:
        json.dump(tools, f, indent=2)
    
    print(f"\n✅ Exported {len(tools)} tools to {output_path}")
    print(f"📊 File size: {output_path.stat().st_size} bytes")
    
    # Verify file is valid JSON
    with open(output_path, "r") as f:
        loaded_tools = json.load(f)
    
    assert len(loaded_tools) == len(tools)
    
    print("\n✅ TEST 4 PASSED")
    return True


def main():
    """Run all tests"""
    print("\n🚀 AI-First → MCP Schema Translation Tests")
    print("=" * 70)
    
    tests = [
        test_single_translation,
        test_multiple_translation,
        test_dangerous_operation_annotation,
        test_output_to_file,
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
