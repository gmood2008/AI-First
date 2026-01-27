"""
AI-First Governance Platform API - 统一平台 API 门面

整合 V1 (Observatory) 和 V2 (Decision Room) APIs。
"""

from typing import Optional

from .observatory.observatory_api import ObservatoryAPI
from .decision_room.decision_room_api import DecisionRoomAPI
from .evaluation.health_authority import HealthAuthority
from .lifecycle.lifecycle_service import LifecycleService
from .signals.signal_bus import SignalBus
from runtime.registry import CapabilityRegistry


class GovernancePlatformAPI:
    """
    AI-First Governance Platform API - 统一平台 API 门面
    
    整合：
    - V1: Observatory APIs (只读治理)
    - V2: Decision Room APIs (人工治理)
    
    原则：
    - API 主权：每个治理能力都通过 API 暴露
    - 只读为主，仅签名可写
    - 不绕过 Runtime 安全措施
    - 审计是强制性的
    """
    
    def __init__(
        self,
        health_authority: Optional[HealthAuthority] = None,
        lifecycle_service: Optional[LifecycleService] = None,
        signal_bus: Optional[SignalBus] = None,
        registry: Optional[CapabilityRegistry] = None
    ):
        """
        初始化 Governance Platform API
        
        Args:
            health_authority: HealthAuthority 实例（默认创建）
            lifecycle_service: LifecycleService 实例（默认创建）
            signal_bus: SignalBus 实例（默认创建）
            registry: CapabilityRegistry 实例（默认创建）
        """
        # 导入并初始化组件
        if signal_bus is None:
            from .signals.signal_bus import SignalBus
            signal_bus = SignalBus()
        
        if health_authority is None:
            health_authority = HealthAuthority(signal_bus)
        
        if lifecycle_service is None:
            from .lifecycle.state_machine import LifecycleStateMachine
            from .lifecycle.lifecycle_service import LifecycleService
            state_machine = LifecycleStateMachine()
            lifecycle_service = LifecycleService(state_machine, signal_bus)
        
        if registry is None:
            registry = CapabilityRegistry(governance_enforced=True)
        
        # 初始化 V1 和 V2 APIs
        self.v1_observatory = ObservatoryAPI(
            health_authority=health_authority,
            lifecycle_service=lifecycle_service,
            signal_bus=signal_bus,
            registry=registry
        )
        
        self.v2_decision_room = DecisionRoomAPI(
            lifecycle_service=lifecycle_service
        )
        
        # 存储引用
        self.health_authority = health_authority
        self.lifecycle_service = lifecycle_service
        self.signal_bus = signal_bus
        self.registry = registry
    
    # ==================== V1: Observatory APIs (只读) ====================
    
    def get_capability_health(self, capability_id: str) -> dict:
        """GET /governance/capabilities/{id}/health"""
        return self.v1_observatory.get_capability_health(capability_id)
    
    def get_all_capabilities_health(self) -> dict:
        """GET /governance/capabilities/health"""
        return self.v1_observatory.get_all_capabilities_health()
    
    def get_risk_distribution(self) -> dict:
        """GET /governance/capabilities/risk-distribution"""
        return self.v1_observatory.get_risk_distribution()
    
    def get_capabilities_by_risk(self, risk_level: str) -> list:
        """GET /governance/capabilities/by-risk?risk={level}"""
        from specs.v3.capability_schema import RiskLevel
        return self.v1_observatory.get_capabilities_by_risk(RiskLevel(risk_level))
    
    def get_signals(self, **kwargs) -> list:
        """GET /governance/signals"""
        return self.v1_observatory.get_signals(**kwargs)
    
    def get_signal_timeline(self, capability_id: str, limit: Optional[int] = None) -> list:
        """GET /governance/signals/timeline?capability_id={id}"""
        return self.v1_observatory.get_signal_timeline(capability_id, limit)
    
    def get_missing_capabilities(self, window_hours: int = 24, min_frequency: int = 1) -> list:
        """GET /governance/demand/missing-capabilities"""
        return self.v1_observatory.get_missing_capabilities(window_hours, min_frequency)
    
    def get_hotspots(self, window_hours: int = 24, top_n: int = 10) -> list:
        """GET /governance/demand/hotspots"""
        return self.v1_observatory.get_hotspots(window_hours, top_n)
    
    def get_demand_summary(self, window_hours: int = 24) -> dict:
        """GET /governance/demand/summary"""
        return self.v1_observatory.get_demand_summary(window_hours)
    
    # ==================== V2: Decision Room APIs (人工治理) ====================
    
    def get_proposals(self, **kwargs) -> list:
        """GET /governance/proposals"""
        return self.v2_decision_room.get_proposals(**kwargs)
    
    def get_proposal(self, proposal_id: str) -> Optional[dict]:
        """GET /governance/proposals/{id}"""
        return self.v2_decision_room.get_proposal(proposal_id)
    
    def approve_proposal(self, proposal_id: str, decided_by: str, rationale: str) -> dict:
        """POST /governance/proposals/{id}/approve"""
        return self.v2_decision_room.approve_proposal(proposal_id, decided_by, rationale)
    
    def reject_proposal(self, proposal_id: str, decided_by: str, rationale: str) -> dict:
        """POST /governance/proposals/{id}/reject"""
        return self.v2_decision_room.reject_proposal(proposal_id, decided_by, rationale)
    
    def get_decision_record(self, proposal_id: str) -> Optional[dict]:
        """GET /governance/decisions/{proposal_id}"""
        return self.v2_decision_room.get_decision_record(proposal_id)
    
    def get_all_decisions(self, limit: Optional[int] = None) -> list:
        """GET /governance/decisions"""
        return self.v2_decision_room.get_all_decisions(limit)
