"""
Signal Repository - 信号存储层

采用 Event Sourcing / Append-only 模式。
只允许追加，不允许更新或删除。
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .models import Signal, SignalType
import json


class SignalRepository:
    """
    Signal 存储仓库 - 只追加，不删除
    
    这是事实层的存储实现，严格遵守：
    - 只追加（append-only）
    - 不更新（immutable）
    - 不删除（permanent record）
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化 Signal Repository
        
        Args:
            db_path: SQLite 数据库路径（默认: ~/.ai-first/governance_signals.db）
        """
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "governance_signals.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governance_signals (
                    signal_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL,
                    workflow_id TEXT,
                    signal_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            # 创建索引用于查询（但不用于聚合）
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_capability_id 
                ON governance_signals(capability_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signal_type 
                ON governance_signals(signal_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON governance_signals(timestamp)
            """)
            
            conn.commit()
    
    def append(self, signal: Signal) -> None:
        """
        追加 Signal（只追加，不更新）
        
        这是唯一允许写入的方法。
        禁止 update / delete。
        
        Args:
            signal: Signal 对象
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            import json
            conn.execute("""
                INSERT INTO governance_signals 
                (signal_id, capability_id, workflow_id, signal_type, severity, source, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.signal_id,
                signal.capability_id,
                signal.workflow_id,
                signal.signal_type.value,
                signal.severity.value,
                signal.source.value,
                signal.timestamp.isoformat(),
                json.dumps(signal.metadata)
            ))
            conn.commit()
    
    def get_by_capability(
        self,
        capability_id: str,
        signal_type: Optional[SignalType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Signal]:
        """
        按 capability_id 查询 Signal（只读）
        
        Args:
            capability_id: 能力 ID
            signal_type: 可选的信号类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量
        
        Returns:
            Signal 列表
        """
        query = "SELECT * FROM governance_signals WHERE capability_id = ?"
        params = [capability_id]
        
        if signal_type:
            query += " AND signal_type = ?"
            params.append(signal_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        signals = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            for row in cursor:
                signals.append(Signal.from_dict(dict(row)))
        
        return signals
    
    def replay(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Signal]:
        """
        重放所有 Signal（按时间顺序）
        
        用于 Event Sourcing 模式。
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            Signal 列表（按时间顺序）
        """
        query = "SELECT * FROM governance_signals WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp ASC"  # 重放时按时间正序
        
        signals = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            for row in cursor:
                signals.append(Signal.from_dict(dict(row)))
        
        return signals
