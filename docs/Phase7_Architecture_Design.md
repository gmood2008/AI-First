# Phase 7 Architecture Design: The Interface of Power

**Project:** K-OS (Knowledge Operating System)  
**Phase:** Phase 7 - The Interface of Power  
**Date:** 2026-01-25  
**Author:** Manus AI  
**Status:** 🏗️ **IN DESIGN**

---

## 1. Strategic Context

Phase 7 represents a strategic pivot from "feature implementation" to "institutional solidification." We are not building user interfaces; we are constructing **the physical manifestation of constitutional control over AI systems.**

### The Three Hidden Constitutions

1. **UI is a View:** UI is never the sole entry point. Every UI action must have a corresponding API/CLI equivalent. UI is merely a projection of underlying logic and contains no independent business logic.

2. **Click is Event:** Every human click (approve, reject, pause) is fundamentally a Signed Event sent to the system. It must be 100% reproducible in the Trace.

3. **Interface is Isolation:** Physical isolation between the three UIs is the final defense against power abuse. We must never attempt to unify them.

---

## 2. Architecture Principles

### 2.1. API-First Design

**Principle:** All functionality must be implemented as APIs first, then exposed through UI as a thin presentation layer.

**Implementation Strategy:**
- Define OpenAPI specifications before writing any code
- Implement backend APIs with full authentication and authorization
- Build UI as stateless clients that only consume APIs
- Ensure CLI tools use the same APIs as UI

**Validation:** If the UI server crashes, all operations must still be executable via CLI/API.

### 2.2. Power Separation Architecture

**Three Independent Systems:**

| System | Purpose | Power | Constraint |
| :--- | :--- | :--- | :--- |
| **Docling Debugger** | Fact Entry | Read-only observation | Cannot modify what Docling sees |
| **K-OS Governance Console** | Judgment Entry | Approve/Reject/Override | Cannot modify Runtime execution |
| **Runtime Mission Control** | Execution Entry | Pause/Resume control | Cannot modify workflow content |

**Physical Isolation:**
- Three separate web applications
- Three separate API endpoints
- Three separate authentication domains
- No shared frontend state

### 2.3. Event Sourcing for Auditability

**Principle:** Every UI action is an event that must be:
1. Signed by the user (authentication)
2. Timestamped with millisecond precision
3. Recorded in an immutable audit log
4. Reproducible from the event stream

**Event Schema:**
```json
{
  "event_id": "uuid",
  "event_type": "GOVERNANCE_DECISION" | "RUNTIME_CONTROL" | "DOCLING_INSPECTION",
  "timestamp": "ISO8601",
  "user_id": "string",
  "user_role": "string",
  "action": "APPROVE" | "REJECT" | "PAUSE" | "RESUME" | "VIEW",
  "target": {
    "type": "knowledge" | "workflow" | "document",
    "id": "string"
  },
  "reason": "string",
  "signature": "cryptographic_signature"
}
```

---

## 3. System Design

### 3.1. Docling Debugger (Fact Entry)

**Purpose:** Engineers calibrate the "senses" of the system by previewing what Docling extracts from documents.

**API Endpoints:**
```
GET  /docling/v1/documents              # List parsed documents
GET  /docling/v1/documents/{id}         # Get document details
GET  /docling/v1/documents/{id}/preview # Get parsing preview
GET  /docling/v1/documents/{id}/raw     # Get raw document content
GET  /docling/v1/parsing/stats          # Get parsing statistics
```

**UI Features:**
- Document list with parsing status
- Side-by-side view: Raw document vs. Parsed output
- Syntax highlighting for extracted metadata
- Diff view for re-parsing results

**Constraints:**
- ❌ No edit capabilities
- ❌ No re-parsing triggers (must use CLI)
- ✅ Read-only observation only

**CLI Equivalent:**
```bash
k-os docling list
k-os docling inspect <doc_id>
k-os docling preview <doc_id>
k-os docling stats
```

### 3.2. K-OS Governance Console (Judgment Entry)

**Purpose:** Compliance officers exercise judicial discretion by approving or rejecting knowledge ingestion and capability activation.

**API Endpoints:**
```
GET  /governance/v1/pending              # List pending decisions
POST /governance/v1/decisions            # Make a decision
GET  /governance/v1/decisions/{id}       # Get decision details
GET  /governance/v1/knowledge/versions   # List knowledge versions (Time Machine)
GET  /governance/v1/knowledge/{id}/history # Get decision history for knowledge
POST /governance/v1/override             # Override a previous decision (requires elevated permission)
```

**UI Features:**
- **Approval Inbox:** List of pending knowledge awaiting review
- **Decision Panel:** Approve/Reject with mandatory reason code
- **Time Machine:** View historical versions and decisions
- **Audit Trail:** Complete decision history with who/when/why

**Critical Implementation:**
When a compliance officer clicks "REJECT":
1. Frontend calls `POST /governance/v1/decisions`
2. Backend records: `who` (User ID), `when` (Timestamp), `what` (Decision), `why` (Reason Code)
3. Backend emits a `GOVERNANCE_DECISION` event
4. Backend updates K-OS state (e.g., mark knowledge as rejected)

**Time Machine Feature:**
- Not only view old knowledge versions
- Also view **"decisions made based on old knowledge at that time"**
- Reconstruct the governance state at any point in history

**Constraints:**
- ✅ Can approve/reject knowledge ingestion
- ✅ Can override previous decisions (with elevated permission)
- ❌ Cannot modify knowledge content
- ❌ Cannot directly control Runtime

**CLI Equivalent:**
```bash
k-os governance pending
k-os governance approve <knowledge_id> --reason "COMPLIANT"
k-os governance reject <knowledge_id> --reason "POLICY_VIOLATION"
k-os governance history <knowledge_id>
k-os governance timemachine --version v1.2.3
```

### 3.3. Runtime Mission Control (Execution Entry)

**Purpose:** SREs have emergency brake control to pause/resume workflows, but cannot modify workflow content.

**API Endpoints:**
```
GET  /runtime/v1/workflows               # List active workflows
GET  /runtime/v1/workflows/{id}          # Get workflow details
POST /runtime/v1/workflows/{id}/pause    # Pause a workflow
POST /runtime/v1/workflows/{id}/resume   # Resume a workflow
GET  /runtime/v1/workflows/{id}/trace    # Get execution trace
GET  /runtime/v1/health                  # Get Runtime health status
```

**UI Features:**
- **Workflow Dashboard:** Real-time status of all workflows
- **Red Button:** Pause/Resume control with confirmation
- **Trace Viewer:** Visualize execution trace with Trace ID
- **Health Monitor:** System health and performance metrics

**Critical Implementation:**
When an SRE clicks "PAUSE":
1. Frontend calls `POST /runtime/v1/workflows/{id}/pause`
2. Backend records: `who` (User ID), `when` (Timestamp), `what` (PAUSE), `why` (Reason)
3. Backend emits a `RUNTIME_CONTROL` event
4. Backend sends pause signal to Runtime

**Constraints:**
- ✅ Can pause/resume workflows (control state)
- ✅ Can view execution traces
- ❌ Cannot modify workflow steps (control content)
- ❌ Cannot approve/reject knowledge

**CLI Equivalent:**
```bash
k-os runtime list
k-os runtime status <workflow_id>
k-os runtime pause <workflow_id> --reason "EMERGENCY_MAINTENANCE"
k-os runtime resume <workflow_id>
k-os runtime trace <workflow_id>
```

---

## 4. Technology Stack

### 4.1. Backend (API Layer)

**Framework:** FastAPI (Python 3.11+)
- OpenAPI auto-generation
- Built-in authentication support
- High performance async/await

**Authentication:** JWT-based with role-based access control (RBAC)
- `docling_engineer` role for Docling Debugger
- `compliance_officer` role for K-OS Governance Console
- `sre` role for Runtime Mission Control

**Database:** 
- SQLAlchemy (metadata)
- Event Store (audit log, append-only)

**API Documentation:** Auto-generated Swagger UI at `/docs`

### 4.2. Frontend (UI Layer)

**Framework:** React + TypeScript + TailwindCSS (via Vite scaffold)

**State Management:** React Query (no shared global state between UIs)

**Routing:** React Router (each UI is a separate SPA)

**HTTP Client:** Axios with interceptors for authentication

**Design System:** Custom components following the "power interface" aesthetic
- Minimal, high-contrast design
- Clear visual hierarchy
- Confirmation dialogs for destructive actions

### 4.3. CLI Layer

**Framework:** Click (Python)

**Implementation:** Reuse the same API client library as UI

**Authentication:** API key stored in `~/.k-os/config.yaml`

**Output Formats:** JSON, YAML, Table (for human readability)

---

## 5. Power & Responsibility Matrix

| UI Button | API Endpoint | HTTP Method | Required Role | CLI Equivalent | Fallback if UI Down |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Docling: View Document** | `/docling/v1/documents/{id}` | GET | `docling_engineer` | `k-os docling inspect <id>` | `curl -H "Authorization: Bearer $TOKEN" $API/docling/v1/documents/{id}` |
| **Governance: Approve** | `/governance/v1/decisions` | POST | `compliance_officer` | `k-os governance approve <id>` | `curl -X POST -H "Authorization: Bearer $TOKEN" -d '{"decision":"APPROVE"}' $API/governance/v1/decisions` |
| **Governance: Reject** | `/governance/v1/decisions` | POST | `compliance_officer` | `k-os governance reject <id>` | `curl -X POST -H "Authorization: Bearer $TOKEN" -d '{"decision":"REJECT"}' $API/governance/v1/decisions` |
| **Runtime: Pause** | `/runtime/v1/workflows/{id}/pause` | POST | `sre` | `k-os runtime pause <id>` | `curl -X POST -H "Authorization: Bearer $TOKEN" $API/runtime/v1/workflows/{id}/pause` |
| **Runtime: Resume** | `/runtime/v1/workflows/{id}/resume` | POST | `sre` | `k-os runtime resume <id>` | `curl -X POST -H "Authorization: Bearer $TOKEN" $API/runtime/v1/workflows/{id}/resume` |

**Key Principle:** If any UI is down, all operations can be performed via CLI or direct API calls.

---

## 6. Audit Trail Schema

Every UI action generates an immutable audit event:

```python
class AuditEvent(BaseModel):
    event_id: UUID
    event_type: Literal["GOVERNANCE_DECISION", "RUNTIME_CONTROL", "DOCLING_INSPECTION"]
    timestamp: datetime
    user_id: str
    user_role: str
    action: str  # APPROVE, REJECT, PAUSE, RESUME, VIEW, etc.
    target_type: str  # knowledge, workflow, document
    target_id: str
    reason: Optional[str]
    metadata: Dict[str, Any]  # Additional context
    signature: str  # Cryptographic signature for non-repudiation
```

**Storage:** Append-only event store (no updates or deletes allowed)

**Querying:** Support filtering by user, time range, action type, target

**Compliance:** All events retained for 7 years (configurable)

---

## 7. Future-Proofing for Phase 8-10

### 7.1. Phase 8: Institutional Hardening

**Preparation:**
- All UI actions already emit events → Easy to replay for "malicious compliance officer" tests
- RBAC already in place → Easy to convert to policy-as-code
- No business logic in UI → Easy to add rate limiting and abuse detection

### 7.2. Phase 9: Composable Adoption

**Preparation:**
- Three UIs are already physically separated → Easy to deploy independently
- Each UI only depends on its corresponding API → No cross-dependencies
- CLI tools are module-agnostic → Can be packaged with any module

### 7.3. Phase 10: Cognitive Infrastructure

**Preparation:**
- Event sourcing architecture → Foundation for "organizational memory"
- Time Machine feature → Foundation for "cognitive drift" detection
- Audit trail → Foundation for "collective correction" mechanisms

---

## 8. Implementation Roadmap

### Phase 7.1: API Development (Backend First)
1. Define OpenAPI specifications for all three systems
2. Implement FastAPI endpoints with authentication
3. Build event sourcing infrastructure
4. Create API documentation

### Phase 7.2: UI Development (Frontend)
1. Initialize three separate Vite + React projects
2. Build Docling Debugger UI (read-only)
3. Build K-OS Governance Console UI (decision-making)
4. Build Runtime Mission Control UI (control)

### Phase 7.3: CLI Development
1. Extend existing K-OS CLI with new commands
2. Ensure all UI actions have CLI equivalents
3. Write CLI documentation

### Phase 7.4: Integration & Testing
1. End-to-end testing of all three systems
2. Audit trail verification
3. Power & Responsibility Matrix validation

---

## 9. Success Criteria

- ✅ All UI actions have corresponding API endpoints
- ✅ All API endpoints have corresponding CLI commands
- ✅ All UI actions generate audit events
- ✅ Three UIs are physically isolated (no shared state)
- ✅ Power & Responsibility Matrix is complete and accurate
- ✅ If any UI crashes, all operations can be performed via CLI

---

**Next Steps:** Begin API development for the three systems, starting with OpenAPI specification design.
