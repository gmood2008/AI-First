# Governance Integration

This directory contains the governance and mission control interfaces for AI-First Runtime, developed as part of Project Trinity Phase 7.

## Overview

The governance integration provides operational control capabilities for runtime workflows, enabling SREs and operators to pause, resume, and monitor agent execution without modifying workflow logic.

## Components

### Mission Control API (`mission_control_api.py`)

A FastAPI-based REST API that provides:

- **Workflow Control**
  - `POST /v1/workflows/{id}/pause` - Pause a running workflow
  - `POST /v1/workflows/{id}/resume` - Resume a paused workflow
  
- **Monitoring**
  - `GET /v1/workflows` - List all workflows
  - `GET /v1/workflows/{id}` - Get workflow details
  - `GET /v1/workflows/{id}/trace` - View execution trace
  
- **Health**
  - `GET /v1/health` - Runtime health status

## Philosophy

> **"The SRE's brake pedal, not the steering wheel."**

This interface is designed for operational safety:
- ✅ Can pause/resume execution
- ✅ Can view workflow status
- ❌ Cannot modify workflow content
- ❌ Cannot change agent behavior

## Integration with K-OS

The Mission Control API integrates with K-OS for policy enforcement:

```python
from k_os.contextual_policy import check_policy

# Check if pause is allowed
result = check_policy(
    action="runtime.pause",
    user_id=current_user,
    user_role=current_role,
    context={"workflow_id": workflow_id}
)

if not result.allowed:
    raise PermissionDenied(result.message)
```

## Running the Mission Control API

```bash
# Install dependencies
pip install fastapi uvicorn

# Run the API
python governance/mission_control_api.py

# API will be available at http://localhost:8030
```

## API Documentation

Once running, visit `http://localhost:8030/docs` for interactive API documentation (Swagger UI).

## Security

All operations are:
- ✅ Authenticated (JWT tokens)
- ✅ Authorized (role-based access control)
- ✅ Audited (all actions logged)
- ✅ Policy-checked (K-OS integration)

## Related Documentation

- [Phase 7 Architecture Design](../docs/Phase7_Architecture_Design.md)
- [Trinity Architecture Overview](../ARCHITECTURE.md)

---

**Part of Project Trinity - Phase 7: The Interface of Power**
