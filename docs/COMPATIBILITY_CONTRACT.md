# Compatibility Contract (AI-First Runtime)

This document defines the compatibility contract for AI-First Runtime for internal partner teams (e.g., Aegis).

---

## 1. Scope

This contract covers:

- Runtime package versioning (SemVer)
- Runtime assets compatibility (capabilities/packs/facades)
- CLI interface stability for partner integration
- Local bridge JSON output stability (Aegis subprocess integration)

It does not cover:

- LLM planner behavior
- Third-party APIs called by capabilities

---

## 2. SemVer rules (MAJOR.MINOR.PATCH)

We use SemVer for the runtime package `ai-first-runtime`.

- **PATCH**: bugfixes, documentation fixes, non-breaking asset fixes
- **MINOR**: backward compatible features, additive fields in schemas/contracts
- **MAJOR**: breaking changes that require partner code/config changes

Recommended consumer pinning:

- Default: `~=X.Y.0` to receive patch releases automatically
- For strict stability: `==X.Y.Z`

---

## 3. Asset compatibility (capabilities / packs / facades)

Runtime assets are delivered either:

- Embedded inside the wheel under `share/ai-first-runtime/...`, or
- Provided as plaintext assets via `AI_FIRST_ASSETS_DIR=<assets_root>`

Asset types:

- Capability specs: `capabilities/validated/stdlib/*.yaml`, `capabilities/validated/external/*.yaml`
- Packs: `packs/**` (including `pack.yaml`, workflows)
- Facade specs: `specs/facades/*.yaml`

### 3.1 Backward compatibility rules

- **Additive changes** are compatible:
  - adding optional fields
  - adding new capabilities/packs/facades
  - expanding enums only if old values remain valid
- **Breaking changes** require a MAJOR bump:
  - removing/renaming required fields
  - changing field type/meaning
  - removing capability IDs that were previously published

### 3.2 Deprecation policy

When a breaking change is planned:

- Mark the old field/capability as deprecated in docs and release notes
- Provide a migration guide
- Keep deprecated behavior for at least one MINOR release window when feasible

---

## 4. CLI compatibility

### 4.1 Stable commands (P0/P1)

The following CLI integration surface is considered stable for partner automation:

- `airun bridge exec-capability` (local subprocess bridge)
- `airun bridge exec-workflow` (local subprocess bridge)

Rules:

- Options are additive-only in MINOR/PATCH
- Removing/renaming flags requires a MAJOR bump

### 4.2 Exit codes

Exit codes are part of the integration contract for local bridge mode.

- `0`: success
- `10`: VALIDATION_ERROR
- `11`: PERMISSION_DENIED
- `12`: RESOURCE_NOT_FOUND
- `13`: TIMEOUT
- `14`: NETWORK_ERROR
- `15`: EXTERNAL_SERVICE_ERROR
- `16`: CONSTITUTION_VIOLATION
- `30`: PAUSED
- `20`: INTERNAL_ERROR
- `21`: UNKNOWN_ERROR

---

## 5. Local bridge JSON contract (Aegis)

### 5.1 Output shape

`airun bridge exec-capability` emits exactly one JSON object to stdout.

Fields:

- `id`: string
- `executionId`: string
- `traceId`: string
- `parentTraceId`: string | null
- `capabilityId`: string
- `capabilityName`: string
- `input`: object
- `output`: object | null
- `status`: `success` | `failure` | `timeout`
- `error`: object | null
- `startTime`: ISO timestamp string
- `endTime`: ISO timestamp string
- `durationMs`: number | null
- `userId`: string
- `metadata`: object | null

### 5.2 Stability rules

- Additive-only changes are allowed in MINOR/PATCH (new optional fields)
- Removing/renaming fields or changing semantics requires MAJOR bump

### 5.3 Schema validation hook

If a partner provides a JSON Schema file, the bridge supports validation via:

- `--schema-path <schema.json>`
- `AEGIS_EXECUTION_RECORD_SCHEMA=<schema.json>`

On schema validation failure, the bridge returns `VALIDATION_ERROR`.

For `airun bridge exec-workflow`, the bridge supports validation via:

- `--schema-path <schema.json>`
- `AEGIS_WORKFLOW_RECORD_SCHEMA=<schema.json>`

Published reference schema (repo-relative):

- `schemas/aegis/bridge_exec_workflow_output.schema.json`

---

## 6. Rollback strategy

- Code rollback: reinstall previous wheel version
- Assets rollback (plaintext mode): switch to previous assets commit/tag/snapshot

For plaintext assets mode, consumers should record both:

- `runtime_version`
- `assets_version`

in their deployment/CI metadata.
