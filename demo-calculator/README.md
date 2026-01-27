# Demo Calculator

A simple calculator library with a deliberate bug for demonstrating AI-First Runtime's time-travel debugging capability.

## The Bug

The `divide()` function returns `a * b` instead of `a / b`.

## Running Tests

```bash
pip install -r requirements.txt
pytest test_calculator.py -v
```

Expected result: `test_divide` will fail.

## Demo Purpose

This repository is used in the AI-First Runtime Native Coder demo to show how an AI agent can:
1. Detect the bug
2. Attempt a fix (wrong)
3. Call `sys.undo()` to roll back
4. Apply the correct fix
5. Verify tests pass

This demonstrates "Time-Travel Debugging" - AI agents that can safely experiment and undo mistakes.
