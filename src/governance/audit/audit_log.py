"""
Governance Audit Log - 治理账本

形成跨系统、可追溯、不可篡改的治理因果链。
"""

import sqlite3
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import json


class AuditEventType(str, Enum):
    """审计事件类型"""
    LIFECYCLE_CHANGED = "LIFECYCLE_CHANGED"
    PROPOSAL_APPROVED = "PROPOSAL_APPROVED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"
    PROPOSAL_EXECUTED = "PROPOSAL_EXECUTED"
    CAPABILITY_FROZEN = "CAPABILITY_FROZEN"
    CAPABILITY_UNFROZEN = "CAPABILITY_UNFROZEN"


@dataclass
class AuditEvent:
    """
    审计事件 - 治理账本记录
    
    必须记录：
    - Capability 状态变更
    - Proposal 批准 / 拒绝
    - 关联 Signal IDs
    - Pack 信息（pack_name, pack_version）
    - （预留字段）permission_package_id（K-OS）
    """
    event_id: str
    event_type: AuditEventType
    capability_id: str
    timestamp: datetime
    actor: str  # 操作者（admin_id）
    proposal_id: Optional[str]
    signal_ids: List[str]  # 关联的 Signal IDs
    reason: str
    metadata: Dict[str, Any]
    permission_package_id: Optional[str] = None  # 预留：K-OS 集成
    pack_id: Optional[str] = None  # Pack 标识符（如果事件与 pack 相关）
    pack_name: Optional[str] = None  # Pack 名称（向后兼容）
    pack_version: Optional[str] = None  # Pack 版本（如果事件与 pack 相关）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "capability_id": self.capability_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "proposal_id": self.proposal_id,
            "signal_ids": json.dumps(self.signal_ids),
            "reason": self.reason,
            "metadata": json.dumps(self.metadata),
            "permission_package_id": self.permission_package_id,
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "pack_version": self.pack_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """从数据库记录创建"""
        return cls(
            event_id=data["event_id"],
            event_type=AuditEventType(data["event_type"]),
            capability_id=data["capability_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data["actor"],
            proposal_id=data.get("proposal_id"),
            signal_ids=json.loads(data["signal_ids"] or "[]"),
            reason=data["reason"],
            metadata=json.loads(data["metadata"] or "{}"),
            permission_package_id=data.get("permission_package_id"),
            pack_id=data.get("pack_id"),
            pack_name=data.get("pack_name"),
            pack_version=data.get("pack_version")
        )


class AuditLog:
    """
    Governance Audit Log - 治理账本
    
    职责：
    - 记录所有治理操作
    - 形成可追溯的因果链
    - 不可篡改（只追加）
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化 Audit Log
        
        Args:
            db_path: 审计数据库路径
        """
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "governance_audit.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Check if table exists and has pack columns
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='governance_audit'
            """)
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # Check for pack columns and add if missing
                cursor = conn.execute("PRAGMA table_info(governance_audit)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if "pack_id" not in columns:
                    conn.execute("ALTER TABLE governance_audit ADD COLUMN pack_id TEXT")
                if "pack_name" not in columns:
                    conn.execute("ALTER TABLE governance_audit ADD COLUMN pack_name TEXT")
                if "pack_version" not in columns:
                    conn.execute("ALTER TABLE governance_audit ADD COLUMN pack_version TEXT")
                
                conn.commit()
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governance_audit (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    proposal_id TEXT,
                    signal_ids TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    permission_package_id TEXT,
                    pack_id TEXT,
                    pack_name TEXT,
                    pack_version TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_capability_id 
                ON governance_audit(capability_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON governance_audit(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proposal_id 
                ON governance_audit(proposal_id)
            """)
            
            conn.commit()
    
    def append(self, event: AuditEvent) -> None:
        """
        追加审计事件（只追加，不删除）
        
        Args:
            event: 审计事件
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO governance_audit
                (event_id, event_type, capability_id, timestamp, actor, proposal_id,
                 signal_ids, reason, metadata, permission_package_id, pack_id, pack_name, pack_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.event_type.value,
                event.capability_id,
                event.timestamp.isoformat(),
                event.actor,
                event.proposal_id,
                json.dumps(event.signal_ids),
                event.reason,
                json.dumps(event.metadata),
                event.permission_package_id,
                event.pack_id,
                event.pack_name,
                event.pack_version
            ))
            conn.commit()
    
    def get_by_capability(
        self,
        capability_id: str,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """
        按能力 ID 查询审计事件
        
        Args:
            capability_id: 能力 ID
            limit: 最大返回数量
        
        Returns:
            审计事件列表
        """
        query = """
            SELECT * FROM governance_audit 
            WHERE capability_id = ? 
            ORDER BY timestamp DESC
        """
        params = [capability_id]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        events = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            for row in cursor:
                events.append(AuditEvent.from_dict(dict(row)))
        
        return events
    
    def get_by_proposal(
        self,
        proposal_id: str
    ) -> List[AuditEvent]:
        """
        按 Proposal ID 查询审计事件
        
        Args:
            proposal_id: Proposal ID
        
        Returns:
            审计事件列表
        """
        query = """
            SELECT * FROM governance_audit 
            WHERE proposal_id = ? 
            ORDER BY timestamp DESC
        """
        
        events = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (proposal_id,))
            
            for row in cursor:
                events.append(AuditEvent.from_dict(dict(row)))
        
        return events
