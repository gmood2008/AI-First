# Release Notes: v2.0.1 (Hotfix)

**Release Date:** January 22, 2026  
**Type:** Hotfix  
**Priority:** Critical

---

## 🚨 Critical Bug Fix

### Issue: Hardcoded Linux Path Breaks macOS/Windows Deployment

**Problem:**
- The MCP servers (`server.py` and `server_v2.py`) contained hardcoded Linux paths (`/home/ubuntu/...`)
- This caused immediate crashes on macOS and Windows environments with `FileNotFoundError`
- The bug prevented any non-Linux user from running the AI-First Runtime

**Impact:**
- **Severity:** P0 - Critical
- **Affected Versions:** v2.0.0
- **Platforms:** macOS, Windows, and any Linux system without the hardcoded path

**Traceback Example:**
```
FileNotFoundError: Specs directory not found: /home/ubuntu/ai-first-specs/capabilities/validated/stdlib
```

---

## ✅ What's Fixed

### 1. Dynamic Specs Directory Resolution

**New Module:** `src/runtime/mcp/specs_resolver.py`

Implements a robust, cross-platform resolution strategy for locating the `ai-first-specs` directory:

**Resolution Priority:**
1. **Environment Variable** (Highest Priority)
   - `AI_FIRST_SPECS_DIR` - Explicit path set by user
   - Example: `export AI_FIRST_SPECS_DIR=/path/to/ai-first-specs/capabilities/validated/stdlib`

2. **Relative Path** (Automatic Discovery)
   - Assumes `ai-first-specs` is a sibling directory to `ai-first-runtime`
   - Works out-of-the-box if both repos are cloned side-by-side

3. **Clear Error Message** (Fallback)
   - If neither method works, provides actionable instructions
   - Includes 3 options with exact commands to fix the issue

**Example Error Message:**
```
❌ AI-First specs directory not found!

The ai-first-specs repository is required but could not be located.

Please choose one of the following solutions:

Option 1: Set environment variable (recommended)
  export AI_FIRST_SPECS_DIR=/path/to/ai-first-specs/capabilities/validated/stdlib

Option 2: Clone ai-first-specs as a sibling directory
  cd ..
  git clone https://github.com/gmood2008/ai-first-specs.git

Option 3: Pass specs_dir parameter when creating server
  server = AIFirstMCPServer(specs_dir='/path/to/specs')

Searched locations:
  - Environment variable AI_FIRST_SPECS_DIR: (not set)
  - Sibling directory: /Users/you/projects/ai-first-specs/capabilities/validated/stdlib
```

### 2. Updated MCP Servers

**Modified Files:**
- `src/runtime/mcp/server.py` - FastMCP implementation
- `src/runtime/mcp/server_v2.py` - Official SDK implementation

**Changes:**
- Removed hardcoded path: `Path("/home/ubuntu/ai-first-specs/...")`
- Added import: `from runtime.mcp.specs_resolver import resolve_specs_dir`
- Updated initialization logic to use dynamic resolution

**Before:**
```python
if specs_dir is None:
    specs_dir = Path("/home/ubuntu/ai-first-specs/capabilities/validated/stdlib")
self.specs_dir = Path(specs_dir)
```

**After:**
```python
if specs_dir is None:
    self.specs_dir = resolve_specs_dir()
else:
    self.specs_dir = resolve_specs_dir(custom_path=specs_dir)
```

### 3. Comprehensive Test Suite

**New File:** `test_specs_resolver.py`

Tests all resolution scenarios:
- ✅ Environment variable resolution
- ✅ Custom path resolution
- ✅ Nonexistent path error handling
- ✅ Relative path resolution (sibling directory)
- ✅ Error message quality and helpfulness

**Test Results:**
```
Total: 5/5 tests passed
🎉 All tests passed! The fix is working correctly.
```

---

## 🔧 How to Use

### Option 1: Environment Variable (Recommended)

Set the environment variable before running the MCP server:

```bash
# macOS/Linux
export AI_FIRST_SPECS_DIR=/path/to/ai-first-specs/capabilities/validated/stdlib

# Windows (PowerShell)
$env:AI_FIRST_SPECS_DIR = "C:\path\to\ai-first-specs\capabilities\validated\stdlib"

# Windows (Command Prompt)
set AI_FIRST_SPECS_DIR=C:\path\to\ai-first-specs\capabilities\validated\stdlib
```

Then run your MCP server as usual:
```bash
python -m runtime.mcp.server_v2
```

### Option 2: Sibling Directory (Automatic)

Clone both repositories side-by-side:

```bash
cd ~/projects
git clone https://github.com/gmood2008/ai-first-runtime.git
git clone https://github.com/gmood2008/ai-first-specs.git

cd ai-first-runtime
# No environment variable needed - it will auto-discover ai-first-specs
python -m runtime.mcp.server_v2
```

### Option 3: Custom Path in Code

Pass the `specs_dir` parameter when creating the server:

```python
from pathlib import Path
from runtime.mcp.server_v2 import AIFirstMCPServer

server = AIFirstMCPServer(
    name="my-ai-first-server",
    specs_dir=Path("/custom/path/to/specs")
)
```

---

## 📦 Upgrade Instructions

### For Existing Users

If you're already using v2.0.0, upgrade immediately:

```bash
cd ai-first-runtime
git pull origin master
git checkout v2.0.1

# If you installed via pip (editable mode)
pip install -e .
```

### For New Users

Clone and set up:

```bash
# Clone both repositories
git clone https://github.com/gmood2008/ai-first-runtime.git
git clone https://github.com/gmood2008/ai-first-specs.git

cd ai-first-runtime
pip install -e .

# No additional configuration needed - sibling directory will be auto-discovered
```

---

## 🧪 Verification

To verify the fix is working:

```bash
cd ai-first-runtime
python3.11 test_specs_resolver.py
```

Expected output:
```
🎉 All tests passed! The fix is working correctly.
```

---

## 📝 Migration Notes

### Breaking Changes

**None.** This is a backward-compatible hotfix.

### Deprecations

**None.**

### New Features

**None.** This release only fixes the critical portability bug.

---

## 🐛 Known Issues

**None** related to this hotfix.

---

## 🙏 Acknowledgments

**Reported by:** User deployment testing on macOS  
**Fixed by:** Manus AI  
**Tested on:** Linux (Ubuntu 22.04), macOS (simulated), Windows (simulated)

---

## 📊 Files Changed

```
src/runtime/mcp/specs_resolver.py      (NEW)  - 107 lines
src/runtime/mcp/server.py              (MOD)  - 4 lines changed
src/runtime/mcp/server_v2.py           (MOD)  - 4 lines changed
test_specs_resolver.py                 (NEW)  - 215 lines
RELEASE_v2.0.1.md                      (NEW)  - This file
```

**Total:** 2 files modified, 3 files added

---

## 🔗 Links

- **GitHub Release:** https://github.com/gmood2008/ai-first-runtime/releases/tag/v2.0.1
- **Issue Tracker:** https://github.com/gmood2008/ai-first-runtime/issues
- **Documentation:** https://github.com/gmood2008/ai-first-runtime#readme

---

## 📅 Next Release

**v2.1.0** (Planned)
- Feature: Enhanced MCP tool discovery
- Feature: Improved audit report formatting
- Enhancement: Better error messages for common issues

---

**For questions or issues, please contact:** daniel.hhd@gmail.com
