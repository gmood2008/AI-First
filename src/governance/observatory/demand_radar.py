"""
Capability Demand Radar API - 能力需求雷达 API

从 CAPABILITY_NOT_FOUND 信号中聚合需求。
无启发式，仅结构化聚合。
"""

from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta

from ..signals.signal_bus import SignalBus
from ..signals.models import SignalType


class DemandRadarAPI:
    """
    Capability Demand Radar API
    
    职责：
    - 从 CAPABILITY_NOT_FOUND 信号聚合需求
    - 识别热点和缺失能力
    - 100% 只读
    """
    
    def __init__(self, signal_bus: SignalBus):
        """
        初始化 Demand Radar API
        
        Args:
            signal_bus: SignalBus 实例
        """
        self.signal_bus = signal_bus
    
    def get_missing_capabilities(
        self,
        window_hours: int = 24,
        min_frequency: int = 1
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/demand/missing-capabilities
        
        获取缺失能力列表
        
        从 CAPABILITY_NOT_FOUND 信号中聚合。
        
        Args:
            window_hours: 时间窗口（小时）
            min_frequency: 最小频率（低于此频率的能力不返回）
        
        Returns:
            缺失能力列表（按频率排序）
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=window_hours)
        
        # 获取所有 CAPABILITY_NOT_FOUND 信号
        signals = self.signal_bus.get_signals(
            signal_type=SignalType.CAPABILITY_NOT_FOUND,
            start_time=start_time,
            end_time=end_time
        )
        
        # 聚合：按 capability_id 统计
        capability_counts = defaultdict(int)
        capability_metadata = defaultdict(list)
        
        for signal in signals:
            capability_id = signal.capability_id
            capability_counts[capability_id] += 1
            capability_metadata[capability_id].append({
                "signal_id": signal.signal_id,
                "timestamp": signal.timestamp.isoformat(),
                "workflow_id": signal.workflow_id,
                "metadata": signal.metadata
            })
        
        # 构建结果列表
        missing_capabilities = []
        for capability_id, count in capability_counts.items():
            if count >= min_frequency:
                missing_capabilities.append({
                    "capability_id": capability_id,
                    "frequency": count,
                    "first_seen": min(m["timestamp"] for m in capability_metadata[capability_id]),
                    "last_seen": max(m["timestamp"] for m in capability_metadata[capability_id]),
                    "signals": capability_metadata[capability_id]
                })
        
        # 按频率降序排序
        missing_capabilities.sort(key=lambda x: x["frequency"], reverse=True)
        
        return missing_capabilities
    
    def get_hotspots(
        self,
        window_hours: int = 24,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/demand/hotspots
        
        获取需求热点
        
        从 CAPABILITY_NOT_FOUND 信号中识别高频需求。
        
        Args:
            window_hours: 时间窗口（小时）
            top_n: 返回前 N 个热点
        
        Returns:
            需求热点列表
        """
        missing_capabilities = self.get_missing_capabilities(
            window_hours=window_hours,
            min_frequency=1
        )
        
        # 返回前 N 个
        return missing_capabilities[:top_n]
    
    def get_demand_summary(
        self,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        GET /governance/demand/summary
        
        获取需求摘要
        
        Args:
            window_hours: 时间窗口（小时）
        
        Returns:
            需求摘要字典
        """
        missing_capabilities = self.get_missing_capabilities(
            window_hours=window_hours,
            min_frequency=1
        )
        
        total_requests = sum(c["frequency"] for c in missing_capabilities)
        unique_capabilities = len(missing_capabilities)
        
        return {
            "window_hours": window_hours,
            "total_requests": total_requests,
            "unique_missing_capabilities": unique_capabilities,
            "top_missing": missing_capabilities[:5]  # 前 5 个
        }
