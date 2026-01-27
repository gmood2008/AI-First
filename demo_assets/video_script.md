# AI-First Runtime Demo Video Script

**Title:** AI-First Runtime: Time-Travel Debugging for AI Agents
**Duration:** ~3 minutes
**Target Audience:** Developers, CTOs, AI enthusiasts
**Style:** Fast-paced, technical, value-driven

---

## Scene 1: The Problem (0:00 - 0:25)

**Visual:**
- Screen recording of a generic AI agent (like LangChain) trying to fix a bug
- The agent writes code, runs a test, and the test fails
- The agent is stuck in a loop, repeatedly trying the same bad fix
- Fast-forward effect to show wasted time

**Narration (AI Voice - Confident, Clear):**
> "AI agents are powerful, but they can be reckless. When they make a mistake, they often get stuck, leaving you with a broken system and a mess to clean up. This is the reality of most agentic frameworks today."

**On-screen Text:**
- "Traditional AI agents are unreliable."
- "They can't undo their mistakes."
- "Production use is risky."

---

## Scene 2: The Solution - AI-First Runtime (0:25 - 0:50)

**Visual:**
- Transition to the AI-First Runtime logo
- Show the core value proposition on screen
- Split screen: Left side shows the old way (stuck agent), right side shows AI-First Runtime logo

**Narration:**
> "But what if agents could learn from their mistakes? What if they could turn back time? Introducing AI-First Runtime - the first agentic framework with built-in time-travel debugging."

**On-screen Text:**
- **AI-First Runtime**
- **Time-Travel Debugging for the AI Era**
- ✅ Safe Experimentation
- ✅ Automatic Rollback
- ✅ Auditable & Compliant

---

## Scene 3: Hero Scenario - The Undo Demo (0:50 - 1:50)

**Visual:**
- Clean terminal view
- Show the `buggy_api.py` file
- Run the AI agent to fix the bug
- Show the agent's thought process (writing the fix)
- Show the test failing
- Show the agent calling `sys.undo()`
- Show the file reverting to its original state
- Show the agent trying a new, correct fix
- Show the test passing

**Narration:**
> "Let's see it in action. We have a simple API with a JSON formatting bug. We'll ask our AI agent to fix it.

> The agent identifies the problem and writes a fix... but the fix is wrong. The test fails.

> Now, the magic. Instead of getting stuck, the agent calls `sys.undo()`. Instantly, the file is restored to its original state. The undo stack captures every change, allowing for safe, atomic rollbacks.

> With a clean slate, the agent tries a new approach. This time, the fix is correct. The test passes.

> This is the power of AI-First Runtime: safe, self-correcting agents that you can trust in production."

**Commands to Execute:**

1. `cat buggy_api.py`
2. `python -m ai_first_runtime.agent --task "Fix the JSON bug in buggy_api.py"`
3. (Agent runs, test fails)
4. (Agent calls `sys.undo()`)
5. `git diff buggy_api.py` (shows no changes)
6. (Agent runs again, test passes)

---

## Scene 4: Enterprise Compliance (1:50 - 2:30)

**Visual:**
- Transition to a clean, professional UI
- Show the `audit.db` file
- Run the `airun audit export` command
- Open the generated `audit_report.html`
- Scroll through the report, highlighting key sections

**Narration:**
> "But safety is more than just undo. For enterprises, compliance is critical. Every action in AI-First Runtime is logged to a tamper-resistant audit database.

> With a single command, you can generate a professional HTML compliance report, ready for your CTO or security team.

> We automatically sanitize sensitive data like API keys and passwords, ensuring your logs are safe to store and share."

**Commands to Execute:**

1. `ls -l audit.db`
2. `airun audit export --output audit_report.html`
3. `open audit_report.html`

**On-screen Highlights:**
- Operation ID
- Timestamp
- Capability ID
- Sanitized Parameters (`token: "[REDACTED]"`)
- Undo Status

---

## Scene 5: Call to Action (2:30 - 3:00)

**Visual:**
- Transition to the GitHub repository page
- Show the README, stars, and files
- End with the AI-First Runtime logo and URL

**Narration:**
> "AI-First Runtime is open source and ready for you to build on. Stop cleaning up after your agents and start building reliable, production-ready AI systems today.

> Star us on GitHub, join the community, and help us build the future of safe AI."

**On-screen Text:**
- **github.com/gmood2008/ai-first-runtime**
- ⭐ Star us on GitHub
- 💬 Join the discussion
- 🚀 Build safe AI

---

## Supademo Execution Plan

This script can be adapted for Supademo by breaking it into interactive steps:

1. **Intro:** A non-interactive slide explaining the problem.
2. **Step 1: The Bug:** Show the `buggy_api.py` code.
3. **Step 2: The Failed Fix:** Show the agent's first attempt and the failed test.
4. **Step 3: The Undo:** A clickable hotspot on the `sys.undo()` command.
5. **Step 4: The Correct Fix:** Show the second attempt and the successful test.
6. **Step 5: The Audit Report:** A clickable hotspot on the `airun audit export` command.
7. **Step 6: The Report:** Show the generated HTML report.
8. **Outro:** A non-interactive slide with the call to action.

**AI Voiceover:** Use Supademo's built-in AI voiceover feature to read the narration for each step.
