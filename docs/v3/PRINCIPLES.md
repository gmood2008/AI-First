# AI-First Runtime v3.0 Beta - Non-Negotiable Principles

**The Constitution of AI-First Runtime**

**Effective Date:** Week 5 (Beta Phase)  
**Status:** Binding on all development  
**Philosophy:** Control over Intelligence, Transactions over Speed

---

## Preamble

AI-First Runtime is a **transactional control plane** for AI agents. We do not optimize for speed or intelligence—we optimize for **safety, auditability, and reversibility**. These 13 principles are the foundation of our architecture and must be upheld in all design decisions.

**Core Beliefs:**
1. **Control over Intelligence** - We don't make agents smarter; we make them safer
2. **Transactions over Speed** - We don't make agents faster; we make them reversible
3. **Governance over Autonomy** - We don't give agents freedom; we give them guardrails

---

## The 13 Principles

### Principle #1: The Runtime is a Control Plane, Not a Planner

**Statement:**  
AI-First Runtime does not decide WHAT to do. It controls HOW things are done.

**Rationale:**  
Planning is the job of LLMs (GPT, Claude, Gemini) and orchestration frameworks (AutoGen, CrewAI, LangChain). We sit between planning and execution, enforcing safety, auditability, and reversibility.

**Architecture:**
```
Planning Layer (LLM/AutoGen/CrewAI) → Decides WHAT
         ↓
AI-First Runtime (Control Plane) → Controls HOW
         ↓
Execution Layer (OS/APIs/Cloud) → Performs the work
```

**Implications:**
- We do not generate plans or make decisions
- We enforce policies, not strategies
- We are the "gatekeeper," not the "commander"

**Code Compliance:**
- ✅ WorkflowEngine executes YAML specs, does not generate them
- ✅ PolicyEngine says "yes" or "no," does not modify plans
- ❌ Do not add "auto-planning" or "agent reasoning" features

---

### Principle #2: Workflow is the Transaction Boundary

**Statement:**  
A workflow is an atomic unit of work. All steps complete, or all are rolled back.

**Rationale:**  
Distributed systems need transaction boundaries. In AI-First, the workflow is that boundary. Like a database transaction (BEGIN/COMMIT/ROLLBACK), a workflow guarantees atomicity.

**Guarantees:**
- **Atomicity:** All steps complete, or none do
- **Consistency:** Workflow state is always valid
- **Isolation:** Workflows don't interfere with each other
- **Durability:** State persists to database, survives crashes

**Implementation:**
- Every step captures a compensation action
- On failure, compensations execute in reverse order (LIFO)
- Workflow status transitions: PENDING → RUNNING → (COMPLETED | FAILED → ROLLED_BACK)

**Code Compliance:**
- ✅ WorkflowEngine._execute_workflow() enforces atomicity
- ✅ Compensation stack stored in WorkflowExecutionContext
- ✅ _rollback_workflow() executes compensations in reverse order
- ❌ Do not allow partial workflow completion without rollback

---

### Principle #3: All Side-Effects Must Be Compensable

**Statement:**  
Every operation with side effects MUST have a compensation strategy.

**Rationale:**  
If we can't undo it, we can't guarantee transactional semantics. Operations without undo are "architectural debt" that undermines the entire system.

**Side-Effect Categories:**
1. **Filesystem:** Create → Delete, Write → Restore, Delete → (Restore from backup)
2. **Network:** POST → DELETE, PUT → PUT (restore), PATCH → PATCH (revert)
3. **Cloud:** Create VM → Delete VM, Deploy → Undeploy
4. **Database:** INSERT → DELETE, UPDATE → UPDATE (restore), DELETE → (Restore from backup)

**Compensation Strategies:**
1. **Delete:** Most common (create → delete)
2. **Restore:** Capture original state, restore on rollback
3. **Inverse Operation:** Add user → Delete user

**Code Compliance:**
- ✅ Every WorkflowStep has optional `compensation` field
- ✅ RuntimeEngine captures undo closures for stdlib capabilities
- ⚠️ Compensation closures not persisted (known limitation)
- ❌ Do not allow steps with side effects without compensation

**Audit Checklist:**
- [ ] Does this capability have side effects?
- [ ] Is there a compensation strategy defined?
- [ ] Is the compensation tested?

---

### Principle #4: Human-in-the-Loop is Mandatory for High-Risk Operations

**Statement:**  
Operations classified as HIGH risk MUST require human approval.

**Rationale:**  
AI agents make mistakes. For destructive operations (delete production data, deploy to prod, charge credit card), a human must approve.

**Risk Classification:**
- **LOW:** Read-only operations (read file, GET request)
- **MEDIUM:** Write operations with undo (write file, POST with rollback)
- **HIGH:** Destructive operations (delete, deploy to prod, payment)

**Implementation:**
- WorkflowStep has `risk_level` field
- PolicyEngine can enforce `REQUIRE_APPROVAL` for HIGH risk
- HUMAN_APPROVAL step type pauses workflow, sends webhook
- Resume with `airun workflow resume <id> --decision approve|reject`

**Code Compliance:**
- ✅ WorkflowStep.risk_level enum (LOW, MEDIUM, HIGH)
- ✅ HUMAN_APPROVAL step type implemented
- ✅ HumanApprovalManager handles approval gates
- ❌ Do not allow HIGH risk operations without approval gate

**Audit Checklist:**
- [ ] Is this operation destructive or irreversible?
- [ ] Is it classified as HIGH risk?
- [ ] Does the workflow have an approval gate before this step?

---

### Principle #5: Crash is Normal, Recovery is Mandatory

**Statement:**  
Processes crash. Workflows must survive and resume.

**Rationale:**  
In production, processes crash due to OOM, SIGKILL, power loss, etc. Workflows must be resilient to crashes and automatically resume on restart.

**Recovery Strategy:**
1. **Checkpoint:** Save workflow state to database after each step
2. **Restore:** On startup, load incomplete workflows from database
3. **Resume:** Skip completed steps, execute remaining steps

**Persistence:**
- SQLite database with WAL mode
- 3 tables: `workflows`, `workflow_steps`, `compensation_log`
- Checkpoint after each step execution

**Code Compliance:**
- ✅ WorkflowPersistence handles database operations
- ✅ WorkflowRecovery.auto_resume_workflows() on startup
- ✅ _execute_workflow() skips completed steps
- ⚠️ Compensation closures not persisted (known limitation)
- ❌ Do not rely on in-memory state for critical data

**Audit Checklist:**
- [ ] Is workflow state persisted to database?
- [ ] Can workflow resume after crash?
- [ ] Are completed steps skipped on resume?

---

### Principle #6: Deterministic Recovery

**Statement:**  
Resuming a workflow after crash must produce the same result as if it never crashed.

**Rationale:**  
Recovery must be deterministic. If a workflow completes successfully after resume, it should be identical to a workflow that never crashed.

**Requirements:**
1. **Idempotent Steps:** Re-executing a completed step should be safe
2. **State Restoration:** Workflow state (outputs, compensation stack) must be fully restored
3. **No Side Effects on Resume:** Resume should not trigger duplicate operations

**Implementation:**
- Completed steps are skipped (not re-executed)
- Step outputs restored from database to workflow state
- Compensation stack reconstructed from YAML spec

**Code Compliance:**
- ✅ _execute_workflow() filters out completed steps
- ✅ Step outputs restored from database
- ⚠️ Compensation closures reconstructed from spec (not persisted)
- ❌ Do not re-execute completed steps on resume

**Audit Checklist:**
- [ ] Are completed steps skipped on resume?
- [ ] Is workflow state fully restored?
- [ ] Does resume produce the same result as no-crash?

---

### Principle #7: Audit Everything

**Statement:**  
Every operation must be logged to an immutable audit trail.

**Rationale:**  
For compliance (SOC2, HIPAA, GDPR), we need a forensic audit trail. Every workflow, step, and compensation must be logged with timestamps, inputs, outputs, and errors.

**Audit Levels:**
1. **BASIC:** Workflow start/end
2. **DETAILED:** Every step execution
3. **FORENSIC:** Every capability call, including inputs/outputs

**Logged Events:**
- Workflow submission
- Workflow start/pause/resume/complete/fail
- Step execution (start, complete, fail)
- Compensation execution
- Human approval decisions
- Policy enforcement decisions

**Code Compliance:**
- ✅ WorkflowPersistence logs to database
- ✅ AuditLogger (v2.0) logs capability executions
- ✅ HumanApprovalManager logs approval decisions
- ❌ Do not skip logging for "internal" operations

**Audit Checklist:**
- [ ] Is this operation logged?
- [ ] Are inputs/outputs logged (if FORENSIC)?
- [ ] Are timestamps recorded?

---

### Principle #8: Policy is Declarative, Not Imperative

**Statement:**  
Policies are defined in YAML, not code. The PolicyEngine interprets policies, it does not contain policy logic.

**Rationale:**  
Policies change frequently. Hardcoding policies in code creates "policy debt." Policies must be data-driven and hot-reloadable.

**Policy Structure:**
```yaml
rules:
  - principal: "user:alice"
    capability: "io.fs.*"
    risk_level: "LOW"
    decision: ALLOW
  
  - principal: "role:admin"
    capability: "cloud.vm.create"
    risk_level: "HIGH"
    decision: REQUIRE_APPROVAL
  
  - principal: "user:*"
    capability: "io.fs.delete"
    risk_level: "HIGH"
    decision: DENY
```

**Policy Decisions:**
- `ALLOW` - Execute immediately
- `REQUIRE_APPROVAL` - Pause and wait for human approval
- `DENY` - Reject execution, trigger rollback

**Code Compliance:**
- ✅ PolicyEngine loads from `policies.yaml`
- ✅ PolicyEngine.check_permission() evaluates rules
- ❌ Do not hardcode policy logic in PolicyEngine
- ❌ Do not allow PolicyEngine to modify inputs or inject logic

**Audit Checklist:**
- [ ] Are policies defined in YAML?
- [ ] Can policies be hot-reloaded?
- [ ] Does PolicyEngine only evaluate, not modify?

---

### Principle #9: The Gatekeeper, Not the Commander

**Statement:**  
The PolicyEngine says "yes" or "no." It does not modify plans, inject logic, or make decisions.

**Rationale:**  
The PolicyEngine is a **gatekeeper**, not a **commander**. It enforces rules, it does not create them. It checks permissions, it does not grant them conditionally with modifications.

**What PolicyEngine DOES:**
- ✅ Check if principal has permission to execute capability
- ✅ Evaluate risk level against policy rules
- ✅ Return ALLOW, DENY, or REQUIRE_APPROVAL

**What PolicyEngine DOES NOT DO:**
- ❌ Modify workflow inputs
- ❌ Inject additional steps
- ❌ Rewrite capability calls
- ❌ Make "smart" decisions based on context

**Example (Correct):**
```python
decision = policy_engine.check_permission(
    principal="user:alice",
    capability="io.fs.delete",
    inputs={"path": "/prod/data"}
)
if decision == PolicyDecision.DENY:
    raise PermissionDenied("User alice cannot delete /prod/data")
```

**Example (Incorrect):**
```python
# ❌ WRONG: PolicyEngine modifying inputs
decision, modified_inputs = policy_engine.check_permission(...)
if decision == PolicyDecision.ALLOW:
    inputs = modified_inputs  # ❌ Gatekeeper became Commander
```

**Code Compliance:**
- ✅ PolicyEngine.check_permission() returns PolicyDecision enum
- ❌ Do not allow PolicyEngine to return modified inputs
- ❌ Do not add "smart" logic to PolicyEngine

---

### Principle #10: Fail Fast, Rollback Faster

**Statement:**  
When a step fails, immediately trigger rollback. Do not attempt to "fix" or "recover" within the workflow.

**Rationale:**  
Workflows are transactions. If a step fails, the transaction fails. Rollback immediately to restore consistency.

**Failure Handling:**
1. Step fails → Mark workflow FAILED
2. Execute compensations in reverse order
3. Mark workflow ROLLED_BACK
4. Log error and audit trail

**Retry Policy (Exception):**
- Retries are allowed BEFORE rollback
- If retry succeeds, workflow continues
- If all retries fail, trigger rollback

**Code Compliance:**
- ✅ _handle_workflow_failure() triggers rollback
- ✅ Compensations executed in reverse order
- ⚠️ Retry policy not yet implemented (Week 5)
- ❌ Do not attempt to "fix" failures within workflow

**Audit Checklist:**
- [ ] Does step failure trigger rollback?
- [ ] Are compensations executed in reverse order?
- [ ] Is error logged to audit trail?

---

### Principle #11: Capabilities are Atomic

**Statement:**  
A capability is an atomic unit of execution. It succeeds completely or fails completely.

**Rationale:**  
Capabilities are the building blocks of workflows. They must be atomic to enable reliable composition.

**Requirements:**
1. **Single Responsibility:** One capability, one operation
2. **Atomic:** No partial success
3. **Idempotent:** Safe to re-execute
4. **Undoable:** Has compensation strategy

**Examples:**
- ✅ `io.fs.write_file` - Atomic (write entire file)
- ✅ `cloud.vm.create` - Atomic (create VM)
- ❌ `io.fs.write_multiple_files` - Not atomic (partial writes possible)

**Code Compliance:**
- ✅ Capability handlers in stdlib are atomic
- ✅ RuntimeEngine.execute() returns ExecutionResult (success/failure)
- ❌ Do not create capabilities with partial success

**Audit Checklist:**
- [ ] Is this capability atomic?
- [ ] Can it partially succeed?
- [ ] Is it idempotent?

---

### Principle #12: No Magic, Only Mechanisms

**Statement:**  
The system should be transparent and debuggable. No hidden behavior, no implicit state changes.

**Rationale:**  
"Magic" (implicit behavior) makes systems hard to debug and reason about. Every state change must be explicit and auditable.

**Examples of Magic (Avoid):**
- ❌ Auto-retry without explicit RetryPolicy
- ❌ Auto-approval based on "context"
- ❌ Implicit state mutations in PolicyEngine
- ❌ Hidden compensation strategies

**Examples of Mechanisms (Good):**
- ✅ Explicit compensation in YAML
- ✅ Explicit retry policy in WorkflowSpec
- ✅ Explicit approval gates in workflow
- ✅ Explicit policy rules in policies.yaml

**Code Compliance:**
- ✅ All state changes logged to database
- ✅ All compensations explicit in YAML or captured from runtime
- ❌ Do not add implicit behavior

**Audit Checklist:**
- [ ] Is this behavior explicit?
- [ ] Can it be disabled/configured?
- [ ] Is it logged to audit trail?

---

### Principle #13: The Constitution is Immutable (Until It's Not)

**Statement:**  
These principles are binding on all development. Changes require explicit approval and documentation.

**Rationale:**  
Principles prevent "architectural drift." If we violate a principle, we must document why and update the Constitution.

**Amendment Process:**
1. Propose amendment with rationale
2. Document impact on existing code
3. Update PRINCIPLES.md
4. Audit codebase for compliance

**Current Exceptions:**
- ⚠️ Compensation closures not persisted (Principle #3, #5) - Known limitation, documented

**Code Compliance:**
- ✅ This document exists and is linked in README
- ❌ Do not violate principles without amendment

---

## Compliance Audit

### Current Codebase Status

**Principle #3: All Side-Effects Must Be Compensable**

**Status:** ⚠️ Partial Compliance

**Issues:**
1. ✅ WorkflowStep has `compensation` field
2. ✅ RuntimeEngine captures undo closures
3. ⚠️ Compensation closures not persisted to database (lost on crash)

**Mitigation:**
- Use explicit YAML compensation for critical steps
- Document limitation in ARCHITECTURE.md
- Plan serialization with `dill` in future release

**Action Items:**
- [ ] Audit all stdlib capabilities for compensation strategies
- [ ] Document which capabilities have built-in undo
- [ ] Add tests for compensation execution

---

**Principle #6: Deterministic Recovery**

**Status:** ⚠️ Partial Compliance

**Issues:**
1. ✅ Completed steps skipped on resume
2. ✅ Step outputs restored from database
3. ⚠️ Compensation closures reconstructed from YAML (not persisted)

**Mitigation:**
- Compensation closures are reconstructed from YAML spec on resume
- Explicit YAML compensation ensures deterministic recovery
- Runtime undo closures may be lost (use explicit compensation for critical steps)

**Action Items:**
- [ ] Test resume with explicit YAML compensation
- [ ] Test resume with runtime undo closures (verify reconstruction)
- [ ] Document recovery behavior in ARCHITECTURE.md

---

**Principle #9: The Gatekeeper, Not the Commander**

**Status:** ✅ Compliant (Not Yet Implemented)

**Notes:**
- PolicyEngine not yet implemented (Week 5 priority)
- Design must ensure PolicyEngine only evaluates, does not modify

**Action Items:**
- [ ] Implement PolicyEngine.check_permission()
- [ ] Ensure return type is PolicyDecision enum only
- [ ] Add tests to verify no input modification

---

## Enforcement

**How to Uphold the Constitution:**

1. **Code Review:** Every PR must be reviewed against these principles
2. **Audit:** Regular audits of codebase for compliance
3. **Testing:** Tests must verify principle compliance
4. **Documentation:** Document any exceptions or limitations

**Red Flags (Reject PR):**
- ❌ Side effects without compensation
- ❌ PolicyEngine modifying inputs
- ❌ Implicit behavior without logging
- ❌ Partial workflow completion without rollback

**Yellow Flags (Requires Discussion):**
- ⚠️ New capability without undo strategy
- ⚠️ State change not logged to database
- ⚠️ Retry logic without explicit policy

---

## Conclusion

These 13 principles are the foundation of AI-First Runtime. They are not suggestions—they are **requirements**. Every design decision, every line of code, every feature must align with these principles.

**Remember:**
- **Control over Intelligence**
- **Transactions over Speed**
- **Governance over Autonomy**

**Build the Law. Enforce the Law. Uphold the Constitution.**

---

**Document Version:** 1.0  
**Effective Date:** Week 5 (Beta Phase)  
**Status:** Binding  
**Amendment History:** None

---

**Questions? Open an issue on GitHub!**
