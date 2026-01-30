# Governance Constitution (Phase A)

This document defines non-negotiable red lines for integrating new capabilities into AI-First Runtime.
The goal is that any new capability is **naturally compliant** by construction.

## Scope

This constitution covers:

- External Capability Adapters
- Packs
- Skill Facades
- Registry ingress

## Terms

- **Capability**: an executable unit registered in `CapabilityRegistry`.
- **External Adapter**: a mechanism to connect external tools (HTTP APIs / sidecars / agent tools) into the runtime.
- **Proposal**: a non-executable record describing an external capability candidate, requiring governance approval.
- **Pack**: a governed composition of capabilities and workflows with lifecycle states.
- **Facade**: a semantic routing layer for users; execution must go through a governed route.

## Red Lines (Non-Negotiable)

### 1) Registry ingress red line

- External tools **must not** be directly registered as executable capabilities.
- The runtime must treat external integrations as **proposal-only** until governance approves the governed composition.

Enforcement intent:

- `CapabilityRegistry.register_external(...)` must not be used for runtime execution.
- External loading must generate proposals instead of registering handlers.

### 2) Facade routing red line

- A facade **must not** route directly to a capability.

Allowed route types:

- `workflow`
- `pack`

Disallowed route types:

- `capability`

### 3) Governance lifecycle red line

- Packs and Facades must obey lifecycle states.

Execution rules:

- Only `ACTIVE` packs/facades are executable.
- `FROZEN` and `DEPRECATED` must reject execution.

### 4) External execution safety red line

- External adapter execution must be mediated through a controlled runtime wrapper.

Minimum safety requirements:

- Per-call timeout
- Domain allowlist
- No filesystem / shell / arbitrary JS execution surfaces

## Required Architecture Pattern

### External integrations must follow this chain

`External Tool / Sidecar` → `AdapterRuntimeWrapper` → `Capability` → `Workflow` → `Pack (ACTIVE)` → `Facade (ACTIVE)` → `CLI/MCP`.

Direct execution shortcuts are not allowed.

## CI / Lint Policy

The repository must include machine checks that fail CI when a red line is violated.

Minimum checks:

- Disallow any code path calling `.register_external(...)` (except its own definition).
- Disallow any facade YAML route referencing `capability`.

## Authoritative Suites (Reference Implementations)

### Financial Skill Suite

- Facades:
  - `specs/facades/financial-analyst.yaml`
  - `specs/facades/pdf.yaml`
- Pack:
  - `packs/financial-analyst/pack.yaml`
- Workflow:
  - `packs/financial-analyst/financial_report.yaml`

### Web Research Suite (dev-browser)

- Sidecar:
  - `src/runtime/sidecars/dev_browser_sidecar.py`
- Capabilities:
  - `web.browser.navigate`
  - `web.browser.snapshot`
- Pack:
  - `packs/web-research/pack.yaml`
- Workflow:
  - `packs/web-research/web_research.yaml`
- Facade:
  - `specs/facades/web-research.yaml`

## Change Management

Any change that impacts these red lines requires:

- Updating this document
- Updating the governance lint (CI enforcement)
- Updating the authoritative suites if needed
