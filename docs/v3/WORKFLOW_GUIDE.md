# AI-First Runtime v3.0 - Workflow Guide

**Complete guide to writing, executing, and managing transactional workflows**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Workflow Basics](#workflow-basics)
3. [Step Types](#step-types)
4. [Dependencies & Ordering](#dependencies--ordering)
5. [Compensation & Rollback](#compensation--rollback)
6. [Human-in-the-Loop](#human-in-the-loop)
7. [State Management](#state-management)
8. [Policy & RBAC](#policy--rbac)
9. [Crash Recovery](#crash-recovery)
10. [Best Practices](#best-practices)
11. [Examples](#examples)

---

## Introduction

AI-First Runtime v3.0 introduces **transactional workflows** - a way to define multi-step operations with automatic rollback on failure. Workflows are defined in YAML and executed by the WorkflowEngine.

**Key Features:**
- **Transactional:** All-or-nothing execution with automatic rollback
- **Resilient:** Workflows survive process crashes
- **Governed:** RBAC and policy enforcement
- **Auditable:** Every step is logged to database

---

## Workflow Basics

### Minimal Workflow

```yaml
name: hello_world
version: 1.0.0
description: Minimal workflow example

steps:
  - name: say_hello
    capability: sys.exec.run
    inputs:
      command: "echo Hello, World!"
```

### Workflow Structure

```yaml
name: <workflow_name>           # Required: Unique identifier
version: <semver>                # Required: Semantic version
description: <text>              # Required: Human-readable description

metadata:                        # Optional: Additional metadata
  owner: <user_id>               # Required: Who owns this workflow
  tags: [<tag1>, <tag2>]         # Optional: Tags for organization
  audit_level: <level>           # Optional: BASIC, DETAILED, FORENSIC

steps:                           # Required: List of steps
  - name: <step_name>            # Required: Unique step identifier
    capability: <capability_id>  # Required: Capability to execute
    inputs: <key-value pairs>    # Required: Input parameters
    depends_on: [<step_names>]   # Optional: Dependencies
    compensation: <undo_spec>    # Optional: How to undo this step
    risk_level: <level>          # Optional: LOW, MEDIUM, HIGH
    description: <text>          # Optional: What this step does
```

---

## Step Types

### 1. ACTION Steps

Execute a capability and produce outputs.

```yaml
- name: create_directory
  step_type: ACTION              # Default, can be omitted
  capability: io.fs.make_dir
  inputs:
    path: "/tmp/mydir"
  risk_level: LOW
```

### 2. HUMAN_APPROVAL Steps

Pause workflow and wait for human approval.

```yaml
- name: approval_gate
  step_type: HUMAN_APPROVAL
  capability: human.approve      # Special capability
  inputs:
    message: "Approve this operation?"
    webhook_url: "https://slack.com/webhooks/..."
    timeout: 3600                # Optional: Timeout in seconds
  risk_level: HIGH
```

**Workflow pauses until:**
- Approved via `airun workflow resume <id> --decision approve`
- Rejected via `airun workflow resume <id> --decision reject`
- Timeout expires (default: no timeout)

### 3. PARALLEL Steps (Planned)

Execute multiple steps in parallel.

```yaml
- name: parallel_writes
  step_type: PARALLEL
  steps:
    - name: write_a
      capability: io.fs.write_file
      inputs:
        path: "/tmp/a.txt"
        content: "A"
    
    - name: write_b
      capability: io.fs.write_file
      inputs:
        path: "/tmp/b.txt"
        content: "B"
```

---

## Dependencies & Ordering

### Sequential Execution

By default, steps execute in order:

```yaml
steps:
  - name: step1
    capability: io.fs.make_dir
    inputs:
      path: "/tmp/dir"
  
  - name: step2
    capability: io.fs.write_file
    inputs:
      path: "/tmp/dir/file.txt"
      content: "Hello"
```

### Explicit Dependencies

Use `depends_on` to specify dependencies:

```yaml
steps:
  - name: create_db
    capability: cloud.db.create
    inputs:
      name: "mydb"
  
  - name: create_table
    capability: cloud.db.exec_sql
    inputs:
      database: "mydb"
      sql: "CREATE TABLE users (...)"
    depends_on: [create_db]
  
  - name: insert_data
    capability: cloud.db.exec_sql
    inputs:
      database: "mydb"
      sql: "INSERT INTO users (...)"
    depends_on: [create_table]
```

### Multiple Dependencies

A step can depend on multiple previous steps:

```yaml
steps:
  - name: fetch_data_a
    capability: net.http.get
    inputs:
      url: "https://api.example.com/a"
  
  - name: fetch_data_b
    capability: net.http.get
    inputs:
      url: "https://api.example.com/b"
  
  - name: merge_data
    capability: data.json.merge
    inputs:
      data_a: "{{fetch_data_a.response}}"
      data_b: "{{fetch_data_b.response}}"
    depends_on: [fetch_data_a, fetch_data_b]
```

---

## Compensation & Rollback

### Automatic Rollback

If any step fails, all completed steps are rolled back in reverse order.

**Example:** Create directory, write file, then fail

```yaml
steps:
  - name: create_dir
    capability: io.fs.make_dir
    inputs:
      path: "/tmp/testdir"
    compensation:
      capability: io.fs.delete
      inputs:
        path: "/tmp/testdir"
  
  - name: write_file
    capability: io.fs.write_file
    inputs:
      path: "/tmp/testdir/file.txt"
      content: "Hello"
    compensation:
      capability: io.fs.delete
      inputs:
        path: "/tmp/testdir/file.txt"
  
  - name: fail_step
    capability: test.fail
    inputs:
      message: "Intentional failure"
```

**Execution:**
1. `create_dir` succeeds
2. `write_file` succeeds
3. `fail_step` fails
4. **Rollback:** `write_file` compensation executes (deletes file)
5. **Rollback:** `create_dir` compensation executes (deletes directory)

**Result:** `/tmp/testdir` is gone, as if nothing happened.

### Compensation Strategies

#### 1. Delete (Most Common)

```yaml
- name: create_resource
  capability: cloud.vm.create
  inputs:
    name: "myvm"
  compensation:
    capability: cloud.vm.delete
    inputs:
      vm_id: "{{vm_id}}"
```

#### 2. Restore

```yaml
- name: update_config
  capability: io.fs.write_file
  inputs:
    path: "/etc/config.yaml"
    content: "{{new_config}}"
  compensation:
    capability: io.fs.write_file
    inputs:
      path: "/etc/config.yaml"
      content: "{{original_config}}"
```

#### 3. Inverse Operation

```yaml
- name: add_user
  capability: sys.user.create
  inputs:
    username: "alice"
  compensation:
    capability: sys.user.delete
    inputs:
      username: "alice"
```

### Runtime Undo Closures

If a capability has built-in undo support, you don't need to specify compensation:

```yaml
- name: write_file
  capability: io.fs.write_file
  inputs:
    path: "/tmp/file.txt"
    content: "Hello"
  # No compensation needed - RuntimeEngine captures undo closure
```

**How it works:**
1. RuntimeEngine executes `io.fs.write_file`
2. Capability handler creates undo closure: `lambda: os.remove("/tmp/file.txt")`
3. WorkflowEngine captures closure and stores in compensation stack
4. On rollback, closure is executed

---

## Human-in-the-Loop

### Basic Approval Gate

```yaml
- name: approval_required
  step_type: HUMAN_APPROVAL
  capability: human.approve
  inputs:
    message: "Approve this operation?"
```

**Workflow pauses. Resume with:**

```bash
airun workflow resume <workflow_id> --decision approve
```

### Webhook Notification

Send approval request to Slack/Teams/etc:

```yaml
- name: approval_with_webhook
  step_type: HUMAN_APPROVAL
  capability: human.approve
  inputs:
    message: "Delete production database?"
    webhook_url: "https://hooks.slack.com/services/..."
    webhook_payload:
      channel: "#ops"
      username: "AI-First Bot"
      icon_emoji: ":robot_face:"
```

**Webhook receives:**

```json
{
  "workflow_id": "abc123",
  "workflow_name": "delete_prod_db",
  "step_name": "approval_with_webhook",
  "message": "Delete production database?",
  "requested_at": "2026-01-23T10:00:00Z",
  "approve_url": "https://airun.example.com/approve/abc123",
  "reject_url": "https://airun.example.com/reject/abc123"
}
```

### Approval with Context

Pass workflow state to approver:

```yaml
- name: approval_with_context
  step_type: HUMAN_APPROVAL
  capability: human.approve
  inputs:
    message: "Approve deployment?"
    context:
      version: "{{app_version}}"
      environment: "production"
      database: "{{database_name}}"
      estimated_downtime: "5 minutes"
```

### Rejection Triggers Rollback

If rejected, workflow rolls back all completed steps:

```bash
airun workflow resume <workflow_id> --decision reject
```

**Result:** Workflow status = FAILED, all steps rolled back.

---

## State Management

### Template Variables

Reference outputs from previous steps using `{{step_name.output_key}}`:

```yaml
steps:
  - name: create_db
    capability: cloud.db.create
    inputs:
      name: "mydb"
    # Outputs: { "database_id": "db-123", "connection_string": "..." }
  
  - name: deploy_app
    capability: cloud.app.deploy
    inputs:
      database: "{{create_db.database_id}}"
      connection_string: "{{create_db.connection_string}}"
```

### Workflow State

All step outputs are merged into workflow state:

```python
# After step1 and step2
workflow_state = {
    "step1.output_a": "value_a",
    "step1.output_b": "value_b",
    "step2.output_c": "value_c"
}
```

### Accessing State in Compensation

```yaml
- name: create_resource
  capability: cloud.vm.create
  inputs:
    name: "myvm"
  compensation:
    capability: cloud.vm.delete
    inputs:
      vm_id: "{{create_resource.vm_id}}"  # From step outputs
```

---

## Policy & RBAC

### Risk Levels

Classify steps by risk:

```yaml
- name: read_file
  capability: io.fs.read_file
  inputs:
    path: "/tmp/file.txt"
  risk_level: LOW

- name: delete_file
  capability: io.fs.delete
  inputs:
    path: "/prod/important.txt"
  risk_level: HIGH
```

**Risk Levels:**
- `LOW` - Read-only operations
- `MEDIUM` - Write operations with undo
- `HIGH` - Destructive operations, network writes

### Policy Rules

Define who can execute what:

```yaml
# policies.yaml
rules:
  - principal: "user:alice"
    capability: "io.fs.*"
    risk_level: "LOW"
    decision: ALLOW
  
  - principal: "user:bob"
    capability: "cloud.vm.create"
    risk_level: "MEDIUM"
    decision: REQUIRE_APPROVAL
  
  - principal: "user:*"
    capability: "io.fs.delete"
    risk_level: "HIGH"
    decision: DENY
```

**Policy Decisions:**
- `ALLOW` - Execute immediately
- `REQUIRE_APPROVAL` - Pause and wait for human approval
- `DENY` - Reject execution

---

## Crash Recovery

### Automatic State Persistence

Every step execution is checkpointed to database:

```sql
-- workflows table
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,  -- PENDING, RUNNING, PAUSED, COMPLETED, FAILED
    spec_yaml TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- workflow_steps table
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
```

### Auto-Resume on Startup

WorkflowEngine automatically resumes workflows on startup:

```python
engine = WorkflowEngine(
    runtime_engine=runtime,
    persistence=WorkflowPersistence(db_path="audit.db")
)
# Automatically resumes RUNNING and PAUSED workflows
```

### Manual Resume

Resume a specific workflow:

```bash
# List paused workflows
airun workflow list --status PAUSED

# Resume with approval
airun workflow resume <workflow_id> --decision approve

# Resume with rejection (triggers rollback)
airun workflow resume <workflow_id> --decision reject
```

---

## Best Practices

### 1. Always Define Compensation

Even if capability has built-in undo, explicit compensation is clearer:

```yaml
# Good
- name: create_file
  capability: io.fs.write_file
  inputs:
    path: "/tmp/file.txt"
    content: "Hello"
  compensation:
    capability: io.fs.delete
    inputs:
      path: "/tmp/file.txt"

# Also OK (relies on runtime undo)
- name: create_file
  capability: io.fs.write_file
  inputs:
    path: "/tmp/file.txt"
    content: "Hello"
```

### 2. Use Descriptive Names

```yaml
# Bad
- name: step1
  capability: io.fs.write_file
  ...

# Good
- name: write_config_file
  capability: io.fs.write_file
  ...
```

### 3. Add Descriptions

```yaml
- name: deploy_app
  capability: cloud.app.deploy
  description: "Deploy application v1.0 to production environment"
  inputs:
    ...
```

### 4. Classify Risk Levels

```yaml
- name: delete_prod_db
  capability: cloud.db.delete
  risk_level: HIGH  # Forces approval or policy check
  inputs:
    ...
```

### 5. Use Human Approval for Destructive Operations

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
      message: "Backup complete. Approve deletion?"
    depends_on: [backup_data]
  
  - name: delete_data
    capability: io.fs.delete
    inputs:
      path: "/prod/data"
    depends_on: [approval_gate]
```

### 6. Test Rollback

Always test that your compensations work:

```yaml
# Add a fail step to trigger rollback
- name: test_rollback
  capability: test.fail
  inputs:
    message: "Testing rollback"
```

---

## Examples

### Example 1: Simple File Operations

```yaml
name: file_operations
version: 1.0.0
description: Create directory and write files

steps:
  - name: create_dir
    capability: io.fs.make_dir
    inputs:
      path: "/tmp/myapp"
    compensation:
      capability: io.fs.delete
      inputs:
        path: "/tmp/myapp"
  
  - name: write_config
    capability: io.fs.write_file
    inputs:
      path: "/tmp/myapp/config.yaml"
      content: "app_name: myapp\nversion: 1.0"
    depends_on: [create_dir]
    compensation:
      capability: io.fs.delete
      inputs:
        path: "/tmp/myapp/config.yaml"
```

### Example 2: Deploy with Approval

```yaml
name: deploy_to_prod
version: 1.0.0
description: Deploy application to production with approval

metadata:
  owner: "devops_team"
  audit_level: FORENSIC

steps:
  - name: run_tests
    capability: sys.exec.run
    inputs:
      command: "pytest tests/"
    risk_level: LOW
  
  - name: build_image
    capability: sys.exec.run
    inputs:
      command: "docker build -t myapp:v1.0 ."
    depends_on: [run_tests]
    risk_level: LOW
  
  - name: approval_gate
    step_type: HUMAN_APPROVAL
    inputs:
      message: "Tests passed. Approve production deployment?"
      webhook_url: "https://slack.com/webhooks/..."
    depends_on: [build_image]
    risk_level: HIGH
  
  - name: deploy_to_prod
    capability: cloud.app.deploy
    inputs:
      image: "myapp:v1.0"
      environment: "production"
    depends_on: [approval_gate]
    risk_level: HIGH
    compensation:
      capability: cloud.app.rollback
      inputs:
        app_id: "{{deploy_to_prod.app_id}}"
```

### Example 3: Database Migration

```yaml
name: db_migration
version: 1.0.0
description: Migrate database schema with backup

steps:
  - name: backup_db
    capability: cloud.db.backup
    inputs:
      database: "prod_db"
      backup_name: "prod_db_backup_{{timestamp}}"
    risk_level: MEDIUM
  
  - name: run_migration
    capability: cloud.db.exec_sql
    inputs:
      database: "prod_db"
      sql_file: "migrations/v2.0.sql"
    depends_on: [backup_db]
    risk_level: HIGH
    compensation:
      capability: cloud.db.restore
      inputs:
        database: "prod_db"
        backup_name: "{{backup_db.backup_name}}"
  
  - name: verify_migration
    capability: cloud.db.exec_sql
    inputs:
      database: "prod_db"
      sql: "SELECT COUNT(*) FROM new_table"
    depends_on: [run_migration]
    risk_level: LOW
```

---

## CLI Reference

### Execute Workflow

```bash
airun workflow run <workflow.yaml>
```

### List Workflows

```bash
airun workflow list [--status STATUS]
```

### Resume Workflow

```bash
airun workflow resume <workflow_id> --decision approve|reject
```

### View Workflow Status

```bash
airun workflow status <workflow_id>
```

### Launch Dashboard

```bash
airun dashboard
```

---

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for deep dive into v3.0 design
- Check [examples/](../../examples/) for more workflow examples
- See [Week 3 Status Report](../week3_status_report.md) for implementation details

---

**Questions? Open an issue on GitHub!**
