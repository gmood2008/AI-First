"""
Lifecycle State Machine - 生命周期状态机

必须严格实现状态转换表。
"""

from enum import Enum
from typing import Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from pathlib import Path


class CapabilityState(str, Enum):
    """Capability 生命周期状态"""
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    DEGRADING = "DEGRADING"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"


# 明确的状态转换表
ALLOWED_TRANSITIONS: Dict[CapabilityState, Set[CapabilityState]] = {
    CapabilityState.PROPOSED: {
        CapabilityState.ACTIVE,
        CapabilityState.DEPRECATED
    },
    CapabilityState.ACTIVE: {
        CapabilityState.DEGRADING,
        CapabilityState.FROZEN,
        CapabilityState.DEPRECATED
    },
    CapabilityState.DEGRADING: {
        CapabilityState.ACTIVE,  # 可以恢复
        CapabilityState.FROZEN,
        CapabilityState.DEPRECATED
    },
    CapabilityState.FROZEN: {
        CapabilityState.ACTIVE,  # 可以解冻
        CapabilityState.DEPRECATED
    },
    CapabilityState.DEPRECATED: set()  # 终端状态
}


@dataclass
class LifecycleRecord:
    """生命周期记录"""
    capability_id: str
    state: CapabilityState
    previous_state: Optional[CapabilityState]
    changed_at: datetime
    changed_by: str
    proposal_id: Optional[str]  # 关联的 Proposal ID
    reason: str
    metadata: Dict


class StateTransitionError(Exception):
    """状态转换错误"""
    pass


class LifecycleStateMachine:
    """
    生命周期状态机
    
    职责：
    - 管理状态转换
    - 验证转换合法性
    - 持久化状态
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化状态机
        
        Args:
            db_path: 生命周期数据库路径
        """
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "lifecycle.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lifecycles: Dict[str, LifecycleRecord] = {}
        self._init_database()
        self._load_lifecycles()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 检查表是否存在
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='capability_lifecycles'
            """)
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # 检查表结构
                cursor = conn.execute("PRAGMA table_info(capability_lifecycles)")
                columns = {row[1] for row in cursor.fetchall()}
                
                # 如果缺少 proposal_id 列，添加它
                if "proposal_id" not in columns:
                    conn.execute("ALTER TABLE capability_lifecycles ADD COLUMN proposal_id TEXT")
                    conn.commit()
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capability_lifecycles (
                    capability_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    previous_state TEXT,
                    changed_at TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    proposal_id TEXT,
                    reason TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state 
                ON capability_lifecycles(state)
            """)
            
            conn.commit()
    
    def _load_lifecycles(self):
        """加载所有生命周期记录"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM capability_lifecycles")
            
            for row in cursor:
                row_dict = dict(row)
                lifecycle = LifecycleRecord(
                    capability_id=row_dict["capability_id"],
                    state=CapabilityState(row_dict["state"]),
                    previous_state=CapabilityState(row_dict["previous_state"]) if row_dict.get("previous_state") else None,
                    changed_at=datetime.fromisoformat(row_dict["changed_at"]),
                    changed_by=row_dict["changed_by"],
                    proposal_id=row_dict.get("proposal_id"),
                    reason=row_dict["reason"],
                    metadata=json.loads(row_dict.get("metadata") or "{}")
                )
                self._lifecycles[lifecycle.capability_id] = lifecycle
    
    def get_state(self, capability_id: str) -> CapabilityState:
        """
        获取当前状态
        
        Args:
            capability_id: 能力 ID
        
        Returns:
            当前状态（默认 ACTIVE）
        """
        if capability_id in self._lifecycles:
            return self._lifecycles[capability_id].state
        return CapabilityState.ACTIVE  # 默认状态
    
    def can_transition(
        self,
        from_state: CapabilityState,
        to_state: CapabilityState
    ) -> bool:
        """
        检查是否可以转换
        
        Args:
            from_state: 源状态
            to_state: 目标状态
        
        Returns:
            是否可以转换
        """
        if from_state == CapabilityState.DEPRECATED:
            return False  # 终端状态
        
        allowed = ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed
    
    def transition(
        self,
        capability_id: str,
        new_state: CapabilityState,
        changed_by: str,
        proposal_id: Optional[str] = None,
        reason: str = "",
        metadata: Optional[Dict] = None
    ) -> None:
        """
        执行状态转换
        
        Args:
            capability_id: 能力 ID
            new_state: 目标状态
            changed_by: 操作者
            proposal_id: 关联的 Proposal ID
            reason: 原因
            metadata: 元数据
        
        Raises:
            StateTransitionError: 如果转换不合法
        """
        current_state = self.get_state(capability_id)
        
        # 检查转换合法性
        if not self.can_transition(current_state, new_state):
            raise StateTransitionError(
                f"Invalid transition from {current_state.value} to {new_state.value} "
                f"for capability {capability_id}. "
                f"Allowed transitions: {[s.value for s in ALLOWED_TRANSITIONS.get(current_state, set())]}"
            )
        
        # 创建记录
        lifecycle = LifecycleRecord(
            capability_id=capability_id,
            state=new_state,
            previous_state=current_state,
            changed_at=datetime.now(),
            changed_by=changed_by,
            proposal_id=proposal_id,
            reason=reason,
            metadata=metadata or {}
        )
        
        # 持久化
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO capability_lifecycles
                (capability_id, state, previous_state, changed_at, changed_by, proposal_id, reason, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                capability_id,
                new_state.value,
                current_state.value if current_state != CapabilityState.ACTIVE or capability_id in self._lifecycles else None,
                lifecycle.changed_at.isoformat(),
                changed_by,
                proposal_id,
                reason,
                json.dumps(metadata or {})
            ))
            conn.commit()
        
        # 更新内存缓存
        self._lifecycles[capability_id] = lifecycle
    
    def get_all_lifecycles(self) -> Dict[str, LifecycleRecord]:
        """获取所有生命周期记录"""
        return self._lifecycles.copy()
