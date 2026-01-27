"""
Governance Decision Record (GDR) - 治理决策记录

每个治理决策必须留下持久、可查询的记录。
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import uuid
import sqlite3
from pathlib import Path


class DecisionType(str, Enum):
    """决策类型"""
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass
class GovernanceDecisionRecord:
    """
    治理决策记录 (GDR)
    
    字段：
    - decision_id
    - proposal_id
    - decision (APPROVE / REJECT)
    - decided_by
    - decided_at
    - rationale (mandatory)
    - affected_capabilities
    - resulting_state_transition (if any)
    """
    decision_id: str
    proposal_id: str
    decision: DecisionType
    decided_by: str
    decided_at: datetime
    rationale: str  # mandatory
    affected_capabilities: List[str]
    resulting_state_transition: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        return {
            "decision_id": self.decision_id,
            "proposal_id": self.proposal_id,
            "decision": self.decision.value,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat(),
            "rationale": self.rationale,
            "affected_capabilities": json.dumps(self.affected_capabilities),
            "resulting_state_transition": json.dumps(self.resulting_state_transition) if self.resulting_state_transition else None,
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceDecisionRecord":
        """从数据库记录创建"""
        return cls(
            decision_id=data["decision_id"],
            proposal_id=data["proposal_id"],
            decision=DecisionType(data["decision"]),
            decided_by=data["decided_by"],
            decided_at=datetime.fromisoformat(data["decided_at"]),
            rationale=data["rationale"],
            affected_capabilities=json.loads(data["affected_capabilities"]),
            resulting_state_transition=json.loads(data["resulting_state_transition"]) if data.get("resulting_state_transition") else None,
            metadata=json.loads(data["metadata"] or "{}")
        )


class GovernanceDecisionRecordStore:
    """
    治理决策记录存储
    
    职责：
    - 持久化决策记录
    - 提供查询接口
    - 保证可审计性
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化决策记录存储
        
        Args:
            db_path: 数据库路径
        """
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "governance_decisions.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governance_decisions (
                    decision_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    decided_by TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    affected_capabilities TEXT NOT NULL,
                    resulting_state_transition TEXT,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proposal_id 
                ON governance_decisions(proposal_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decided_at 
                ON governance_decisions(decided_at)
            """)
            
            conn.commit()
    
    def save(self, record: GovernanceDecisionRecord) -> None:
        """
        保存决策记录
        
        Args:
            record: 决策记录
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO governance_decisions
                (decision_id, proposal_id, decision, decided_by, decided_at,
                 rationale, affected_capabilities, resulting_state_transition, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.decision_id,
                record.proposal_id,
                record.decision.value,
                record.decided_by,
                record.decided_at.isoformat(),
                record.rationale,
                json.dumps(record.affected_capabilities),
                json.dumps(record.resulting_state_transition) if record.resulting_state_transition else None,
                json.dumps(record.metadata)
            ))
            conn.commit()
    
    def get_by_proposal(self, proposal_id: str) -> Optional[GovernanceDecisionRecord]:
        """按提案 ID 获取决策记录"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM governance_decisions WHERE proposal_id = ?",
                (proposal_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return GovernanceDecisionRecord.from_dict(dict(row))
            return None
    
    def get_all(self, limit: Optional[int] = None) -> List[GovernanceDecisionRecord]:
        """获取所有决策记录"""
        records = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM governance_decisions ORDER BY decided_at DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            for row in cursor:
                records.append(GovernanceDecisionRecord.from_dict(dict(row)))
        
        return records
