"""
V2: Decision Room API - 人工治理 API 门面

只有 proposal approval / rejection 是可写的。
"""

from typing import List, Optional, Dict, Any

from .proposal_model import GovernanceProposalV2, ProposalTypeV2, ProposalStatusV2
from .decision_record import GovernanceDecisionRecord, DecisionType, GovernanceDecisionRecordStore
from .proposal_lifecycle import ProposalLifecycleAPI
from ..lifecycle.lifecycle_service import LifecycleService


class DecisionRoomAPI:
    """
    V2: Decision Room API - 人工治理 API 门面
    
    职责：
    - 管理提案生命周期
    - 处理批准/拒绝
    - 生成决策记录
    - 与 Runtime 集成
    """
    
    def __init__(
        self,
        lifecycle_service: LifecycleService,
        proposal_lifecycle_api: Optional[ProposalLifecycleAPI] = None,
        decision_store: Optional[GovernanceDecisionRecordStore] = None
    ):
        """
        初始化 Decision Room API
        
        Args:
            lifecycle_service: LifecycleService 实例
            proposal_lifecycle_api: ProposalLifecycleAPI 实例（默认创建）
            decision_store: 决策记录存储（默认创建）
        """
        self.lifecycle_service = lifecycle_service
        
        if decision_store is None:
            decision_store = GovernanceDecisionRecordStore()
        
        if proposal_lifecycle_api is None:
            self.proposal_lifecycle_api = ProposalLifecycleAPI(
                lifecycle_service=lifecycle_service,
                decision_store=decision_store
            )
        else:
            self.proposal_lifecycle_api = proposal_lifecycle_api
        
        self.decision_store = decision_store
    
    # ==================== B2: Proposal Lifecycle APIs ====================
    
    def get_proposals(
        self,
        status: Optional[ProposalStatusV2] = None,
        target_capability_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /governance/proposals
        
        获取提案列表
        
        Args:
            status: 可选的状态过滤
            target_capability_id: 可选的能力 ID 过滤
        
        Returns:
            提案列表（字典格式）
        """
        proposals = self.proposal_lifecycle_api.get_proposals(
            status=status,
            target_capability_id=target_capability_id
        )
        
        return [p.to_dict() for p in proposals]
    
    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /governance/proposals/{id}
        
        获取单个提案
        
        Args:
            proposal_id: 提案 ID
        
        Returns:
            提案字典（如果存在）
        """
        proposal = self.proposal_lifecycle_api.get_proposal(proposal_id)
        
        if proposal:
            return proposal.to_dict()
        return None
    
    def approve_proposal(
        self,
        proposal_id: str,
        decided_by: str,
        rationale: str
    ) -> Dict[str, Any]:
        """
        POST /governance/proposals/{id}/approve
        
        批准提案
        
        规则：
        - 不直接修改 Runtime
        - 产生 Governance Decision Record
        
        Args:
            proposal_id: 提案 ID
            decided_by: 决策者
            rationale: 理由（必需）
        
        Returns:
            决策记录字典
        """
        decision_record = self.proposal_lifecycle_api.approve_proposal(
            proposal_id=proposal_id,
            decided_by=decided_by,
            rationale=rationale
        )
        
        return decision_record.to_dict()
    
    def reject_proposal(
        self,
        proposal_id: str,
        decided_by: str,
        rationale: str
    ) -> Dict[str, Any]:
        """
        POST /governance/proposals/{id}/reject
        
        拒绝提案
        
        Args:
            proposal_id: 提案 ID
            decided_by: 决策者
            rationale: 理由（必需）
        
        Returns:
            决策记录字典
        """
        decision_record = self.proposal_lifecycle_api.reject_proposal(
            proposal_id=proposal_id,
            decided_by=decided_by,
            rationale=rationale
        )
        
        return decision_record.to_dict()
    
    # ==================== B3: Governance Decision Record ====================
    
    def get_decision_record(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /governance/decisions/{proposal_id}
        
        获取决策记录
        
        Args:
            proposal_id: 提案 ID
        
        Returns:
            决策记录字典（如果存在）
        """
        record = self.decision_store.get_by_proposal(proposal_id)
        
        if record:
            return record.to_dict()
        return None
    
    def get_all_decisions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        GET /governance/decisions
        
        获取所有决策记录
        
        Args:
            limit: 最大返回数量
        
        Returns:
            决策记录列表
        """
        records = self.decision_store.get_all(limit=limit)
        return [r.to_dict() for r in records]
    
    # ==================== B4: Lifecycle Enforcement Hook ====================
    
    def create_freeze_proposal(
        self,
        target_capability_id: str,
        triggering_evidence: Dict[str, Any],
        created_by: str
    ) -> Dict[str, Any]:
        """
        创建冻结提案（便捷方法）
        
        Args:
            target_capability_id: 目标能力 ID
            triggering_evidence: 触发证据
            created_by: 创建者
        
        Returns:
            提案字典
        """
        proposal = self.proposal_lifecycle_api.create_proposal(
            proposal_type=ProposalTypeV2.FREEZE,
            target_capability_id=target_capability_id,
            triggering_evidence=triggering_evidence,
            created_by=created_by
        )
        
        return proposal.to_dict()
