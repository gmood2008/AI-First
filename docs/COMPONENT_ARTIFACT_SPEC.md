# Component Artifact Spec v1.0

## Purpose

This document defines a governance-compliant, auditable representation for renderable presentation components (e.g., charts and tables). It standardizes:

- Deterministic serialization rules
- Size limits
- Integrity checks (SHA256)
- Provenance (how the component was produced)

This spec is intended to prevent “black box blob” outputs and to enable policy enforcement and audit logging.

## ComponentArtifact (v1)

A `ComponentArtifact` is a JSON object with the following fields:

- `artifact_type` (enum)
  - `chart_component`
  - `table_component`
- `version` (string)
  - Must be `"1"`
- `payload` (object)
  - Type-specific structured payload (see below)
- `byte_size` (integer)
  - Byte length of canonical JSON encoding of the whole artifact
- `checksum_sha256` (string)
  - SHA256 of canonical JSON bytes
- `provenance` (object)
  - `producer_capability_id` (string)
  - `producer_version` (string)
  - `created_at` (string, ISO-8601)

## Deterministic canonical JSON

To compute `byte_size` and `checksum_sha256`, the artifact MUST be serialized with canonical JSON:

- UTF-8 encoding
- No insignificant whitespace
- Object keys sorted lexicographically
- Arrays preserved in order

## Governance constraints

- The component artifact MUST NOT contain external URLs.
- The component artifact MUST be bounded in size.
  - Default policy: `byte_size <= 1_000_000` (1MB)
- Any renderer producing a ComponentArtifact MUST log:
  - `artifact_type`, `byte_size`, `checksum_sha256`, `provenance`

## Payload schemas

### Chart payload

`payload.chart`:

- `chart_type` (enum)
  - `bar`, `line`, `pie`
- `title` (string)
- `series` (array)
  - each item:
    - `name` (string)
    - `values` (array of number)
- `x_labels` (array of string, optional)

### Table payload

`payload.table`:

- `headers` (array of string)
- `rows` (array of array of (string | number | null))
- `caption` (string, optional)
