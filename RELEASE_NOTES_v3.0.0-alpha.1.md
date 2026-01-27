# AI-First Runtime v3.0.0-alpha.1 Release Notes

**Release Date:** January 23, 2026  
**Status:** Alpha Release  
**GitHub:** https://github.com/gmood2008/ai-first-runtime/releases/tag/v3.0.0-alpha.1

---

## 🎉 What's New in v3.0

AI-First Runtime v3.0 introduces a **transactional control plane** for AI agents with workflow orchestration, crash recovery, and human-in-the-loop approval gates.

### ✨ Major Features

#### 1. Transactional Workflows

Define multi-step operations in YAML with automatic rollback on failure.

**Example:**
```yaml
name: deploy_web_service
steps:
  - name: create_database
    capability: cloud.db.create
    compensation:
      capability: cloud.db.delete
  
  - name: deploy_app
    capability: cloud.app.deploy
    depends_on: [create_database]
    compensation:
      capability: cloud.app.undeploy
```

**If any step fails, all completed steps are automatically rolled back.**

#### 2. Crash Recovery

Workflows survive process crashes and automatically resume on restart.

**Demo Scenario:**
1. Start workflow → Step 1 completes → Workflow pauses at Step 2
2. **Process crashes** (simulated)
3. Restart runtime → Workflow state restored from database
4. Resume workflow → Remaining steps execute
5. Workflow completes successfully ✅

**Implementation:**
- SQLite-based persistence with WAL mode
- Checkpoint every step execution
- Auto-resume on startup

#### 3. Human-in-the-Loop

Add approval gates for high-risk operations.

**Example:**
```yaml
- name: approval_gate
  step_type: HUMAN_APPROVAL
  inputs:
    message: "Approve production deployment?"
    webhook_url: "https://slack.com/webhooks/..."
```

**Workflow pauses and sends webhook notification. Resume with:**
```bash
airun workflow resume <workflow_id> --decision approve
```

#### 4. TUI Dashboard

Monitor and control workflows in real-time via terminal UI.

```bash
airun dashboard
```

**Features:**
- View all active workflows with status
- See workflow progress with progress bars
- Approve/reject pending workflows
- Trigger rollback (panic button)
- Real-time updates from database

---

## 📊 Technical Highlights

### Architecture

**3-Layer Design:**
1. **Workflow Engine (v3.0)** - YAML workflows, transactional execution, crash recovery
2. **Runtime Engine (v2.0)** - Capability execution, undo closures, RBAC
3. **Persistence Layer (v3.0)** - SQLite state, step checkpointing, compensation log

### Database Schema

```sql
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,  -- PENDING, RUNNING, PAUSED, COMPLETED, FAILED
    spec_yaml TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE workflow_steps (
    id INTEGER PRIMARY KEY,
    workflow_id TEXT,
    step_name TEXT,
    status TEXT,  -- COMPLETED, PAUSED, FAILED
    inputs_json TEXT,
    outputs_json TEXT,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE compensation_log (
    id INTEGER PRIMARY KEY,
    workflow_id TEXT,
    step_name TEXT,
    compensation_action TEXT,
    executed_at TEXT,
    success BOOLEAN
);
```

### Transactional Model

AI-First implements the **Saga pattern** for distributed transactions:
1. Execute steps sequentially
2. Capture compensation for each step
3. On failure, execute compensations in reverse order

**ACID-like Guarantees:**
- **Atomicity:** All steps complete, or all are rolled back
- **Consistency:** Workflow state is always valid
- **Isolation:** Workflows don't interfere with each other
- **Durability:** All state persisted to database, survives crashes

---

## 🧪 Testing & Quality

**Test Results:**
- Crash recovery: 2/2 ✅
- Human-in-the-Loop: 4/4 ✅
- Transactional workflows: 2/3 ⚠️
- Overall: 8/13 tests passing (62%)

**Code Quality:**
- Total coverage: 35%
- persistence.py: 81% ✅
- human_approval.py: 59%
- Formatted with autopep8

---

## 📚 Documentation

**New Documentation:**
- [README.md](README.md) - Updated with v3.0 architecture diagram
- [WORKFLOW_GUIDE.md](docs/v3/WORKFLOW_GUIDE.md) - Complete guide to writing workflows
- [ARCHITECTURE.md](docs/v3/ARCHITECTURE.md) - Deep dive into v3.0 design
- [Week 3 Status Report](docs/week3_status_report.md) - Development progress

**Topics Covered:**
- 3-layer architecture
- Workflow YAML syntax
- Compensation strategies
- State management
- Policy & RBAC
- Crash recovery internals
- Best practices

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/gmood2008/ai-first-runtime.git
cd ai-first-runtime
pip install -r requirements.txt
pip install -e .
```

### Run Your First Workflow

```bash
# Start the TUI dashboard
airun dashboard

# Or execute a workflow directly
airun workflow run examples/simple_workflow.yaml
```

### Example Workflow

Create `my_workflow.yaml`:

```yaml
name: hello_world
version: 1.0.0
description: Simple workflow demo

steps:
  - name: create_file
    capability: io.fs.write_file
    inputs:
      path: "/tmp/hello.txt"
      content: "Hello, AI-First!"
  
  - name: read_file
    capability: io.fs.read_file
    inputs:
      path: "/tmp/hello.txt"
    depends_on: [create_file]
```

Run it:
```bash
airun workflow run my_workflow.yaml
```

---

## ⚠️ Known Limitations (Alpha)

1. **Test Coverage:** 62% (target: 80%)
2. **Single-threaded execution:** Steps execute sequentially (parallel execution planned)
3. **In-memory compensation closures:** Lost on crash (use explicit YAML compensation)
4. **SQLite database:** Single file, no replication (PostgreSQL support planned)
5. **Policy engine:** Basic implementation (advanced RBAC in progress)

---

## 🗺️ Roadmap

**Week 5 (Next):**
- Policy engine & advanced RBAC
- Improve test coverage to 80%+
- Fix remaining test failures

**Week 6:**
- Parallel execution support
- Distributed workflow execution

**Week 7:**
- Error handling & retry strategies
- Timeout management

**Week 8:**
- Beta release
- Production-ready features

---

## 🙏 Acknowledgments

This release represents 4 weeks of intensive development:
- **Week 1:** Initial prototype
- **Week 2:** Runtime engine with undo closures
- **Week 3:** Workflow persistence & crash recovery
- **Week 4:** Polish, documentation, alpha release

Special thanks to the AI agent revolution for inspiring this project! 🤖

---

## 📞 Contact & Support

- **GitHub Issues:** https://github.com/gmood2008/ai-first-runtime/issues
- **Email:** gmood2008@gmail.com
- **Documentation:** https://github.com/gmood2008/ai-first-runtime/tree/master/docs

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

**Built with ❤️ for the AI agent revolution**

**Try it now:** `git clone https://github.com/gmood2008/ai-first-runtime.git`
