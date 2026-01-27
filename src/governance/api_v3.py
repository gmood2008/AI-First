"""
Governance Platform API v3 - 完整治理系统 API

核心原则（写在代码注释顶部）：

If the Web Console disappears,
the Governance System must still fully function.

所有治理逻辑、状态机、校验、权限判断，必须只存在于 API 层。
UI 只是 API 的一个客户端示例。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .platform_api import GovernancePlatformAPI
from .observatory.observatory_api import ObservatoryAPI
from .decision_room.decision_room_api import DecisionRoomAPI
from .decision_room.proposal_model import ProposalTypeV2, ProposalStatusV2
from .evaluation.health_authority import HealthAuthority
from .lifecycle.lifecycle_service import LifecycleService
from .signals.signal_bus import SignalBus
from runtime.registry import CapabilityRegistry


class GovernanceAPIV3:
    """
    Governance Platform API v3 - 完整治理系统 API
    
    这是治理系统的完整实现。
    UI 只是这个 API 的一个客户端。
    
    原则：
    - API 主权：所有逻辑在 API 层
    - 只读为主，仅签名可写
    - UI 可删除：删除 UI 后，治理系统仍然完整
    """
    
    def __init__(
        self,
        health_authority: Optional[HealthAuthority] = None,
        lifecycle_service: Optional[LifecycleService] = None,
        signal_bus: Optional[SignalBus] = None,
        registry: Optional[CapabilityRegistry] = None
    ):
        """
        初始化 Governance API v3
        
        Args:
            health_authority: HealthAuthority 实例
            lifecycle_service: LifecycleService 实例
            signal_bus: SignalBus 实例
            registry: CapabilityRegistry 实例
        """
        self.platform_api = GovernancePlatformAPI(
            health_authority=health_authority,
            lifecycle_service=lifecycle_service,
            signal_bus=signal_bus,
            registry=registry
        )
        
        # 存储引用以便直接访问
        self.health_authority = self.platform_api.health_authority
        self.lifecycle_service = self.platform_api.lifecycle_service
        self.signal_bus = self.platform_api.signal_bus
        self.registry = self.platform_api.registry
    
    # ==================== Part 1.1: Capability Governance ====================
    
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """
        GET /capabilities
        
        获取所有能力列表
        
        返回：
        - capability_id
        - name
        - description
        - risk_level
        - current_state
        - health_score
        """
        capabilities = []
        
        for capability_id in self.registry.list_capabilities():
            try:
                spec_dict = self.registry.get_spec(capability_id)
                health = self.platform_api.get_capability_health(capability_id)
                state = self.lifecycle_service.get_state(capability_id)
                
                capabilities.append({
                    "capability_id": capability_id,
                    "name": spec_dict.get("name", capability_id),
                    "description": spec_dict.get("description", ""),
                    "risk_level": self._extract_risk_level(spec_dict).value,
                    "current_state": state.value,
                    "health_score": health.get("reliability_score", 100.0)
                })
            except Exception as e:
                # 记录错误但继续处理
                print(f"⚠️  Failed to get capability {capability_id}: {e}")
        
        return capabilities
    
    def get_capability(self, capability_id: str) -> Dict[str, Any]:
        """
        GET /capabilities/{id}
        
        获取单个能力详情
        
        返回完整的能力信息，包括：
        - 规范
        - 健康度
        - 生命周期状态
        - 风险信息
        """
        spec_dict = self.registry.get_spec(capability_id)
        health = self.platform_api.get_capability_health(capability_id)
        state = self.lifecycle_service.get_state(capability_id)
        
        return {
            "capability_id": capability_id,
            "spec": spec_dict,
            "health": health,
            "lifecycle": {
                "current_state": state.value,
                "is_executable": self.lifecycle_service.is_executable(capability_id)
            },
            "risk": {
                "level": self._extract_risk_level(spec_dict).value
            }
        }
    
    def get_capability_health(self, capability_id: str) -> Dict[str, Any]:
        """
        GET /capabilities/{id}/health
        
        获取能力健康度
        
        ⚠️ 注意：Health 由 API 计算，UI 严禁本地计算
        """
        return self.platform_api.get_capability_health(capability_id)
    
    def get_capability_signals(
        self,
        capability_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /capabilities/{id}/signals
        
        获取能力的信号时间线
        
        ⚠️ 注意：Signals 由 API 提供，UI 严禁本地计算
        """
        return self.platform_api.get_signal_timeline(capability_id, limit)
    
    def get_capability_lifecycle(self, capability_id: str) -> Dict[str, Any]:
        """
        GET /capabilities/{id}/lifecycle
        
        获取能力生命周期信息
        
        ⚠️ 注意：Lifecycle 由 API 提供，UI 严禁本地计算
        """
        state = self.lifecycle_service.get_state(capability_id)
        
        return {
            "capability_id": capability_id,
            "current_state": state.value,
            "is_executable": self.lifecycle_service.is_executable(capability_id),
            "state_history": []  # 可以扩展为获取历史记录
        }
    
    # ==================== Part 1.2: Governance Proposals ====================
    
    def get_proposals(
        self,
        status: Optional[str] = None,
        proposal_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /proposals
        
        获取提案列表
        
        查询参数：
        - status: 状态过滤（PENDING / APPROVED / REJECTED）
        - proposal_type: 类型过滤（FIX / SPLIT / FREEZE / etc.）
        """
        proposals = self.platform_api.get_proposals()
        
        if status:
            proposals = [p for p in proposals if p.get("status") == status]
        
        if proposal_type:
            proposals = [p for p in proposals if p.get("proposal_type") == proposal_type]
        
        return proposals
    
    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /proposals/{id}
        
        获取单个提案详情
        
        包含：
        - 提案信息
        - 触发原因（Signal / Health）
        - 证据（metrics + references）
        - 受影响的能力
        - 所需审批者（role-based）
        """
        proposal = self.platform_api.get_proposal(proposal_id)
        
        if not proposal:
            return None
        
        # 获取决策记录（如果有）
        decision_record = self.platform_api.get_decision_record(proposal_id)
        
        return {
            **proposal,
            "decision_record": decision_record
        }
    
    def approve_proposal(
        self,
        proposal_id: str,
        decided_by: str,
        rationale: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST /proposals/{id}/approve
        
        批准提案
        
        要求：
        - decided_by: 决策者（必需）
        - rationale: 理由（必需）
        - role: 角色（可选，用于权限检查）
        
        返回：
        - 决策记录（GDR）
        - 状态变更结果
        """
        # 权限检查（如果实现了 role-based）
        if role and not self._check_approval_permission(role, proposal_id):
            raise PermissionError(f"Role {role} does not have permission to approve this proposal")
        
        # 批准提案
        decision_record = self.platform_api.approve_proposal(
            proposal_id=proposal_id,
            decided_by=decided_by,
            rationale=rationale
        )
        
        return decision_record
    
    def reject_proposal(
        self,
        proposal_id: str,
        decided_by: str,
        rationale: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST /proposals/{id}/reject
        
        拒绝提案
        
        要求：
        - decided_by: 决策者（必需）
        - rationale: 理由（必需）
        - role: 角色（可选，用于权限检查）
        
        返回：
        - 决策记录（GDR）
        """
        # 权限检查
        if role and not self._check_approval_permission(role, proposal_id):
            raise PermissionError(f"Role {role} does not have permission to reject this proposal")
        
        # 拒绝提案
        decision_record = self.platform_api.reject_proposal(
            proposal_id=proposal_id,
            decided_by=decided_by,
            rationale=rationale
        )
        
        return decision_record
    
    # ==================== Part 1.3: Governance Decision Record ====================
    
    def get_decisions(
        self,
        limit: Optional[int] = None,
        capability_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /decisions
        
        获取所有决策记录
        
        查询参数：
        - limit: 最大返回数量
        - capability_id: 能力 ID 过滤
        """
        decisions = self.platform_api.get_all_decisions(limit=limit)
        
        if capability_id:
            decisions = [
                d for d in decisions
                if capability_id in d.get("affected_capabilities", [])
            ]
        
        return decisions
    
    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /decisions/{id}
        
        获取单个决策记录
        
        包含：
        - Who: 决策者
        - When: 决策时间
        - Why: 理由
        - Based on: 基于哪些信号/知识
        - Resulting state change: 结果状态变更
        """
        # 通过 proposal_id 查找决策记录
        # 这里需要扩展决策存储以支持按 decision_id 查询
        decisions = self.platform_api.get_all_decisions()
        
        for decision in decisions:
            if decision.get("decision_id") == decision_id:
                return decision
        
        return None
    
    # ==================== Helper Methods ====================
    
    def _extract_risk_level(self, spec_dict: Dict) -> Any:
        """从 spec_dict 提取风险级别"""
        from specs.v3.capability_schema import RiskLevel
        
        if "risk" in spec_dict:
            risk_data = spec_dict["risk"]
            if isinstance(risk_data, dict):
                level_str = risk_data.get("level")
            else:
                level_str = str(risk_data)
            
            if level_str:
                try:
                    return RiskLevel(level_str)
                except ValueError:
                    pass
        
        return RiskLevel.MEDIUM
    
    def _check_approval_permission(self, role: str, proposal_id: str) -> bool:
        """
        检查审批权限（role-based）
        
        当前实现：简单 mock
        未来可扩展为 SSO 集成
        
        Args:
            role: 角色（admin / reviewer / operator）
            proposal_id: 提案 ID
        
        Returns:
            是否有权限
        """
        # Mock 实现：admin 和 reviewer 有权限
        allowed_roles = ["admin", "reviewer"]
        return role in allowed_roles
