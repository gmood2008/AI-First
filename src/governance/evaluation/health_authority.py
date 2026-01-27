"""
Health Authority - 健康权威（裁决生成层）

将 Signal 转换为 GovernanceProposal。
只能"建议"，不能"执行"。
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import json

from ..signals.signal_bus import SignalBus
from ..signals.models import SignalType
from .proposal import GovernanceProposal, ProposalStatus
from .rules import EvaluationRules


class HealthAuthority:
    """
    Health Authority - 裁决生成层
    
    职责：
    - 读取 Signal（只读）
    - 生成 GovernanceProposal（只建议，不执行）
    
    禁止事项：
    - ❌ 不能改变 Capability 状态
    - ❌ 不能直接调用 Lifecycle Service
    - ❌ 不能接触 Registry
    """
    
    def __init__(
        self,
        signal_bus: SignalBus,
        db_path: Optional[Path] = None
    ):
        """
        初始化 Health Authority
        
        Args:
            signal_bus: SignalBus 实例
            db_path: 提案数据库路径
        """
        self.signal_bus = signal_bus
        
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "governance_proposals.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化提案数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 检查表是否存在
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='governance_proposals'
            """)
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # 检查表结构
                cursor = conn.execute("PRAGMA table_info(governance_proposals)")
                columns = {row[1]: row for row in cursor.fetchall()}
                
                # 如果表结构不匹配，删除旧表重新创建
                required_columns = {"proposal_id", "capability_id", "proposal_type", 
                                   "evidence_signal_ids", "confidence", "reason", 
                                   "created_at", "status", "metadata"}
                existing_columns = set(columns.keys())
                
                if not required_columns.issubset(existing_columns) or "trigger_metrics" in existing_columns:
                    # 删除旧表
                    conn.execute("DROP TABLE IF EXISTS governance_proposals")
                    conn.commit()
                    table_exists = False
            
            if not table_exists:
                conn.execute("""
                    CREATE TABLE governance_proposals (
                        proposal_id TEXT PRIMARY KEY,
                        capability_id TEXT NOT NULL,
                        proposal_type TEXT NOT NULL,
                        evidence_signal_ids TEXT NOT NULL,
                        confidence REAL NOT NULL DEFAULT 0.0,
                        reason TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT NOT NULL
                    )
                """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_capability_id 
                ON governance_proposals(capability_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON governance_proposals(status)
            """)
            
            conn.commit()
    
    def evaluate(
        self,
        capability_id: str,
        window_hours: int = 24
    ) -> List[GovernanceProposal]:
        """
        评估能力并生成 Proposal
        
        这是裁决生成层的核心方法。
        只生成 Proposal，不执行。
        
        Args:
            capability_id: 能力 ID
            window_hours: 评估时间窗口（小时）
        
        Returns:
            Proposal 列表
        """
        # 读取 Signal（只读）
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=window_hours)
        
        signals = self.signal_bus.get_signals(
            capability_id=capability_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # 使用规则生成 Proposal
        proposals = EvaluationRules.evaluate(capability_id, signals)
        
        # 持久化 Proposal
        for proposal in proposals:
            self._save_proposal(proposal)
        
        return proposals
    
    def _save_proposal(self, proposal: GovernanceProposal):
        """保存 Proposal 到数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO governance_proposals
                (proposal_id, capability_id, proposal_type, evidence_signal_ids,
                 confidence, reason, created_at, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.proposal_id,
                proposal.capability_id,
                proposal.proposal_type.value,
                json.dumps(proposal.evidence_signal_ids),
                proposal.confidence,
                proposal.reason,
                proposal.created_at.isoformat(),
                proposal.status.value,
                json.dumps(proposal.metadata)
            ))
            conn.commit()
    
    def get_pending_proposals(self) -> List[GovernanceProposal]:
        """获取所有待处理的 Proposal"""
        proposals = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM governance_proposals 
                WHERE status = ? 
                ORDER BY created_at DESC
            """, (ProposalStatus.PENDING.value,))
            
            for row in cursor:
                proposals.append(GovernanceProposal.from_dict(dict(row)))
        
        return proposals
    
    def update_proposal_status(
        self,
        proposal_id: str,
        status: ProposalStatus,
        reason: Optional[str] = None
    ):
        """
        更新 Proposal 状态（由 Console 调用）
        
        这仍然不执行提案，只是更新状态。
        执行由 Lifecycle Service 负责。
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            update_query = "UPDATE governance_proposals SET status = ?"
            params = [status.value]
            
            if reason:
                update_query += ", reason = ?"
                params.append(reason)
            
            update_query += " WHERE proposal_id = ?"
            params.append(proposal_id)
            
            conn.execute(update_query, params)
            conn.commit()
