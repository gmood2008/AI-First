"""
Signal Timeline API - 信号时间线 API

要求：
- 信号必须严格 append-only
- 排序必须确定性
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..signals.signal_bus import SignalBus
from ..signals.models import SignalType, Signal


class SignalTimelineAPI:
    """
    Signal Timeline API - 信号时间线 API
    
    职责：
    - 提供因果可观测性
    - 严格只读
    - 确定性排序
    """
    
    def __init__(self, signal_bus: SignalBus):
        """
        初始化 Signal Timeline API
        
        Args:
            signal_bus: SignalBus 实例
        """
        self.signal_bus = signal_bus
    
    def get_signals(
        self,
        capability_id: Optional[str] = None,
        signal_type: Optional[SignalType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/signals
        
        获取信号时间线
        
        过滤器：
        - capability_id: 能力 ID
        - signal_type: 信号类型
        - time_range: 时间范围
        - limit: 最大返回数量
        
        Args:
            capability_id: 可选的能力 ID 过滤
            signal_type: 可选的信号类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量
        
        Returns:
            信号列表（按时间排序，确定性）
        """
        signals = self.signal_bus.get_signals(
            capability_id=capability_id,
            signal_type=signal_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # 转换为字典（确定性排序）
        return [self._signal_to_dict(s) for s in signals]
    
    def get_signal_timeline(
        self,
        capability_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/signals/timeline?capability_id={id}
        
        获取能力的信号时间线（因果链）
        
        Args:
            capability_id: 能力 ID
            limit: 最大返回数量
        
        Returns:
            信号时间线（按时间正序，形成因果链）
        """
        signals = self.signal_bus.get_signals(
            capability_id=capability_id,
            limit=limit
        )
        
        # 按时间正序排序（因果链）
        signals_sorted = sorted(signals, key=lambda s: s.timestamp)
        
        return [self._signal_to_dict(s) for s in signals_sorted]
    
    def _signal_to_dict(self, signal: Signal) -> Dict[str, Any]:
        """将 Signal 转换为字典"""
        return {
            "signal_id": signal.signal_id,
            "capability_id": signal.capability_id,
            "workflow_id": signal.workflow_id,
            "signal_type": signal.signal_type.value,
            "severity": signal.severity.value,
            "source": signal.source.value,
            "timestamp": signal.timestamp.isoformat(),
            "metadata": signal.metadata
        }
