# Installation Guide

## Quick Start

### Option 1: Clone from GitHub (Recommended)

```bash
git clone https://github.com/gmood2008/ai-first-runtime.git
cd ai-first-runtime
```

### Option 2: Download Release

Download the latest release from:
https://github.com/gmood2008/ai-first-runtime/releases

---

## Using the CLI Tool

### Method 1: Direct Python Execution

```bash
python3 airun_cli.py audit export -o my_report.html
```

### Method 2: Create Symbolic Link

```bash
# Create a global command
sudo ln -s $(pwd)/airun_cli.py /usr/local/bin/airun

# Now you can use it anywhere
airun audit export -o my_report.html
```

### Method 3: Add to PATH

```bash
# Add to your ~/.bashrc or ~/.zshrc
export PATH="$PATH:/path/to/ai-first-runtime"

# Reload your shell
source ~/.bashrc  # or source ~/.zshrc

# Use the command
airun_cli.py audit export
```

---

## Running the Runtime

### As a Python Module

```python
import sys
sys.path.insert(0, '/path/to/ai-first-runtime/src')

from runtime.mcp.server_v2 import AIFirstServer
from runtime.types import ExecutionContext

# Initialize server
server = AIFirstServer()

# Create execution context
context = ExecutionContext(
    user_id='your_user_id',
    session_id='your_session_id',
    confirmation_callback=lambda h, p, c: True,
    undo_enabled=True
)

# Execute a capability
result = server.engine.execute(
    'io.fs.write_file',
    {'path': '/tmp/test.txt', 'content': 'Hello, World!'},
    context
)

print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### As an MCP Server

See `docs/INTEGRATION_GUIDE.md` for detailed instructions on integrating with:
- Claude Desktop
- Cursor / VS Code
- Python scripts

---

## Dependencies

AI-First Runtime requires:
- **Python 3.11+**
- No external dependencies for core functionality

Optional dependencies for development:
- `pytest` - For running tests
- `pytest-cov` - For code coverage

---

## Verification

### Test the Compliance Engine

```bash
python3 test_compliance_engine.py
```

Expected output:
```
✅ AuditLogger initialized
✅ 5 sample actions logged
✅ Retrieved 5 records
✅ Session summary: 3 success, 1 failure, 1 denied
✅ HTML report generated
✅ Sensitive data redacted
```

### Test the Hero Scenario

```bash
python3 test_hero_scenario.py
```

Expected output:
```
✅ All 7 steps completed successfully
✅ sys.undo worked correctly
✅ File state verified
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'runtime'"

**Solution:** Ensure you're running from the project root directory or have added `src/` to your Python path:

```python
import sys
sys.path.insert(0, '/path/to/ai-first-runtime/src')
```

### "Permission denied" when creating symbolic link

**Solution:** Use `sudo`:

```bash
sudo ln -s $(pwd)/airun_cli.py /usr/local/bin/airun
```

### "Database is locked" error

**Solution:** Ensure no other processes are accessing the audit database:

```bash
# Check for locks
lsof ~/.ai-first/workspace/.ai-first/audit.db

# If needed, kill the process
kill <PID>
```

---

## Next Steps

1. Read the [QUICKSTART.md](QUICKSTART.md) for a 3-minute tutorial
2. Explore the [Integration Guide](docs/INTEGRATION_GUIDE.md) for Claude Desktop, Cursor, and Python recipes
3. Review the [Enterprise Audit Guide](docs/ENTERPRISE_AUDIT.md) for compliance features

---

## Support

- **Issues:** https://github.com/gmood2008/ai-first-runtime/issues
- **Documentation:** https://github.com/gmood2008/ai-first-runtime/tree/master/docs
