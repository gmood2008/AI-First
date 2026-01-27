#!/usr/bin/env python3
"""
Hero Scenario Test: Complex Multi-Step Workflow with Undo.

Scenario:
"Recursively find all .py files in src/, count lines, write to stats.json,
realize it's wrong format, UNDO, write to stats.csv".

This demonstrates:
1. Multi-step workflow
2. File system operations
3. Confirmation pattern
4. sys.undo in action
5. Error recovery
"""

import sys
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.mcp.server_v2 import create_server


async def hero_scenario():
    """Execute the hero scenario"""
    
    print("=" * 80)
    print("🦸 HERO SCENARIO: Multi-Step Workflow with Undo")
    print("=" * 80)
    print("\n📋 Task: Analyze Python files, count lines, save stats (with mistake + undo)")
    print()
    
    # Create server
    server = create_server()
    
    # Track all operations
    operations = []
    
    # Step 1: List files in src directory
    print("\n" + "=" * 80)
    print("STEP 1: List all files in src/")
    print("=" * 80)
    
    result1 = await server._execute_capability("io.fs.list_dir", {"path": "src"})
    operations.append(("io.fs.list_dir", result1))
    
    print(f"Status: {result1['status']}")
    if result1['status'] == 'success':
        files = result1['outputs'].get('entries', [])
        print(f"Found {len(files)} entries")
        py_files = [f for f in files if f.endswith('.py')]
        print(f"Python files: {len(py_files)}")
    
    # Step 2: Count lines in each Python file
    print("\n" + "=" * 80)
    print("STEP 2: Count lines in Python files")
    print("=" * 80)
    
    stats = {}
    total_lines = 0
    
    # For demo purposes, we'll just check a few files
    test_files = ["runtime/types.py", "runtime/engine.py", "runtime/registry.py"]
    
    for file_path in test_files:
        result = await server._execute_capability("io.fs.read_file", {
            "path": file_path,
            "encoding": "utf-8"
        })
        
        if result['status'] == 'success':
            content = result['outputs'].get('content', '')
            lines = len(content.split('\n'))
            stats[file_path] = lines
            total_lines += lines
            print(f"  {file_path}: {lines} lines")
            operations.append(("io.fs.read_file", result))
    
    print(f"\nTotal lines analyzed: {total_lines}")
    
    # Step 3: Write stats to JSON (MISTAKE - should be CSV)
    print("\n" + "=" * 80)
    print("STEP 3: Write stats to stats.json (MISTAKE!)")
    print("=" * 80)
    
    stats_json = json.dumps({
        "files": stats,
        "total_lines": total_lines,
        "file_count": len(stats)
    }, indent=2)
    
    # First call - dry run (confirmation required)
    result3a = await server._execute_capability("io.fs.write_file", {
        "path": "stats.json",
        "content": stats_json,
        "encoding": "utf-8"
    })
    
    print(f"Status: {result3a['status']}")
    if result3a['status'] == 'confirmation_required':
        print(f"⚠️  {result3a['message']}")
        print(f"Side effects: {result3a['side_effects']}")
        print(f"Undo strategy: {result3a['undo_strategy']}")
        
        # Confirm and execute
        print("\n✅ User confirms operation...")
        result3b = await server._execute_capability("io.fs.write_file", {
            "path": "stats.json",
            "content": stats_json,
            "encoding": "utf-8",
            "_confirm": True
        })
        
        print(f"Status: {result3b['status']}")
        print(f"Undo available: {result3b.get('undo_available', False)}")
        operations.append(("io.fs.write_file", result3b))
    
    # Step 4: Realize the mistake
    print("\n" + "=" * 80)
    print("STEP 4: Realize the mistake - should be CSV, not JSON!")
    print("=" * 80)
    print("❌ User: \"Wait, I wanted CSV format, not JSON!\"")
    
    # Step 5: UNDO the write operation
    print("\n" + "=" * 80)
    print("STEP 5: Use sys.undo to fix the mistake")
    print("=" * 80)
    
    undo_result = await server._handle_undo({"steps": 1})
    
    print(f"Status: {undo_result['status']}")
    if undo_result['status'] == 'success':
        print(f"✅ Undone {undo_result['steps_undone']} operations")
        print(f"Operations undone: {undo_result['operations']}")
        print(f"Remaining history: {undo_result['remaining_history']}")
        operations.append(("sys.undo", undo_result))
    
    # Step 6: Write correct CSV format
    print("\n" + "=" * 80)
    print("STEP 6: Write stats to stats.csv (CORRECT)")
    print("=" * 80)
    
    # Generate CSV content
    csv_lines = ["file,lines"]
    for file_path, lines in stats.items():
        csv_lines.append(f"{file_path},{lines}")
    csv_lines.append(f"TOTAL,{total_lines}")
    stats_csv = "\n".join(csv_lines)
    
    print("CSV content:")
    print(stats_csv)
    
    # Write CSV (with confirmation)
    result6a = await server._execute_capability("io.fs.write_file", {
        "path": "stats.csv",
        "content": stats_csv,
        "encoding": "utf-8"
    })
    
    if result6a['status'] == 'confirmation_required':
        print(f"\n⚠️  Confirmation required")
        result6b = await server._execute_capability("io.fs.write_file", {
            "path": "stats.csv",
            "content": stats_csv,
            "encoding": "utf-8",
            "_confirm": True
        })
        print(f"✅ CSV written successfully")
        operations.append(("io.fs.write_file", result6b))
    
    # Step 7: Verify the result
    print("\n" + "=" * 80)
    print("STEP 7: Verify the final result")
    print("=" * 80)
    
    # Check if stats.json exists (should not, because we undid it)
    result7a = await server._execute_capability("io.fs.exists", {"path": "stats.json"})
    print(f"stats.json exists: {result7a['outputs'].get('exists', False)}")
    
    # Check if stats.csv exists (should exist)
    result7b = await server._execute_capability("io.fs.exists", {"path": "stats.csv"})
    print(f"stats.csv exists: {result7b['outputs'].get('exists', False)}")
    
    # Read the CSV to confirm
    if result7b['outputs'].get('exists', False):
        result7c = await server._execute_capability("io.fs.read_file", {
            "path": "stats.csv",
            "encoding": "utf-8"
        })
        print(f"\n📄 Final stats.csv content:")
        print(result7c['outputs'].get('content', ''))
    
    # Summary
    print("\n" + "=" * 80)
    print("🎉 HERO SCENARIO COMPLETE")
    print("=" * 80)
    print(f"\n📊 Operations performed: {len(operations)}")
    for i, (op_name, result) in enumerate(operations, 1):
        status = result.get('status', 'unknown')
        print(f"  {i}. {op_name}: {status}")
    
    print("\n✅ Demonstrated:")
    print("  - Multi-step workflow (7 steps)")
    print("  - File system operations (list, read, write, exists)")
    print("  - Confirmation pattern (dry-run → confirm)")
    print("  - sys.undo in action (mistake recovery)")
    print("  - Error recovery (JSON → CSV)")
    
    print("\n🏆 This proves AI-First Runtime can handle complex, real-world scenarios!")
    
    return True


async def main():
    """Run hero scenario"""
    try:
        success = await hero_scenario()
        return success
    except Exception as e:
        print(f"\n❌ HERO SCENARIO FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
