# AI-First Runtime: Enterprise Audit & Compliance Guide

**Version:** 2.0  
**Audience:** CTOs, Compliance Officers, Security Teams  
**Last Updated:** January 22, 2026

---

## 1. The Compliance Imperative for AI Agents

As AI agents move from experimental toys to production systems, the need for enterprise-grade audit and compliance becomes paramount. Unmonitored AI agents operating in a corporate environment represent an unacceptable level of risk.

**AI-First Runtime was built to solve this problem.** Our Compliance Engine provides a complete, immutable, and auditable record of every action an AI agent takes.

This document outlines the features of our Compliance Engine and how it helps enterprises meet their regulatory and security requirements.

---

## 2. The Compliance Engine: How It Works

The Compliance Engine is a core component of AI-First Runtime, designed to be **always on** and **tamper-resistant**.

### 2.1. Architecture

| Component | Description | Technology |
|---|---|---|
| **AuditLogger** | Centralized logging service integrated into the RuntimeEngine. | Python | 
| **audit.db** | Persistent SQLite database storing all audit records. | SQLite (WAL mode) |
| **Data Sanitizer** | Automatically redacts sensitive information from logs. | Regex patterns |
| **Async Writer** | Background thread for non-blocking, high-throughput logging. | Python `threading` |
| **Report Generator** | Generates professional HTML reports from the audit database. | Python |

### 2.2. Data Flow

1.  An AI agent requests to execute a capability (e.g., `io.fs.write_file`).
2.  The `RuntimeEngine` receives the request.
3.  **Before execution**, the intent is logged (if configured).
4.  The capability is executed.
5.  **After execution**, the `AuditLogger` is invoked.
6.  The action details (params, result, status, etc.) are sanitized.
7.  The sanitized record is placed in an asynchronous write queue.
8.  A background thread writes the record to `audit.db`.

This ensures that logging has minimal performance impact on the agent's execution speed.

---

## 3. What Is Logged? The `audit_log` Schema

Every action is recorded as a row in the `audit_log` table. This provides a granular, chronological history of all agent activity.

**Key Logged Fields:**

| Field | Description | Example |
|---|---|---|
| `timestamp` | ISO 8601 timestamp of the action. | `2026-01-22T12:00:00Z` |
| `session_id` | Unique ID for the agent's session. | `mcp_20260122_120000` |
| `user_id` | Identifier for the user who initiated the session. | `claude_user_123` |
| `capability_id` | The capability that was executed. | `io.fs.write_file` |
| `action_type` | Type of action (execute, undo, etc.). | `execute` |
| `params_json` | Input parameters (sanitized). | `{"path": "/tmp/report.txt"}` |
| `result_json` | Output of the action (sanitized). | `{"bytes_written": 128}` |
| `status` | `success`, `failure`, or `denied`. | `success` |
| `side_effects` | Comma-separated list of side effects. | `filesystem_write` |
| `was_undone` | `1` if the action was later undone. | `0` |
| `undo_record_id` | ID of the corresponding undo action. | `NULL` |
| `error_message` | Error details if the action failed. | `NULL` |

### 3.1. Data Sanitization

To prevent sensitive data from being stored in logs, the `AuditLogger` automatically redacts any parameter or result field whose key matches common sensitive patterns:

- `.*token.*`
- `.*key.*`
- `.*password.*`
- `.*secret.*`

All matching values are replaced with `***REDACTED***`.

---

## 4. Generating Compliance Reports

AI-First Runtime includes a built-in command-line tool for generating professional compliance reports.

### 4.1. The `airun audit export` Command

This command queries the `audit.db` and generates a self-contained HTML report.

**Usage:**

```bash
# From the ai-first-runtime directory
python3 tools/airun/cli.py audit export \
  --session <session_id> \
  --output report.html
```

**Options:**

- `--db PATH`: Specify the path to `audit.db`.
- `--session ID`: Filter the report for a specific session.
- `--user ID`: Filter the report for a specific user.
- `--limit N`: Limit the number of records in the report.
- `-o, --output FILE`: Set the output file name.

### 4.2. The HTML Report

The generated report provides a clear, human-readable overview of agent activity, designed for review by compliance officers and security teams.

**Report Features:**

- **Dashboard Summary:** High-level statistics (total actions, success/failure rates, etc.).
- **Filter Display:** Clearly indicates which filters were applied.
- **Detailed Log Table:** A chronological list of all actions, with color-coded status badges.
- **Clear Flags:** Visual indicators for actions that were undone, required confirmation, or had undo available.
- **Responsive Design:** Readable on both desktop and mobile devices.

---

## 5. Security & Tamper Resistance

- **File Permissions:** The `audit.db` file is created with `0o600` permissions, meaning it is only readable and writable by the user running the runtime.
- **Immutable Records:** The logging pattern is append-only. While not strictly immutable, modifying historical records requires direct database manipulation and would be detectable in a secure environment.
- **Local Storage:** By default, the audit database is stored locally. For enterprise deployments, we recommend placing the database on a secure, write-once file system (WORM) or streaming logs to a dedicated security information and event management (SIEM) system.

---

## 6. Conclusion: Auditability as a First-Class Citizen

In the AI-First era, agentic systems without robust auditing are a liability. AI-First Runtime treats auditability not as an afterthought, but as a core design principle.

Our Compliance Engine provides the visibility and accountability that enterprises need to deploy AI agents with confidence.
