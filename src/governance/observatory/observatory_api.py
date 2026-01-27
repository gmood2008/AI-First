"""
V1: Observatory API - 只读治理 API 门面

100% read-only governance observability.
No write endpoints.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime

from .health_model import HealthReadModel
from .risk_distribution import RiskDistributionAPI
from .signal_timeline import SignalTimelineAPI
from .demand_radar import DemandRadarAPI
from ..evaluation.health_authority import HealthAuthority
from ..lifecycle.lifecycle_service import LifecycleService
from ..signals.signal_bus import SignalBus
from ..signals.models import SignalType
from runtime.registry import CapabilityRegistry
from specs.v3.capability_schema import RiskLevel


class ObservatoryAPI:
    """
    V1: Observatory API - 只读治理 API 门面
    
    职责：
    - 提供完整的治理可观测性
    - 100% 只读
    - 不修改任何数据
    """
    
    def __init__(
        self,
        health_authority: HealthAuthority,
        lifecycle_service: LifecycleService,
        signal_bus: SignalBus,
        registry: CapabilityRegistry
    ):
        """
        初始化 Observatory API
        
        Args:
            health_authority: HealthAuthority 实例
            lifecycle_service: LifecycleService 实例
            signal_bus: SignalBus 实例
            registry: CapabilityRegistry 实例
        """
        self.health_read_model = HealthReadModel(
            health_authority=health_authority,
            lifecycle_service=lifecycle_service,
            signal_bus=signal_bus
        )
        self.risk_distribution_api = RiskDistributionAPI(registry=registry)
        self.signal_timeline_api = SignalTimelineAPI(signal_bus=signal_bus)
        self.demand_radar_api = DemandRadarAPI(signal_bus=signal_bus)
    
    # ==================== A1: Capability Health Read Model ====================
    
    def get_capability_health(self, capability_id: str) -> Dict[str, Any]:
        """
        GET /governance/capabilities/{id}/health
        
        获取单个能力的健康度
        """
        health = self.health_read_model.get_capability_health(capability_id)
        return health.to_dict()
    
    def get_all_capabilities_health(self) -> Dict[str, Dict[str, Any]]:
        """
        GET /governance/capabilities/health
        
        获取所有能力的健康度
        """
        # 需要从 Registry 获取所有能力 ID
        # 这里假设可以通过某种方式获取
        # 实际实现需要从 Registry 获取
        health_map = self.health_read_model.get_all_capabilities_health()
        return {cap_id: health.to_dict() for cap_id, health in health_map.items()}
    
    # ==================== A2: Risk & Registry Distribution ====================
    
    def get_risk_distribution(self) -> Dict[str, Any]:
        """
        GET /governance/capabilities/risk-distribution
        
        获取风险分布
        """
        return self.risk_distribution_api.get_risk_distribution()
    
    def get_capabilities_by_risk(self, risk_level: RiskLevel) -> List[str]:
        """
        GET /governance/capabilities/by-risk?risk={level}
        
        按风险级别获取能力列表
        """
        return self.risk_distribution_api.get_capabilities_by_risk(risk_level)
    
    # ==================== A3: Signal Timeline ====================
    
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
        """
        return self.signal_timeline_api.get_signals(
            capability_id=capability_id,
            signal_type=signal_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    def get_signal_timeline(
        self,
        capability_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/signals/timeline?capability_id={id}
        
        获取能力的信号时间线（因果链）
        """
        return self.signal_timeline_api.get_signal_timeline(
            capability_id=capability_id,
            limit=limit
        )
    
    # ==================== A4: Capability Demand Radar ====================
    
    def get_missing_capabilities(
        self,
        window_hours: int = 24,
        min_frequency: int = 1
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/demand/missing-capabilities
        
        获取缺失能力列表
        """
        return self.demand_radar_api.get_missing_capabilities(
            window_hours=window_hours,
            min_frequency=min_frequency
        )
    
    def get_hotspots(
        self,
        window_hours: int = 24,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/demand/hotspots
        
        获取需求热点
        """
        return self.demand_radar_api.get_hotspots(
            window_hours=window_hours,
            top_n=top_n
        )
    
    def get_demand_summary(
        self,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        GET /governance/demand/summary
        
        获取需求摘要
        """
        return self.demand_radar_api.get_demand_summary(
            window_hours=window_hours
        )
