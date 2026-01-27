# AI-First Runtime v3.0 - Architecture Guide

**Deep dive into the transactional control plane design**

---

## Table of Contents

1. [Overview](#overview)
2. [3-Layer Architecture](#3-layer-architecture)
3. [Workflow Engine](#workflow-engine)
4. [Persistence Layer](#persistence-layer)
5. [Crash Recovery](#crash-recovery)
6. [Human-in-the-Loop](#human-in-the-loop)
7. [State Machine](#state-machine)
8. [Transactional Model](#transactional-model)
9. [Performance & Scalability](#performance--scalability)
10. [Security & Compliance](#security--compliance)

---

## Overview

AI-First Runtime v3.0 is a **transactional control plane** for AI agents. It sits between the planning layer (LLM/AutoGen/CrewAI) and the execution layer (OS/APIs/Cloud), providing:

- **Transactional Workflows** - All-or-nothing execution with automatic rollback
- **Crash Recovery** - Workflows survive process crashes
- **Human-in-the-Loop** - Approval gates for high-risk operations
- **Governance** - RBAC, policy enforcement, audit logging

**Design Principles:**
1. **Safety First** - Every operation is reversible
2. **Resilience** - Survive crashes and network failures
3. **Auditability** - Every action is logged
4. **Simplicity** - YAML workflows, not code

---

## 3-Layer Architecture

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

### Layer 1: Workflow Engine (v3.0)

**Responsibilities:**
- Parse YAML workflow specs
- Execute steps in dependency order
- Manage workflow state and compensation stack
- Trigger rollback on failure
- Handle human approval gates
- Checkpoint progress to database

**Key Components:**
- `WorkflowEngine` - Main orchestrator
- `WorkflowExecutionContext` - Per-workflow state
- `WorkflowRecovery` - Crash recovery logic
- `HumanApprovalManager` - Approval gate handler

### Layer 2: Runtime Engine (v2.0)

**Responsibilities:**
- Execute capabilities (filesystem, network, cloud, etc.)
- Capture undo closures for each operation
- Enforce RBAC and policies
- Log all operations to audit trail

**Key Components:**
- `RuntimeEngine` - Capability executor
- `CapabilityRegistry` - Capability catalog
- `UndoManager` - Undo closure storage
- `AuditLogger` - Forensic logging

### Layer 3: Persistence Layer (v3.0)

**Responsibilities:**
- Store workflow state in SQLite
- Checkpoint each step execution
- Log compensation operations
- Enable crash recovery

**Key Components:**
- `WorkflowPersistence` - Database abstraction
- SQLite with WAL mode
- 3 tables: `workflows`, `workflow_steps`, `compensation_log`

---

## Workflow Engine

### Core Classes

#### WorkflowEngine

Main orchestrator for workflow execution.

```python
class WorkflowEngine:
    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        execution_context: ExecutionContext,
        approval_manager: HumanApprovalManager,
        persistence: WorkflowPersistence
    ):
        self.runtime_engine = runtime_engine
        self.execution_context = execution_context
        self.approval_manager = approval_manager
        self.persistence = persistence
        self.recovery = WorkflowRecovery(self, persistence)
        self.workflows: Dict[str, WorkflowExecutionContext] = {}
    
    def submit_workflow(self, spec: WorkflowSpec) -> str:
        """Submit a workflow for execution"""
        workflow_id = str(uuid.uuid4())
        spec.metadata.workflow_id = workflow_id
        
        # Persist to database
        self.persistence.create_workflow(workflow_id, spec)
        
        # Create execution context
        context = WorkflowExecutionContext(spec)
        self.workflows[workflow_id] = context
        
        return workflow_id
    
    def start_workflow(self, workflow_id: str):
        """Start executing a workflow"""
        context = self.workflows[workflow_id]
        self._execute_workflow(context)
    
    def resume_workflow(
        self,
        workflow_id: str,
        decision: str,
        approver: Optional[str] = None
    ):
        """Resume a PAUSED workflow after human approval"""
        context = self.workflows[workflow_id]
        
        if decision == "approve":
            self._execute_workflow(context)
        elif decision == "reject":
            self._handle_workflow_failure(context, "Rejected by approver")
```

#### WorkflowExecutionContext

Per-workflow state container.

```python
@dataclass
class WorkflowExecutionContext:
    spec: WorkflowSpec
    state: Dict[str, Any] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)
    compensation_stack: List[Tuple[str, Callable]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def mark_step_completed(self, step_name: str, outputs: Dict[str, Any]):
        """Mark a step as completed and merge outputs into state"""
        self.completed_steps.append(step_name)
        for key, value in outputs.items():
            self.state[f"{step_name}.{key}"] = value
    
    def mark_step_failed(self, step_name: str, error: str):
        """Mark a step as failed"""
        self.spec.metadata.status = WorkflowStatus.FAILED
        self.spec.metadata.error_message = error
```

### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. submit_workflow(spec)                                     │
│    • Generate workflow_id                                    │
│    • Persist spec to database                                │
│    • Create WorkflowExecutionContext                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. start_workflow(workflow_id)                               │
│    • Mark status = RUNNING                                   │
│    • Call _execute_workflow(context)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. _execute_workflow(context)                                │
│    • Filter remaining_steps (exclude completed)              │
│    • For each step:                                          │
│      - Check dependencies                                    │
│      - Execute step                                          │
│      - Checkpoint to database                                │
│      - Capture compensation closure                          │
│    • If all steps complete: mark COMPLETED                   │
│    • If any step fails: trigger rollback                     │
│    • If HUMAN_APPROVAL: mark PAUSED                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. _execute_step(context, step)                              │
│    • If step_type == HUMAN_APPROVAL:                         │
│      - Send webhook notification                             │
│      - Mark workflow PAUSED                                  │
│      - Return PAUSED                                         │
│    • If step_type == ACTION:                                 │
│      - Resolve inputs with template variables                │
│      - Call runtime_engine.execute()                         │
│      - Mark step completed                                   │
│      - Checkpoint to database                                │
│      - Create compensation closure                           │
│      - Return SUCCESS or FAILURE                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Rollback (if failure)                                     │
│    • Pop compensation_stack in reverse order                 │
│    • Execute each undo closure                               │
│    • Log compensation operations                             │
│    • Mark workflow ROLLED_BACK                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Persistence Layer

### Database Schema

```sql
-- Workflow metadata and status
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,                 -- UUID
    name TEXT NOT NULL,                  -- Workflow name
    version TEXT NOT NULL,               -- Semantic version
    owner TEXT NOT NULL,                 -- User ID
    status TEXT NOT NULL,                -- PENDING, RUNNING, PAUSED, COMPLETED, FAILED, ROLLED_BACK
    spec_yaml TEXT NOT NULL,             -- Full workflow spec in YAML
    created_at TEXT NOT NULL,            -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,            -- ISO 8601 timestamp
    completed_at TEXT,                   -- ISO 8601 timestamp (nullable)
    error_message TEXT                   -- Error message if failed (nullable)
);

-- Step execution history
CREATE TABLE workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,           -- Foreign key to workflows.id
    step_name TEXT NOT NULL,             -- Step identifier
    status TEXT NOT NULL,                -- COMPLETED, PAUSED, FAILED
    inputs_json TEXT,                    -- Step inputs as JSON
    outputs_json TEXT,                   -- Step outputs as JSON
    started_at TEXT NOT NULL,            -- ISO 8601 timestamp
    completed_at TEXT,                   -- ISO 8601 timestamp (nullable)
    error_message TEXT,                  -- Error message if failed (nullable)
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Compensation/rollback log
CREATE TABLE compensation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,           -- Foreign key to workflows.id
    step_name TEXT NOT NULL,             -- Step being compensated
    compensation_action TEXT NOT NULL,   -- Compensation capability
    inputs_json TEXT,                    -- Compensation inputs as JSON
    executed_at TEXT NOT NULL,           -- ISO 8601 timestamp
    success BOOLEAN NOT NULL,            -- Whether compensation succeeded
    error_message TEXT,                  -- Error message if failed (nullable)
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Indexes for performance
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflow_steps_workflow_id ON workflow_steps(workflow_id);
CREATE INDEX idx_compensation_log_workflow_id ON compensation_log(workflow_id);
```

### WAL Mode

SQLite is configured with Write-Ahead Logging (WAL) for better concurrency and crash safety:

```python
conn = sqlite3.connect("audit.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
```

**Benefits:**
- Readers don't block writers
- Writers don't block readers
- Better crash recovery
- Faster writes

### Checkpointing Strategy

**When to checkpoint:**
1. After each step completes successfully
2. When workflow status changes (RUNNING → PAUSED)
3. When compensation is executed

**What to checkpoint:**
- Workflow status
- Step name, inputs, outputs
- Execution timestamps
- Error messages (if failed)

**Code:**

```python
def checkpoint_step(
    self,
    workflow_id: str,
    step_name: str,
    status: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any]
):
    """Checkpoint a step execution to database"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO workflow_steps (
            workflow_id, step_name, status,
            inputs_json, outputs_json,
            started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        workflow_id,
        step_name,
        status,
        json.dumps(inputs),
        json.dumps(outputs),
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat() if status == "COMPLETED" else None
    ))
    
    conn.commit()
    conn.close()
```

---

## Crash Recovery

### Problem Statement

**Scenario:** Workflow is executing, process crashes (OOM, SIGKILL, power loss). What happens?

**Without crash recovery:**
- Workflow state is lost
- Partial changes remain on disk
- No way to resume or rollback
- Manual cleanup required

**With crash recovery:**
- Workflow state persisted to database
- On restart, workflows auto-resume
- Completed steps are skipped
- Remaining steps execute normally

### Recovery Strategy

#### 1. On Startup: Auto-Resume

```python
class WorkflowEngine:
    def __init__(self, ...):
        # ... initialization ...
        
        # Auto-resume workflows on startup
        self.recovery.auto_resume_workflows()
```

#### 2. Load Workflow State

```python
def auto_resume_workflows(self):
    """Resume all RUNNING and PAUSED workflows on startup"""
    # Query database for incomplete workflows
    workflows = self.persistence.get_workflows_by_status([
        WorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED
    ])
    
    for workflow_record in workflows:
        workflow_id = workflow_record["id"]
        spec_yaml = workflow_record["spec_yaml"]
        
        # Reconstruct WorkflowSpec from YAML
        spec = WorkflowSpec(**yaml.safe_load(spec_yaml))
        
        # Restore execution context
        context = WorkflowExecutionContext(spec)
        context.spec.metadata.status = WorkflowStatus(workflow_record["status"])
        
        # Restore completed steps from database
        steps = self.persistence.get_workflow_steps(workflow_id)
        for step in steps:
            if step["status"] in ("COMPLETED", "PAUSED"):
                context.completed_steps.append(step["step_name"])
                
                # Restore outputs to state
                if step["outputs_json"]:
                    outputs = json.loads(step["outputs_json"])
                    context.state.update(outputs)
        
        # Register context
        self.engine.workflows[workflow_id] = context
        
        # Resume execution
        if workflow_record["status"] == "RUNNING":
            self.engine._execute_workflow(context)
        elif workflow_record["status"] == "PAUSED":
            # Wait for human approval
            pass
```

#### 3. Skip Completed Steps

```python
def _execute_workflow(self, context: WorkflowExecutionContext):
    """Execute workflow, skipping completed steps"""
    spec = context.spec
    
    # Filter out completed steps
    remaining_steps = [
        step for step in spec.steps
        if step.name not in context.completed_steps
    ]
    
    for step in remaining_steps:
        result = self._execute_step(context, step)
        
        if result == StepExecutionResult.FAILURE:
            self._handle_workflow_failure(context, ...)
            return
        elif result == StepExecutionResult.PAUSED:
            return  # Wait for approval
    
    self._complete_workflow(context)
```

### Known Limitations

**Compensation closures are not persisted:**

In v3.0, undo closures are stored in memory (`compensation_stack`). If the process crashes, these closures are lost.

**Workaround:**
- Use explicit `compensation` in YAML specs
- Compensation is re-created from spec on resume

**Future improvement:**
- Serialize closures using `dill` or `cloudpickle`
- Store serialized closures in database
- Deserialize on resume

---

## Human-in-the-Loop

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ WorkflowEngine                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ _execute_step(context, step)                           │  │
│  │  if step.step_type == HUMAN_APPROVAL:                  │  │
│  │    approval_manager.request_approval(...)              │  │
│  │    return PAUSED                                       │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ HumanApprovalManager                                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ request_approval(workflow_id, message, webhook_url)    │  │
│  │  • Store pending approval in memory                    │  │
│  │  • Send webhook notification                           │  │
│  │  • Log to audit trail                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ record_decision(workflow_id, decision, approver)       │  │
│  │  • Update pending approval                             │  │
│  │  • Log decision to audit trail                         │  │
│  │  • Return True if approved, False if rejected          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ Webhook Endpoint (Slack / Teams / Custom)                    │
│  • Receives approval request                                 │
│  • Displays message to human                                 │
│  • Provides approve/reject buttons                           │
│  • Calls airun workflow resume <id> --decision <approve|reject>│
└──────────────────────────────────────────────────────────────┘
```

### Webhook Payload

```json
{
  "workflow_id": "abc123",
  "workflow_name": "deploy_to_prod",
  "step_name": "approval_gate",
  "message": "Approve production deployment?",
  "requested_at": "2026-01-23T10:00:00Z",
  "context": {
    "version": "v1.0",
    "environment": "production"
  }
}
```

### Approval State Machine

```
PENDING ──approve──> APPROVED ──> Workflow continues
   │
   └──reject──> REJECTED ──> Workflow rolls back
   │
   └──timeout──> TIMEOUT ──> Workflow fails
```

---

## State Machine

### Workflow Status

```
PENDING ──start──> RUNNING ──all steps complete──> COMPLETED
   │                  │
   │                  ├──step fails──> FAILED ──rollback──> ROLLED_BACK
   │                  │
   │                  └──human approval needed──> PAUSED ──approve──> RUNNING
                                                     │
                                                     └──reject──> FAILED
```

**States:**
- `PENDING` - Workflow submitted but not started
- `RUNNING` - Workflow is executing
- `PAUSED` - Workflow is waiting for human approval
- `COMPLETED` - All steps completed successfully
- `FAILED` - A step failed, rollback triggered
- `ROLLED_BACK` - Rollback completed

### Step Status

```
PENDING ──execute──> RUNNING ──success──> COMPLETED
   │                    │
   │                    └──failure──> FAILED
   │
   └──human approval──> PAUSED ──approve──> COMPLETED
                           │
                           └──reject──> FAILED
```

---

## Transactional Model

### ACID-like Guarantees

**Atomicity:**
- All steps complete, or all are rolled back
- No partial state

**Consistency:**
- Workflow state is always valid
- Database constraints enforced

**Isolation:**
- Workflows don't interfere with each other
- (No distributed transactions yet)

**Durability:**
- All state persisted to database
- Survives crashes

### Compensation-Based Transactions

Unlike database transactions (BEGIN/COMMIT/ROLLBACK), AI-First uses **compensation-based transactions**:

**Traditional DBMS:**
```sql
BEGIN TRANSACTION;
  INSERT INTO users ...;
  UPDATE accounts ...;
COMMIT;  -- Or ROLLBACK
```

**AI-First:**
```yaml
steps:
  - name: create_user
    capability: db.insert
    compensation:
      capability: db.delete
      inputs: { user_id: "{{user_id}}" }
  
  - name: update_account
    capability: db.update
    compensation:
      capability: db.update
      inputs: { account_id: "{{account_id}}", balance: "{{old_balance}}" }
```

**Why compensation?**
- Operations span multiple systems (filesystem, cloud APIs, databases)
- No global transaction coordinator
- Long-running workflows (hours/days)
- Human approval gates

### Saga Pattern

AI-First implements the **Saga pattern** for distributed transactions:

1. Execute steps sequentially
2. Capture compensation for each step
3. On failure, execute compensations in reverse order

**Example:** Book flight + hotel

```yaml
steps:
  - name: book_flight
    capability: airline.book
    compensation:
      capability: airline.cancel
      inputs: { booking_id: "{{flight_booking_id}}" }
  
  - name: book_hotel
    capability: hotel.book
    compensation:
      capability: hotel.cancel
      inputs: { booking_id: "{{hotel_booking_id}}" }
  
  - name: charge_card
    capability: payment.charge
    compensation:
      capability: payment.refund
      inputs: { transaction_id: "{{transaction_id}}" }
```

**If `charge_card` fails:**
1. Refund payment (compensation for charge_card)
2. Cancel hotel (compensation for book_hotel)
3. Cancel flight (compensation for book_flight)

---

## Performance & Scalability

### Current Limitations (v3.0 Alpha)

- **Single-threaded execution** - Steps execute sequentially
- **In-memory state** - Workflow contexts stored in memory
- **SQLite database** - Single file, no replication
- **No distributed execution** - All steps run on one machine

### Future Improvements

**Parallel Execution:**
```yaml
- name: parallel_writes
  step_type: PARALLEL
  steps:
    - name: write_a
      capability: io.fs.write_file
      ...
    - name: write_b
      capability: io.fs.write_file
      ...
```

**Distributed Execution:**
- Use message queue (RabbitMQ, Redis) for step distribution
- Multiple worker processes
- Shared database for coordination

**Database Scaling:**
- PostgreSQL for production
- Read replicas for dashboard
- Partitioning by workflow_id

---

## Security & Compliance

### RBAC (Role-Based Access Control)

**Policy Rules:**
```yaml
rules:
  - principal: "user:alice"
    capability: "io.fs.*"
    risk_level: "LOW"
    decision: ALLOW
  
  - principal: "role:admin"
    capability: "*"
    risk_level: "HIGH"
    decision: REQUIRE_APPROVAL
```

### Audit Logging

**Every operation is logged:**
- Workflow submission
- Step execution
- Compensation execution
- Human approval decisions

**Audit levels:**
- `BASIC` - Workflow start/end
- `DETAILED` - Every step
- `FORENSIC` - Every capability call, including inputs/outputs

### Compliance

**SOC2 / HIPAA / GDPR:**
- Immutable audit trail
- Retention policies
- Data encryption at rest (SQLite encryption extension)
- Access control logs

---

## Next Steps

- Read [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) for practical examples
- Check [Week 3 Status Report](../week3_status_report.md) for implementation details
- Explore [examples/](../../examples/) for workflow templates

---

**Questions? Open an issue on GitHub!**
