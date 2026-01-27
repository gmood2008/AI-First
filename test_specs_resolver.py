"""
Test script for specs_resolver cross-platform compatibility.

This script tests the specs_dir resolution logic without requiring
the actual ai-first-specs repository to be present.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from runtime.mcp.specs_resolver import resolve_specs_dir


def test_env_var_resolution():
    """Test resolution via environment variable."""
    print("\n" + "="*60)
    print("TEST 1: Environment Variable Resolution")
    print("="*60)
    
    # Create a temporary specs directory
    temp_specs = Path("/tmp/test_specs")
    temp_specs.mkdir(exist_ok=True)
    
    # Set environment variable
    os.environ["AI_FIRST_SPECS_DIR"] = str(temp_specs)
    
    try:
        result = resolve_specs_dir()
        print(f"✅ PASS: Resolved to {result}")
        assert result == temp_specs, f"Expected {temp_specs}, got {result}"
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    finally:
        # Clean up
        del os.environ["AI_FIRST_SPECS_DIR"]
        temp_specs.rmdir()
    
    return True


def test_custom_path_resolution():
    """Test resolution via custom path parameter."""
    print("\n" + "="*60)
    print("TEST 2: Custom Path Resolution")
    print("="*60)
    
    # Create a temporary specs directory
    temp_specs = Path("/tmp/test_custom_specs")
    temp_specs.mkdir(exist_ok=True)
    
    try:
        result = resolve_specs_dir(custom_path=temp_specs)
        print(f"✅ PASS: Resolved to {result}")
        assert result == temp_specs, f"Expected {temp_specs}, got {result}"
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    finally:
        # Clean up
        temp_specs.rmdir()
    
    return True


def test_nonexistent_path_error():
    """Test that nonexistent paths raise clear errors."""
    print("\n" + "="*60)
    print("TEST 3: Nonexistent Path Error Handling")
    print("="*60)
    
    nonexistent = Path("/tmp/nonexistent_specs_dir_12345")
    
    try:
        result = resolve_specs_dir(custom_path=nonexistent)
        print(f"❌ FAIL: Should have raised FileNotFoundError, got {result}")
        return False
    except FileNotFoundError as e:
        error_msg = str(e)
        print(f"✅ PASS: Raised FileNotFoundError as expected")
        print(f"Error message preview: {error_msg[:200]}...")
        
        # Check that error message is helpful
        if "AI_FIRST_SPECS_DIR" in error_msg and "git clone" in error_msg:
            print("✅ PASS: Error message contains helpful instructions")
            return True
        else:
            print("❌ FAIL: Error message lacks helpful instructions")
            return False
    except Exception as e:
        print(f"❌ FAIL: Wrong exception type: {type(e).__name__}: {e}")
        return False


def test_relative_path_resolution():
    """Test resolution via relative path (sibling directory)."""
    print("\n" + "="*60)
    print("TEST 4: Relative Path Resolution (Sibling Directory)")
    print("="*60)
    
    # Calculate where the sibling directory would be
    runtime_root = Path(__file__).parent
    sibling_specs = runtime_root.parent / "ai-first-specs" / "capabilities" / "validated" / "stdlib"
    
    print(f"Expected sibling location: {sibling_specs}")
    
    if sibling_specs.exists():
        try:
            result = resolve_specs_dir()
            print(f"✅ PASS: Resolved to {result}")
            assert result == sibling_specs, f"Expected {sibling_specs}, got {result}"
            return True
        except Exception as e:
            print(f"❌ FAIL: {e}")
            return False
    else:
        print(f"⏭️  SKIP: Sibling directory does not exist (expected in CI)")
        print(f"   This test would pass if ai-first-specs was cloned as a sibling")
        return True  # Not a failure, just not applicable


def test_error_message_quality():
    """Test that error messages are clear and actionable."""
    print("\n" + "="*60)
    print("TEST 5: Error Message Quality")
    print("="*60)
    
    # Ensure no env var is set
    if "AI_FIRST_SPECS_DIR" in os.environ:
        del os.environ["AI_FIRST_SPECS_DIR"]
    
    try:
        result = resolve_specs_dir()
        print(f"⏭️  SKIP: Specs directory found at {result}, cannot test error message")
        return True
    except FileNotFoundError as e:
        error_msg = str(e)
        print("Error message:")
        print("-" * 60)
        print(error_msg)
        print("-" * 60)
        
        # Check for required elements
        required_elements = [
            "AI_FIRST_SPECS_DIR",
            "export",
            "git clone",
            "Option",
            "Searched locations",
        ]
        
        missing = [elem for elem in required_elements if elem not in error_msg]
        
        if not missing:
            print(f"✅ PASS: Error message contains all required elements")
            return True
        else:
            print(f"❌ FAIL: Error message missing: {missing}")
            return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SPECS RESOLVER CROSS-PLATFORM COMPATIBILITY TESTS")
    print("="*60)
    
    tests = [
        ("Environment Variable Resolution", test_env_var_resolution),
        ("Custom Path Resolution", test_custom_path_resolution),
        ("Nonexistent Path Error Handling", test_nonexistent_path_error),
        ("Relative Path Resolution", test_relative_path_resolution),
        ("Error Message Quality", test_error_message_quality),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)
    
    print(f"\nTotal: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n🎉 All tests passed! The fix is working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed_count} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
