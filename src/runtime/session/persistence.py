"""
Session Persistence for AI-First Runtime.

This module provides SQLite-based persistence for session state, including
undo history, so that sessions can survive MCP connection drops and restarts.

Architecture:
- One MCP Connection (stdio process) = One Session ID
- Session ID is generated when MCP server starts
- Undo stack is persisted to SQLite after each operation
- On reconnection, undo history is restored
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class PersistedUndoRecord:
    """
    A serializable undo record for persistence.
    """
    
    session_id: str
    """Session this record belongs to"""
    
    operation_id: str
    """Unique identifier for this operation"""
    
    capability_id: str
    """ID of the capability that was executed"""
    
    timestamp: str
    """ISO timestamp of when operation was executed"""
    
    undo_function: str
    """Name of the undo function (e.g., 'restore_file_from_backup')"""
    
    undo_args: Dict[str, Any]
    """Arguments for the undo function (JSON-serializable)"""
    
    description: str
    """Human-readable description of the operation"""


class SessionPersistence:
    """
    Manages session persistence using SQLite.
    
    Features:
    - Stores undo history per session
    - Automatic cleanup of old sessions
    - Transaction support for atomic operations
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize session persistence.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                connection_info TEXT
            )
        """)
        
        # Undo records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                operation_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                undo_function TEXT NOT NULL,
                undo_args TEXT NOT NULL,
                description TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Index for fast session lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_undo_session 
            ON undo_records(session_id, sequence_number DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, connection_info: Optional[Dict[str, Any]] = None):
        """
        Create a new session.
        
        Args:
            session_id: Unique session identifier
            connection_info: Optional metadata about the connection
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, created_at, last_active, connection_info)
            VALUES (?, ?, ?, ?)
        """, (session_id, now, now, json.dumps(connection_info or {})))
        
        conn.commit()
        conn.close()
    
    def update_session_activity(self, session_id: str):
        """
        Update the last_active timestamp for a session.
        
        Args:
            session_id: Session to update
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE sessions SET last_active = ? WHERE session_id = ?
        """, (now, session_id))
        
        conn.commit()
        conn.close()
    
    def save_undo_record(self, record: PersistedUndoRecord):
        """
        Save an undo record to the database.
        
        Args:
            record: Undo record to save
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get next sequence number for this session
        cursor.execute("""
            SELECT COALESCE(MAX(sequence_number), 0) + 1
            FROM undo_records
            WHERE session_id = ?
        """, (record.session_id,))
        sequence_number = cursor.fetchone()[0]
        
        # Insert record
        cursor.execute("""
            INSERT INTO undo_records 
            (session_id, operation_id, capability_id, timestamp, undo_function, undo_args, description, sequence_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.session_id,
            record.operation_id,
            record.capability_id,
            record.timestamp,
            record.undo_function,
            json.dumps(record.undo_args),
            record.description,
            sequence_number
        ))
        
        conn.commit()
        conn.close()
        
        # Update session activity
        self.update_session_activity(record.session_id)
    
    def load_undo_history(self, session_id: str) -> List[PersistedUndoRecord]:
        """
        Load undo history for a session.
        
        Args:
            session_id: Session to load history for
            
        Returns:
            List of undo records, ordered from oldest to newest
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT operation_id, capability_id, timestamp, undo_function, undo_args, description
            FROM undo_records
            WHERE session_id = ?
            ORDER BY sequence_number ASC
        """, (session_id,))
        
        records = []
        for row in cursor.fetchall():
            records.append(PersistedUndoRecord(
                session_id=session_id,
                operation_id=row[0],
                capability_id=row[1],
                timestamp=row[2],
                undo_function=row[3],
                undo_args=json.loads(row[4]),
                description=row[5]
            ))
        
        conn.close()
        return records
    
    def pop_undo_records(self, session_id: str, count: int = 1) -> List[PersistedUndoRecord]:
        """
        Remove and return the most recent undo records.
        
        Args:
            session_id: Session to pop records from
            count: Number of records to pop
            
        Returns:
            List of popped records, ordered from newest to oldest
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the records to pop
        cursor.execute("""
            SELECT operation_id, capability_id, timestamp, undo_function, undo_args, description, sequence_number
            FROM undo_records
            WHERE session_id = ?
            ORDER BY sequence_number DESC
            LIMIT ?
        """, (session_id, count))
        
        records = []
        sequence_numbers = []
        for row in cursor.fetchall():
            records.append(PersistedUndoRecord(
                session_id=session_id,
                operation_id=row[0],
                capability_id=row[1],
                timestamp=row[2],
                undo_function=row[3],
                undo_args=json.loads(row[4]),
                description=row[5]
            ))
            sequence_numbers.append(row[6])
        
        # Delete the records
        if sequence_numbers:
            placeholders = ','.join('?' * len(sequence_numbers))
            cursor.execute(f"""
                DELETE FROM undo_records
                WHERE session_id = ? AND sequence_number IN ({placeholders})
            """, [session_id] + sequence_numbers)
        
        conn.commit()
        conn.close()
        
        # Update session activity
        self.update_session_activity(session_id)
        
        return records
    
    def get_undo_count(self, session_id: str) -> int:
        """
        Get the number of undo records for a session.
        
        Args:
            session_id: Session to count records for
            
        Returns:
            Number of undo records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM undo_records WHERE session_id = ?
        """, (session_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def cleanup_old_sessions(self, max_age_days: int = 7):
        """
        Remove sessions that haven't been active for a specified period.
        
        Args:
            max_age_days: Maximum age in days for inactive sessions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        
        # Get old session IDs
        cursor.execute("""
            SELECT session_id FROM sessions WHERE last_active < ?
        """, (cutoff_iso,))
        
        old_sessions = [row[0] for row in cursor.fetchall()]
        
        if old_sessions:
            placeholders = ','.join('?' * len(old_sessions))
            
            # Delete undo records
            cursor.execute(f"""
                DELETE FROM undo_records WHERE session_id IN ({placeholders})
            """, old_sessions)
            
            # Delete sessions
            cursor.execute(f"""
                DELETE FROM sessions WHERE session_id IN ({placeholders})
            """, old_sessions)
        
        conn.commit()
        conn.close()
        
        return len(old_sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a session.
        
        Args:
            session_id: Session to get info for
            
        Returns:
            Session info dict, or None if session doesn't exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT created_at, last_active, connection_info
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "session_id": session_id,
                "created_at": row[0],
                "last_active": row[1],
                "connection_info": json.loads(row[2]),
                "undo_count": self.get_undo_count(session_id)
            }
        
        return None
