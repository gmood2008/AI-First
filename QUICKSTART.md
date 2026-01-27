# Quickstart: 3 Minutes to Time-Travel Debugging

This guide will get you from zero to using AI-First Runtime's flagship `sys.undo` feature in under 3 minutes.

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/gmood2008/ai-first-runtime.git
cd ai-first-runtime
```

---

## Step 2: Run the Undo Demo Script

We've created a simple script that demonstrates the entire undo flow. It will:
1. Create a file
2. Verify it exists
3. Call `sys.undo()` to delete it
4. Verify it's gone

```bash
python3.11 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from runtime.mcp.server_v2 import AIFirstServer
from runtime.types import ExecutionContext

# Setup
server = AIFirstServer()
context = ExecutionContext(
    user_id='quickstart',
    workspace_root=Path('/tmp/quickstart_workspace'),
    session_id='test',
    undo_enabled=True
)
file_path = '/tmp/quickstart_test.txt'

# 1. Write a file
print('\n[1] Writing file...')
server.engine.execute('io.fs.write_file', {'path': file_path, 'content': 'Hello, AI-First!'}, context)
print(f'✅ File created. Undo stack size: {server.undo_manager.size()}')

# 2. Verify file exists
import os
assert os.path.exists(file_path), 'File was not created!'
print('✅ File verified to exist.')

# 3. Call sys.undo()
print('\n[2] Calling sys.undo()...')
result = server.engine.execute('sys.undo', {}, context)
print(f'✅ Undo successful: {result.outputs["description"]}')
print(f'   Stack size after undo: {result.outputs["stack_size"]}')

# 4. Verify file is gone
assert not os.path.exists(file_path), 'File was not deleted by undo!'
print('✅ File verified to be deleted.')

print('\n🎉 Quickstart complete! You just used time-travel debugging.')
"
```

### Expected Output

```
[1] Writing file...
✅ File created. Undo stack size: 1
✅ File verified to exist.

[2] Calling sys.undo()...
✅ Undo successful: Undone: Wrote 17 bytes to /tmp/quickstart_test.txt
   Stack size after undo: 0
✅ File verified to be deleted.

🎉 Quickstart complete! You just used time-travel debugging.
```

---

## What Just Happened?

1. **`io.fs.write_file`** was called. The handler automatically created an `UndoRecord` containing a closure that knew how to delete the file it just created.
2. This record was pushed to the `UndoManager` stack.
3. **`sys.undo`** was called. It popped the record from the stack and executed the closure, deleting the file.

This is the core of AI-First Runtime's safety model: **every action knows how to undo itself.**

## Next Steps

- Explore the `demo-calculator` repository to see a more advanced bug-fixing scenario.
- Read the `docs/HANDLER_DEVELOPER_GUIDE.md` to learn how to build your own undoable tools.
- Use the `forge import` tool to automatically generate safe capabilities from your own Python code.
