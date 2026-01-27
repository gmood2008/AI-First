# Audit Database Schema Design

**Version:** 2.0  
**Purpose:** Enterprise-grade compliance logging for AI-First Runtime

---

## Overview

The audit database (`audit.db`) is a SQLite database that records every action performed by the AI-First Runtime. It provides a permanent, queryable record for compliance, debugging, and accountability.

---

## Schema Design

### Table: `audit_log`

Primary table for recording all runtime actions.

```sql
CREATE TABLE audit_log (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Temporal Information
    timestamp TEXT NOT NULL,  -- ISO 8601 format: 2026-01-22T14:30:00.123Z
    
    -- Session & User Context
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    
    -- Action Details
    capability_id TEXT NOT NULL,  -- e.g., "io.fs.write_file"
    action_type TEXT NOT NULL,    -- "execute", "undo", "confirm", "deny"
    
    -- Parameters & Results
    params_json TEXT,             -- JSON string of input parameters
    result_json TEXT,             -- JSON string of output/result
    
    -- Status & Classification
    status TEXT NOT NULL,         -- "success", "failure", "denied", "pending"
    side_effects TEXT,            -- Comma-separated: "fs_write,network_write"
    
    -- Safety & Compliance
    requires_confirmation BOOLEAN DEFAULT 0,
    was_confirmed BOOLEAN DEFAULT NULL,
    undo_available BOOLEAN DEFAULT 0,
    was_undone BOOLEAN DEFAULT 0,
    undo_record_id INTEGER,       -- Foreign key to itself (if this action was undone)
    
    -- Metadata
    error_message TEXT,           -- If status=failure
    duration_ms INTEGER,          -- Execution time in milliseconds
    
    -- Indexes for common queries
    FOREIGN KEY (undo_record_id) REFERENCES audit_log(id)
);

CREATE INDEX idx_session_id ON audit_log(session_id);
CREATE INDEX idx_timestamp ON audit_log(timestamp);
CREATE INDEX idx_capability_id ON audit_log(capability_id);
CREATE INDEX idx_status ON audit_log(status);
CREATE INDEX idx_user_id ON audit_log(user_id);
```

---

## Field Descriptions

| Field | Type | Description | Example |
|---|---|---|---|
| `id` | INTEGER | Auto-incrementing primary key | 1, 2, 3... |
| `timestamp` | TEXT | ISO 8601 timestamp with milliseconds | `2026-01-22T14:30:00.123Z` |
| `session_id` | TEXT | Unique identifier for the session | `session_abc123` |
| `user_id` | TEXT | User identifier (from ExecutionContext) | `user@example.com` |
| `capability_id` | TEXT | Capability being executed | `io.fs.write_file` |
| `action_type` | TEXT | Type of action | `execute`, `undo`, `confirm`, `deny` |
| `params_json` | TEXT | JSON-serialized input parameters | `{"path": "/tmp/test.txt", "content": "..."}` |
| `result_json` | TEXT | JSON-serialized output/result | `{"bytes_written": 42}` |
| `status` | TEXT | Execution status | `success`, `failure`, `denied`, `pending` |
| `side_effects` | TEXT | Comma-separated side effects | `fs_write,network_write` |
| `requires_confirmation` | BOOLEAN | Whether action required confirmation | `0` or `1` |
| `was_confirmed` | BOOLEAN | Whether user confirmed (NULL if not required) | `0`, `1`, or `NULL` |
| `undo_available` | BOOLEAN | Whether action can be undone | `0` or `1` |
| `was_undone` | BOOLEAN | Whether action was undone | `0` or `1` |
| `undo_record_id` | INTEGER | ID of the audit_log entry that undid this action | `42` or `NULL` |
| `error_message` | TEXT | Error message if status=failure | `Permission denied` |
| `duration_ms` | INTEGER | Execution time in milliseconds | `150` |

---

## Data Sanitization Rules

**Sensitive Parameters:**
- API keys, tokens, passwords are **masked** before writing to `params_json`
- Pattern: Replace with `"***REDACTED***"`
- Detection: Field names containing `token`, `key`, `password`, `secret`, `credential`

**Example:**
```json
// Original
{"api_key": "sk-1234567890", "message": "Hello"}

// Sanitized
{"api_key": "***REDACTED***", "message": "Hello"}
```

---

## Query Examples

### 1. Get all actions in a session
```sql
SELECT * FROM audit_log 
WHERE session_id = 'session_abc123' 
ORDER BY timestamp ASC;
```

### 2. Find all failed actions
```sql
SELECT timestamp, capability_id, error_message 
FROM audit_log 
WHERE status = 'failure' 
ORDER BY timestamp DESC;
```

### 3. Find all undone actions
```sql
SELECT a1.timestamp, a1.capability_id, a1.params_json, a2.timestamp AS undone_at
FROM audit_log a1
LEFT JOIN audit_log a2 ON a1.undo_record_id = a2.id
WHERE a1.was_undone = 1
ORDER BY a1.timestamp DESC;
```

### 4. Get actions with side effects
```sql
SELECT * FROM audit_log 
WHERE side_effects IS NOT NULL 
AND side_effects != ''
ORDER BY timestamp DESC;
```

### 5. Compliance report (last 24 hours)
```sql
SELECT 
    user_id,
    capability_id,
    COUNT(*) as action_count,
    SUM(CASE WHEN status = 'denied' THEN 1 ELSE 0 END) as denied_count,
    SUM(CASE WHEN was_undone = 1 THEN 1 ELSE 0 END) as undone_count
FROM audit_log
WHERE timestamp >= datetime('now', '-1 day')
GROUP BY user_id, capability_id
ORDER BY action_count DESC;
```

---

## Database Location

**Default Path:** `~/.ai-first/audit.db`

**Configuration:**
```python
# In config.py or environment variable
AUDIT_DB_PATH = os.getenv('AI_FIRST_AUDIT_DB', 
                          os.path.expanduser('~/.ai-first/audit.db'))
```

---

## Retention Policy

**Default:** Keep all records indefinitely

**Optional:** Implement auto-cleanup for old records
```sql
-- Delete records older than 90 days
DELETE FROM audit_log 
WHERE timestamp < datetime('now', '-90 days');
```

---

## Performance Considerations

1. **Indexes:** Created on frequently queried fields (session_id, timestamp, capability_id)
2. **Async Writes:** Use a background thread to avoid blocking RuntimeEngine
3. **Batch Inserts:** Buffer multiple records and insert in batches
4. **WAL Mode:** Enable Write-Ahead Logging for better concurrency
   ```sql
   PRAGMA journal_mode=WAL;
   ```

---

## Security

1. **File Permissions:** `audit.db` should be readable only by the user (chmod 600)
2. **Encryption:** Consider using SQLCipher for encrypted database (future enhancement)
3. **Sanitization:** Always mask sensitive data before writing

---

## Future Enhancements

1. **Table: `sessions`** - Track session metadata (start time, end time, client info)
2. **Table: `users`** - User profiles and permissions
3. **Table: `capabilities`** - Capability metadata and usage statistics
4. **Full-Text Search:** Enable FTS5 for searching params_json and result_json

---

## Implementation Checklist

- [ ] Create database initialization script
- [ ] Implement AuditLogger class
- [ ] Integrate with RuntimeEngine
- [ ] Add data sanitization
- [ ] Create export command
- [ ] Write unit tests
- [ ] Document API

---

**Status:** ✅ Schema Design Complete  
**Next Step:** Implement database initialization and AuditLogger class
