"""
Audit Logger for AI-First Runtime v2.0

Provides enterprise-grade compliance logging with:
- SQLite persistence
- Data sanitization
- Async writes
- Query utilities
"""

import sqlite3
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import threading
from queue import Queue


class AuditLogger:
    """
    Enterprise audit logger for AI-First Runtime.
    
    Records all runtime actions to SQLite database for compliance,
    debugging, and accountability.
    """
    
    # Sensitive field patterns (case-insensitive)
    SENSITIVE_PATTERNS = [
        r'.*token.*',
        r'.*key.*',
        r'.*password.*',
        r'.*secret.*',
        r'.*credential.*',
        r'.*auth.*',
    ]
    
    REDACTED = "***REDACTED***"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize audit logger.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.ai-first/audit.db
        """
        if db_path is None:
            db_path = os.path.expanduser('~/.ai-first/audit.db')
        
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        
        # Async write queue
        self._shutdown = False  # MUST be set before starting thread
        self._write_queue: Queue = Queue()
        self._writer_thread = threading.Thread(target=self._write_worker, daemon=True)
        self._writer_thread.start()
    
    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Create audit_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                params_json TEXT,
                result_json TEXT,
                status TEXT NOT NULL,
                side_effects TEXT,
                requires_confirmation BOOLEAN DEFAULT 0,
                was_confirmed BOOLEAN DEFAULT NULL,
                undo_available BOOLEAN DEFAULT 0,
                was_undone BOOLEAN DEFAULT 0,
                undo_record_id INTEGER,
                error_message TEXT,
                duration_ms INTEGER,
                FOREIGN KEY (undo_record_id) REFERENCES audit_log(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON audit_log(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_capability_id ON audit_log(capability_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON audit_log(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON audit_log(user_id)")
        
        conn.commit()
        conn.close()
        
        # Set file permissions (readable only by user)
        os.chmod(self.db_path, 0o600)
    
    def _sanitize_data(self, data: Any) -> Any:
        """
        Recursively sanitize sensitive data.
        
        Args:
            data: Data to sanitize (dict, list, or primitive)
        
        Returns:
            Sanitized copy of data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Check if key matches sensitive pattern
                is_sensitive = any(
                    re.match(pattern, key, re.IGNORECASE)
                    for pattern in self.SENSITIVE_PATTERNS
                )
                
                if is_sensitive and isinstance(value, str):
                    sanitized[key] = self.REDACTED
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        
        else:
            return data
    
    def log_action(
        self,
        session_id: str,
        user_id: str,
        capability_id: str,
        action_type: str,
        params: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        status: str = "success",
        side_effects: Optional[List[str]] = None,
        requires_confirmation: bool = False,
        was_confirmed: Optional[bool] = None,
        undo_available: bool = False,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        """
        Log an action to the audit database (async).
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            capability_id: Capability being executed
            action_type: Type of action (execute, undo, confirm, deny)
            params: Input parameters
            result: Output result
            status: Execution status (success, failure, denied, pending)
            side_effects: List of side effects
            requires_confirmation: Whether action required confirmation
            was_confirmed: Whether user confirmed (None if not required)
            undo_available: Whether action can be undone
            error_message: Error message if status=failure
            duration_ms: Execution time in milliseconds
        
        Returns:
            Record ID (will be available after async write completes)
        """
        # Sanitize params and result
        sanitized_params = self._sanitize_data(params) if params else None
        sanitized_result = self._sanitize_data(result) if result else None
        
        # Prepare record
        record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'session_id': session_id,
            'user_id': user_id,
            'capability_id': capability_id,
            'action_type': action_type,
            'params_json': json.dumps(sanitized_params) if sanitized_params else None,
            'result_json': json.dumps(sanitized_result) if sanitized_result else None,
            'status': status,
            'side_effects': ','.join(side_effects) if side_effects else None,
            'requires_confirmation': 1 if requires_confirmation else 0,
            'was_confirmed': 1 if was_confirmed else (0 if was_confirmed is False else None),
            'undo_available': 1 if undo_available else 0,
            'was_undone': 0,
            'undo_record_id': None,
            'error_message': error_message,
            'duration_ms': duration_ms,
        }
        
        # Queue for async write
        self._write_queue.put(record)
        
        # Return placeholder ID (actual ID will be assigned after write)
        return -1
    
    def mark_undone(self, original_record_id: int, undo_record_id: int):
        """
        Mark an action as undone.
        
        Args:
            original_record_id: ID of the original action
            undo_record_id: ID of the undo action
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE audit_log
            SET was_undone = 1, undo_record_id = ?
            WHERE id = ?
        """, (undo_record_id, original_record_id))
        
        conn.commit()
        conn.close()
    
    def _write_worker(self):
        """Background worker for async writes."""
        while not self._shutdown:
            try:
                record = self._write_queue.get(timeout=1)
                if record is None:  # Shutdown signal
                    break
                
                self._write_record(record)
                self._write_queue.task_done()
            
            except Exception:
                # Queue.get timeout or write error
                continue
    
    def _write_record(self, record: Dict[str, Any]):
        """Write a single record to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_log (
                timestamp, session_id, user_id, capability_id, action_type,
                params_json, result_json, status, side_effects,
                requires_confirmation, was_confirmed, undo_available, was_undone,
                undo_record_id, error_message, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record['timestamp'],
            record['session_id'],
            record['user_id'],
            record['capability_id'],
            record['action_type'],
            record['params_json'],
            record['result_json'],
            record['status'],
            record['side_effects'],
            record['requires_confirmation'],
            record['was_confirmed'],
            record['undo_available'],
            record['was_undone'],
            record['undo_record_id'],
            record['error_message'],
            record['duration_ms'],
        ))
        
        conn.commit()
        conn.close()
    
    def query(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        capability_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit log with filters.
        
        Args:
            session_id: Filter by session
            user_id: Filter by user
            capability_id: Filter by capability
            status: Filter by status
            limit: Maximum number of records to return
        
        Returns:
            List of audit records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if capability_id:
            query += " AND capability_id = ?"
            params.append(capability_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Summary dictionary with counts and statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                COUNT(*) as total_actions,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END) as failure_count,
                SUM(CASE WHEN status = 'denied' THEN 1 ELSE 0 END) as denied_count,
                SUM(CASE WHEN was_undone = 1 THEN 1 ELSE 0 END) as undone_count,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time
            FROM audit_log
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total_actions': row[0],
            'success_count': row[1],
            'failure_count': row[2],
            'denied_count': row[3],
            'undone_count': row[4],
            'start_time': row[5],
            'end_time': row[6],
        }
    
    def shutdown(self):
        """Gracefully shutdown the audit logger."""
        self._shutdown = True
        self._write_queue.put(None)  # Signal shutdown
        self._writer_thread.join(timeout=5)
