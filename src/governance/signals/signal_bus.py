"""
Signal Bus - 信号总线（事实层入口）

这是 Runtime、Policy、Human Gate 上报事实的唯一入口。
只记录事实，不判断、不聚合、不删除。
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from .models import Signal, SignalType, SignalSeverity, SignalSource
from .repository import SignalRepository


class SignalBus:
    """
    Signal Bus - 事实层入口
    
    职责：
    - 接收来自 Runtime、Policy、Human Gate 的事实报告
    - 只追加 Signal，不判断、不聚合、不删除
    
    禁止事项：
    - ❌ update / delete
    - ❌ 在这里计算健康度
    - ❌ 自动触发生命周期变更
    """
    
    def __init__(self, repository: Optional[SignalRepository] = None):
        """
        初始化 Signal Bus
        
        Args:
            repository: SignalRepository 实例（默认创建新实例）
        """
        self.repository = repository or SignalRepository()
    
    def append(
        self,
        capability_id: str,
        signal_type: SignalType,
        severity: SignalSeverity,
        source: SignalSource,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        追加 Signal（只追加，不判断）
        
        这是 Runtime、Policy、Human Gate 上报事实的唯一方法。
        
        Args:
            capability_id: 能力 ID
            signal_type: 信号类型
            severity: 严重程度
            source: 信号来源
            workflow_id: 可选的工作流 ID
            metadata: 可选的元数据
        
        Returns:
            signal_id: 生成的信号 ID
        """
        signal_id = f"sig_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now()
        metadata = metadata or {}
        
        signal = Signal(
            signal_id=signal_id,
            capability_id=capability_id,
            workflow_id=workflow_id,
            signal_type=signal_type,
            severity=severity,
            source=source,
            timestamp=timestamp,
            metadata=metadata
        )
        
        # 只追加，不判断
        self.repository.append(signal)
        
        return signal_id
    
    def get_signals(
        self,
        capability_id: Optional[str] = None,
        signal_type: Optional[SignalType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> list:
        """
        查询 Signal（只读）
        
        Args:
            capability_id: 可选的能力 ID 过滤
            signal_type: 可选的信号类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量
        
        Returns:
            Signal 列表
        """
        if capability_id:
            return self.repository.get_by_capability(
                capability_id=capability_id,
                signal_type=signal_type,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        else:
            return self.repository.replay(start_time=start_time, end_time=end_time)[:limit] if limit else self.repository.replay(start_time=start_time, end_time=end_time)
