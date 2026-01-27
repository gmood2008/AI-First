# AI-First Runtime

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 62%](https://img.shields.io/badge/tests-62%25-yellow.svg)]()
[![Version: 3.0.0-alpha.1](https://img.shields.io/badge/version-3.0.0--alpha.1-orange.svg)]()

**The Transactional Control Plane for AI Agents**

AI-First Runtime is the execution and governance layer for multi-agent systems. We don't replace your LLM planner—we control how agents execute, ensuring every action is transactional, auditable, and reversible.

---

## 🎯 v3.0 Alpha: Workflow Orchestration + Crash Recovery

**New in v3.0:**
- ✅ **Transactional Workflows** - YAML-based workflow definitions with automatic rollback
- ✅ **Crash Recovery** - Workflows survive process crashes and auto-resume
- ✅ **Human-in-the-Loop** - Webhook-based approval gates for high-risk operations
- ✅ **TUI Dashboard** - Real-time monitoring and control via terminal UI

**Status:** Alpha release ready for early adopters and testing

📜 **[Read the Constitution: 13 Non-Negotiable Principles](docs/v3/PRINCIPLES.md)**

---

## Architecture: 3-Layer Design

```
┌──────────────────────────────────────────────────────────────┐
│                    Planning Layer                             │
│            (LLM / AutoGen / CrewAI / Cursor)                  │
│                 Decides WHAT to do                            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│              AI-First Runtime v3.0 (Control Plane)            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Workflow Engine (v3.0)                                │  │
│  │  • YAML workflow specs                                 │  │
│  │  • Transactional execution                             │  │
│  │  • Automatic rollback on failure                       │  │
│  │  • Human-in-the-Loop approval gates                    │  │
│  │  • Crash recovery & auto-resume                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                            ↓                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Runtime Engine (v2.0)                                 │  │
│  │  • Capability registry & execution                     │  │
│  │  • Atomic undo closures                                │  │
│  │  • RBAC & policy enforcement                           │  │
│  │  • Audit logging                                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                            ↓                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Persistence Layer (v3.0)                              │  │
│  │  • SQLite workflow state                               │  │
│  │  • Step checkpointing                                  │  │
│  │  • Compensation log                                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                    Execution Layer                            │
│              (OS / APIs / Cloud / Filesystem)                 │
│                  Performs the work                            │
└──────────────────────────────────────────────────────────────┘
```

**Key Insight:** AI-First is NOT a planner. We're the **control plane** that sits between planning and execution, ensuring safety, auditability, and reversibility.

---

## Why AI-First?

**The Problem:** Enterprises want to deploy AI agents, but they can't answer three critical questions:
1. **"Who controls these agents?"** (Governance)
2. **"What happens when they fail?"** (Rollback)
3. **"How do we prove compliance?"** (Audit)

Existing frameworks (LangChain, LlamaIndex, AutoGen) focus on **planning** but ignore **control**. They're great for prototyping, but they leave enterprises exposed.

**AI-First Runtime is different.** We're the **control plane** that sits between your LLM planner and the real world. We don't replace your agents—we make them **safe, auditable, and reversible**.

### Our Competitive Moat

**Transactional Workflows for AI Agents**
- Every workflow is a distributed transaction with ACID-like guarantees
- Automatic rollback on failure (no manual cleanup)
- Built-in governance (RBAC for agents, risk classification)
- Forensic audit trail (SOC2, HIPAA, GDPR compliance)
- **Crash recovery** - Workflows survive process crashes

---

## Key Features

### 1. Transactional Workflows (v3.0)

Define multi-step workflows in YAML with automatic rollback on failure.

**Example:** Deploy a web service with automatic cleanup on failure

```yaml
name: deploy_web_service
version: 1.0.0
description: Deploy web service with database and load balancer

steps:
  - name: create_database
    capability: cloud.db.create
    inputs:
      name: "prod-db"
      size: "medium"
    compensation:
      capability: cloud.db.delete
      inputs:
        name: "{{database_name}}"
  
  - name: deploy_app
    capability: cloud.app.deploy
    inputs:
      image: "myapp:v1.0"
      database: "{{database_name}}"
    depends_on: [create_database]
    compensation:
      capability: cloud.app.undeploy
      inputs:
        app_id: "{{app_id}}"
  
  - name: configure_lb
    capability: cloud.lb.configure
    inputs:
      target: "{{app_id}}"
    depends_on: [deploy_app]
    compensation:
      capability: cloud.lb.remove
      inputs:
        lb_id: "{{lb_id}}"
```

**If any step fails, all completed steps are automatically rolled back in reverse order.**

### 2. Crash Recovery (v3.0)

Workflows survive process crashes and automatically resume.

**Demo Scenario:**
1. Start workflow (Step 1: Write File A, Step 2: Human Approval)
2. Step 1 completes, workflow pauses at Step 2
3. **Process crashes** (simulated)
4. Restart runtime → Workflow state restored from database
5. File A still exists ✅
6. Resume workflow → Step 3 executes
7. Workflow completes successfully ✅

**Implementation:**
- SQLite-based persistence with WAL mode
- Checkpoint every step execution
- Store workflow spec, state, and compensation stack
- Auto-resume on startup

### 3. Human-in-the-Loop (v3.0)

Add approval gates for high-risk operations.

**Example:** Require approval before deleting production data

```yaml
steps:
  - name: backup_data
    capability: io.fs.copy
    inputs:
      source: "/prod/data"
      dest: "/backup/data"
  
  - name: approval_gate
    step_type: HUMAN_APPROVAL
    inputs:
      message: "Approve deletion of production data?"
      webhook_url: "https://slack.com/webhooks/..."
    depends_on: [backup_data]
  
  - name: delete_data
    capability: io.fs.delete
    inputs:
      path: "/prod/data"
    depends_on: [approval_gate]
```

**Workflow pauses at approval gate and sends webhook notification. Resume with:**

```bash
airun workflow resume <workflow_id> --decision approve
```

### 4. TUI Dashboard (v3.0)

Monitor and control workflows in real-time.

```bash
airun dashboard
```

**Features:**
- View all active workflows with status
- See workflow progress with progress bars
- Approve/reject pending workflows
- Trigger rollback (panic button)
- Real-time updates from database

**Keyboard shortcuts:**
- `q` - Quit
- `r` - Refresh
- `d` - View workflow details

### 5. Time-Travel Debugging (`sys.undo`)

Our flagship feature from v2.0. Every write operation automatically creates an undo record.

**Demo:**
1. AI writes bad code → Test fails
2. AI calls `sys.undo()` → Code is restored
3. AI writes good code → Test passes

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/gmood2008/ai-first-runtime.git
cd ai-first-runtime

# Install dependencies
pip install -r requirements.txt

# Install CLI
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

## Documentation

- **[Workflow Guide](docs/v3/WORKFLOW_GUIDE.md)** - How to write YAML workflows
- **[Architecture Guide](docs/v3/ARCHITECTURE.md)** - Deep dive into v3.0 design
- **[API Reference](docs/v3/API_REFERENCE.md)** - Python API documentation
- **[Week 3 Status Report](docs/week3_status_report.md)** - Development progress

---

## Project Status

**v3.0 Alpha (Week 4):**
- ✅ Workflow persistence with crash recovery
- ✅ Human-in-the-Loop approval system
- ✅ TUI dashboard for monitoring
- ✅ Transactional workflows with rollback
- ⚠️ Test coverage: 62% (target: 80%)
- ⚠️ Policy engine: In progress
- ⚠️ Parallel execution: Planned

**Roadmap:**
- **Week 5:** Policy engine & RBAC
- **Week 6:** Parallel execution
- **Week 7:** Error handling & retry
- **Week 8:** Beta release

---

## Testing

```bash
# Run all tests
pytest tests/v3/

# Run specific test suites
pytest tests/v3/test_crash_recovery.py
pytest tests/v3/test_human_approval.py

# Run with coverage
pytest tests/v3/ --cov=src/runtime/workflow
```

**Current Test Status:**
- Crash recovery: 2/2 ✅
- Human-in-the-Loop: 4/4 ✅
- Transactional workflows: 2/3 ⚠️
- Overall: 8/13 (62%)

---

## Contributing

We're in active development and welcome contributions!

**Areas needing help:**
- Test coverage improvements
- Documentation
- Example workflows
- Bug fixes

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Contact

- **GitHub:** https://github.com/gmood2008/ai-first-runtime
- **Issues:** https://github.com/gmood2008/ai-first-runtime/issues
- **Email:** gmood2008@gmail.com

---

**Built with ❤️ for the AI agent revolution**
