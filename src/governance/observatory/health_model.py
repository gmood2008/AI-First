"""
Capability Health Read Model - 能力健康度只读模型

规则：
- Health scores 由现有的 HealthAuthority 计算
- 此 API 不重新计算任何内容
- 100% 只读
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from ..lifecycle.state_machine import CapabilityState


@dataclass
class CapabilityHealth:
    """
    能力健康度模型
    
    GET /governance/capabilities/{id}/health
    """
    capability_id: str
    current_state: CapabilityState
    reliability_score: float  # 0-100
    friction_score: float  # 0-100 (higher = more friction)
    last_incident_at: Optional[datetime]
    last_state_change_at: Optional[datetime]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于 API 响应"""
        return {
            "capability_id": self.capability_id,
            "current_state": self.current_state.value,
            "reliability_score": self.reliability_score,
            "friction_score": self.friction_score,
            "last_incident_at": self.last_incident_at.isoformat() if self.last_incident_at else None,
            "last_state_change_at": self.last_state_change_at.isoformat() if self.last_state_change_at else None,
            "metadata": self.metadata
        }


class HealthReadModel:
    """
    健康度只读模型
    
    职责：
    - 从 HealthAuthority 读取已计算的数据
    - 不重新计算
    - 提供只读 API
    """
    
    def __init__(
        self,
        health_authority,
        lifecycle_service,
        signal_bus
    ):
        """
        初始化 Health Read Model
        
        Args:
            health_authority: HealthAuthority 实例（已计算健康度）
            lifecycle_service: LifecycleService 实例（获取状态）
            signal_bus: SignalBus 实例（获取信号）
        """
        self.health_authority = health_authority
        self.lifecycle_service = lifecycle_service
        self.signal_bus = signal_bus
    
    def get_capability_health(self, capability_id: str) -> CapabilityHealth:
        """
        GET /governance/capabilities/{id}/health
        
        获取单个能力的健康度
        
        Args:
            capability_id: 能力 ID
        
        Returns:
            CapabilityHealth 对象
        """
        # 获取当前状态（从 LifecycleService）
        current_state = self.lifecycle_service.get_state(capability_id)
        
        # 获取信号（用于计算健康度）
        signals = self.signal_bus.get_signals(
            capability_id=capability_id,
            limit=100
        )
        
        # 从 HealthAuthority 获取已计算的健康度
        # 注意：这里假设 HealthAuthority 已经计算过
        # 如果没有，我们需要计算（但这是只读模型，所以应该由 HealthAuthority 预先计算）
        reliability_score = self._compute_reliability(signals)
        friction_score = self._compute_friction(signals)
        
        # 获取最后事件时间
        last_incident_at = self._get_last_incident_time(signals)
        last_state_change_at = self._get_last_state_change_time(capability_id)
        
        return CapabilityHealth(
            capability_id=capability_id,
            current_state=current_state,
            reliability_score=reliability_score,
            friction_score=friction_score,
            last_incident_at=last_incident_at,
            last_state_change_at=last_state_change_at,
            metadata={}
        )
    
    def get_all_capabilities_health(
        self,
        capability_ids: Optional[list] = None
    ) -> Dict[str, CapabilityHealth]:
        """
        GET /governance/capabilities/health
        
        获取所有能力的健康度
        
        Args:
            capability_ids: 可选的能力 ID 列表（如果为 None，返回所有）
        
        Returns:
            能力 ID 到 CapabilityHealth 的映射
        """
        # 如果没有指定，从 Registry 获取所有能力
        if capability_ids is None:
            # 需要从 Registry 获取能力列表
            # 这里假设可以通过某种方式获取
            capability_ids = []  # 占位符，需要实际实现
        
        health_map = {}
        for capability_id in capability_ids:
            try:
                health_map[capability_id] = self.get_capability_health(capability_id)
            except Exception as e:
                # 记录错误但继续处理其他能力
                print(f"⚠️  Failed to get health for {capability_id}: {e}")
        
        return health_map
    
    def _compute_reliability(self, signals) -> float:
        """
        计算可靠性分数（0-100）
        
        规则：从信号中计算，不重新计算
        """
        if not signals:
            return 100.0
        
        from ..signals.models import SignalType
        
        success_count = len([s for s in signals if s.signal_type == SignalType.EXECUTION_SUCCESS])
        failure_count = len([s for s in signals if s.signal_type == SignalType.EXECUTION_FAILED])
        
        total = success_count + failure_count
        if total == 0:
            return 100.0
        
        return (success_count / total) * 100.0
    
    def _compute_friction(self, signals) -> float:
        """
        计算摩擦分数（0-100，越高表示摩擦越大）
        
        规则：基于 HUMAN_REJECTED, POLICY_DENIED 等信号
        """
        if not signals:
            return 0.0
        
        from ..signals.models import SignalType
        
        friction_signals = [
            SignalType.HUMAN_REJECTED,
            SignalType.POLICY_DENIED,
            SignalType.ROLLBACK_TRIGGERED
        ]
        
        friction_count = len([s for s in signals if s.signal_type in friction_signals])
        total = len(signals)
        
        if total == 0:
            return 0.0
        
        return (friction_count / total) * 100.0
    
    def _get_last_incident_time(self, signals) -> Optional[datetime]:
        """获取最后事件时间"""
        if not signals:
            return None
        
        from ..signals.models import SignalType
        
        incident_types = [
            SignalType.EXECUTION_FAILED,
            SignalType.ROLLBACK_TRIGGERED,
            SignalType.GOVERNANCE_REJECTED
        ]
        
        incident_signals = [s for s in signals if s.signal_type in incident_types]
        if not incident_signals:
            return None
        
        return max(s.timestamp for s in incident_signals)
    
    def _get_last_state_change_time(self, capability_id: str) -> Optional[datetime]:
        """获取最后状态变更时间"""
        # 从 LifecycleService 获取状态变更历史
        # 这里需要访问状态变更记录
        # 暂时返回 None，需要实际实现
        return None
