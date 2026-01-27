# Native Coder Demo: Design Document

**Purpose:** Demonstrate AI-First Runtime's "Time-Travel Debugging" capability using `sys.undo`

**Target Audience:** Developers, CTOs, AI researchers

**Key Message:** AI agents can safely experiment, make mistakes, and automatically roll back without causing irreversible harm.

---

## Demo Scenario: "Fix a Bug in a Calculator Library"

### The Setup

**Demo Repository:** `demo-calculator`

**Initial State:**
- `calculator.py` contains a working `add()` function
- `calculator.py` contains a **buggy** `divide()` function (returns wrong result)
- Tests for `add()` pass
- Tests for `divide()` fail

---

## The Demo Flow

1. **Run Tests** - Initial failure on divide()
2. **AI Analyzes** - Identifies the bug
3. **AI Attempts Fix #1** - Wrong fix (intentional)
4. **Run Tests** - Still failing
5. **AI Calls sys.undo()** - Rolls back wrong fix
6. **AI Applies Correct Fix** - Right solution
7. **Run Tests** - Success!

---

## The "Wow" Moment

The AI made a mistake (Step 3), but instead of leaving the codebase broken, it **called `sys.undo()`** to roll back. This is **Time-Travel Debugging**.

**Why This Matters:**
- Safety: AI agents can try multiple solutions without risk
- Auditability: Every change is tracked and reversible
- Reliability: No manual cleanup required
- Unique: LangChain and LlamaIndex cannot do this

---

## Marketing Angle

**Headline:** "AI Agents That Can Undo Their Mistakes"

**Tagline:** "Time-Travel Debugging for the AI Era"

This demo will be the centerpiece of our v1.0.0 launch.
