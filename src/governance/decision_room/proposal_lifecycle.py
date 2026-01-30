"""
Proposal Lifecycle API - 提案生命周期 API

规则：
- Approval 不直接修改 Runtime
- Approval 产生 Governance Decision Record
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid

from .proposal_model import GovernanceProposalV2, ProposalTypeV2, ProposalStatusV2
from .decision_record import GovernanceDecisionRecord, DecisionType, GovernanceDecisionRecordStore
from ..lifecycle.lifecycle_service import LifecycleService
from ..lifecycle.state_machine import CapabilityState

# Pack Registry integration (optional)
try:
    from registry.pack_registry import PackRegistry, PackState
    PACK_REGISTRY_AVAILABLE = True
except ImportError:
    PACK_REGISTRY_AVAILABLE = False
    PackRegistry = None
    PackState = None


class ProposalLifecycleAPI:
    """
    Proposal Lifecycle API
    
    职责：
    - 管理提案生命周期
    - 处理批准/拒绝
    - 生成决策记录
    """
    
    def __init__(
        self,
        lifecycle_service: LifecycleService,
        decision_store: Optional[GovernanceDecisionRecordStore] = None,
        pack_registry: Optional[PackRegistry] = None
    ):
        """
        初始化 Proposal Lifecycle API
        
        Args:
            lifecycle_service: LifecycleService 实例
            decision_store: 决策记录存储（默认创建）
            pack_registry: PackRegistry 实例（用于 Pack 相关提案）
        """
        self.lifecycle_service = lifecycle_service
        self.decision_store = decision_store or GovernanceDecisionRecordStore()
        self.pack_registry = pack_registry
        self._proposals: Dict[str, GovernanceProposalV2] = {}
        self._init_database()
        self._load_proposals()
    
    def _init_database(self):
        """初始化数据库"""
        db_path = Path.home() / ".ai-first" / "governance_proposals_v2.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governance_proposals_v2 (
                    proposal_id TEXT PRIMARY KEY,
                    proposal_type TEXT NOT NULL,
                    target_capability_id TEXT NOT NULL,
                    triggering_evidence TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON governance_proposals_v2(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_target_capability 
                ON governance_proposals_v2(target_capability_id)
            """)
            
            conn.commit()
        
        self.db_path = db_path
    
    def _load_proposals(self):
        """加载提案"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM governance_proposals_v2")
            
            for row in cursor:
                proposal = GovernanceProposalV2.from_dict(dict(row))
                self._proposals[proposal.proposal_id] = proposal
    
    def create_proposal(
        self,
        proposal_type: ProposalTypeV2,
        target_capability_id: str,
        triggering_evidence: Dict[str, Any],
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GovernanceProposalV2:
        """
        创建提案
        
        Args:
            proposal_type: 提案类型
            target_capability_id: 目标能力 ID
            triggering_evidence: 触发证据
            created_by: 创建者
            metadata: 元数据
        
        Returns:
            GovernanceProposalV2 对象
        """
        proposal_id = f"prop_v2_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}"
        
        proposal = GovernanceProposalV2(
            proposal_id=proposal_id,
            proposal_type=proposal_type,
            target_capability_id=target_capability_id,
            triggering_evidence=triggering_evidence,
            created_at=datetime.now(),
            created_by=created_by,
            status=ProposalStatusV2.PENDING,
            metadata=metadata or {}
        )
        
        self._save_proposal(proposal)
        self._proposals[proposal_id] = proposal
        
        return proposal
    
    def get_proposal(self, proposal_id: str) -> Optional[GovernanceProposalV2]:
        """获取提案"""
        return self._proposals.get(proposal_id)
    
    def get_proposals(
        self,
        status: Optional[ProposalStatusV2] = None,
        target_capability_id: Optional[str] = None
    ) -> List[GovernanceProposalV2]:
        """
        获取提案列表
        
        Args:
            status: 可选的状态过滤
            target_capability_id: 可选的能力 ID 过滤
        
        Returns:
            提案列表
        """
        proposals = list(self._proposals.values())
        
        if status:
            proposals = [p for p in proposals if p.status == status]
        
        if target_capability_id:
            proposals = [p for p in proposals if p.target_capability_id == target_capability_id]
        
        return proposals
    
    def approve_proposal(
        self,
        proposal_id: str,
        decided_by: str,
        rationale: str
    ) -> GovernanceDecisionRecord:
        """
        POST /governance/proposals/{id}/approve
        
        批准提案
        
        规则：
        - 不直接修改 Runtime
        - 产生 Governance Decision Record
        - 根据提案类型执行相应操作
        
        Args:
            proposal_id: 提案 ID
            decided_by: 决策者
            rationale: 理由（必需）
        
        Returns:
            GovernanceDecisionRecord 对象
        
        Raises:
            ValueError: 如果提案不存在或状态无效
        """
        proposal = self.get_proposal(proposal_id)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.status != ProposalStatusV2.PENDING:
            raise ValueError(
                f"Proposal {proposal_id} cannot be approved from status {proposal.status.value}"
            )
        
        # 更新提案状态
        proposal.status = ProposalStatusV2.APPROVED
        self._save_proposal(proposal)
        
        # 执行提案操作（根据类型）
        resulting_state_transition = self._execute_proposal(proposal)
        
        # 创建决策记录
        decision_record = GovernanceDecisionRecord(
            decision_id=f"decision_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            proposal_id=proposal_id,
            decision=DecisionType.APPROVE,
            decided_by=decided_by,
            decided_at=datetime.now(),
            rationale=rationale,
            affected_capabilities=[proposal.target_capability_id],
            resulting_state_transition=resulting_state_transition,
            metadata={
                "proposal_type": proposal.proposal_type.value,
                "created_by": proposal.created_by
            }
        )
        
        # 保存决策记录
        self.decision_store.save(decision_record)
        
        return decision_record
    
    def reject_proposal(
        self,
        proposal_id: str,
        decided_by: str,
        rationale: str
    ) -> GovernanceDecisionRecord:
        """
        POST /governance/proposals/{id}/reject
        
        拒绝提案
        
        Args:
            proposal_id: 提案 ID
            decided_by: 决策者
            rationale: 理由（必需）
        
        Returns:
            GovernanceDecisionRecord 对象
        """
        proposal = self.get_proposal(proposal_id)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.status != ProposalStatusV2.PENDING:
            raise ValueError(
                f"Proposal {proposal_id} cannot be rejected from status {proposal.status.value}"
            )
        
        # 更新提案状态
        proposal.status = ProposalStatusV2.REJECTED
        self._save_proposal(proposal)
        
        # 创建决策记录
        decision_record = GovernanceDecisionRecord(
            decision_id=f"decision_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            proposal_id=proposal_id,
            decision=DecisionType.REJECT,
            decided_by=decided_by,
            decided_at=datetime.now(),
            rationale=rationale,
            affected_capabilities=[proposal.target_capability_id],
            resulting_state_transition=None,
            metadata={
                "proposal_type": proposal.proposal_type.value,
                "created_by": proposal.created_by
            }
        )
        
        # 保存决策记录
        self.decision_store.save(decision_record)
        
        return decision_record
    
    def _execute_proposal(self, proposal: GovernanceProposalV2) -> Optional[Dict[str, Any]]:
        """
        执行提案操作
        
        根据提案类型执行相应操作。
        不直接修改 Runtime，而是通过 LifecycleService。
        
        Args:
            proposal: 提案对象
        
        Returns:
            状态转换信息（如果有）
        """
        capability_id = proposal.target_capability_id
        
        if proposal.proposal_type == ProposalTypeV2.FREEZE:
            # 冻结能力
            self.lifecycle_service.freeze(
                capability_id=capability_id,
                proposal_id=proposal.proposal_id,
                approved_by=proposal.created_by,
                reason=f"Approved proposal {proposal.proposal_id}",
                metadata=proposal.metadata
            )
            
            return {
                "from_state": "ACTIVE",
                "to_state": "FROZEN",
                "capability_id": capability_id
            }
        
        elif proposal.proposal_type == ProposalTypeV2.DEPRECATE:
            # 废弃能力
            self.lifecycle_service.state_machine.transition(
                capability_id=capability_id,
                new_state=CapabilityState.DEPRECATED,
                changed_by=proposal.created_by,
                proposal_id=proposal.proposal_id,
                reason=f"Approved proposal {proposal.proposal_id}",
                metadata=proposal.metadata
            )
            
            return {
                "from_state": self.lifecycle_service.get_state(capability_id).value,
                "to_state": "DEPRECATED",
                "capability_id": capability_id
            }
        
        # Pack-related proposals
        elif PACK_REGISTRY_AVAILABLE and self.pack_registry:
            if proposal.proposal_type == ProposalTypeV2.PACK_CREATE:
                # 创建 Pack：从 metadata 中获取 pack_spec，注册并激活
                pack_spec_dict = proposal.metadata.get("pack_spec")
                if not pack_spec_dict:
                    raise ValueError(f"PACK_CREATE proposal {proposal.proposal_id} missing pack_spec in metadata")
                
                from specs.capability_pack import CapabilityPackSpec
                pack_spec = CapabilityPackSpec.model_validate(pack_spec_dict)
                
                # 注册 Pack（如果尚未注册）
                try:
                    if self.pack_registry:
                        existing_pack = self.pack_registry.get_pack(pack_spec.name, pack_spec.version)
                        if not existing_pack:
                            self.pack_registry.register_pack(
                                pack_spec=pack_spec,
                                registered_by=proposal.created_by,
                                proposal_id=proposal.proposal_id
                            )
                except Exception:
                    # Pack 可能已存在，继续尝试激活
                    pass
                
                # 激活 Pack
                self.pack_registry.update_pack_state(
                    name=pack_spec.name,
                    version=pack_spec.version,
                    new_state=PackState.ACTIVE,
                    changed_by=proposal.created_by,
                    reason=f"Approved PACK_CREATE proposal {proposal.proposal_id}",
                    proposal_id=proposal.proposal_id,
                    approval_id=proposal.proposal_id
                )
                
                return {
                    "from_state": "PROPOSED",
                    "to_state": "ACTIVE",
                    "pack_name": pack_spec.name,
                    "pack_version": pack_spec.version
                }
            
            elif proposal.proposal_type == ProposalTypeV2.PACK_FREEZE:
                # 冻结 Pack：pack_name 在 target_capability_id 字段中
                pack_name = proposal.target_capability_id  # 对于 Pack 提案，这是 pack_name
                pack_version = proposal.metadata.get("pack_version")
                
                self.pack_registry.update_pack_state(
                    name=pack_name,
                    version=pack_version,
                    new_state=PackState.FROZEN,
                    changed_by=proposal.created_by,
                    reason=f"Approved PACK_FREEZE proposal {proposal.proposal_id}",
                    proposal_id=proposal.proposal_id,
                    approval_id=proposal.proposal_id
                )
                
                return {
                    "from_state": "ACTIVE",
                    "to_state": "FROZEN",
                    "pack_name": pack_name,
                    "pack_version": pack_version
                }
        
        # 其他类型（FIX, SPLIT, PROMOTE）需要具体实现
        return None
    
    def _save_proposal(self, proposal: GovernanceProposalV2):
        """保存提案到数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO governance_proposals_v2
                (proposal_id, proposal_type, target_capability_id, triggering_evidence,
                 created_at, created_by, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.proposal_id,
                proposal.proposal_type.value,
                proposal.target_capability_id,
                json.dumps(proposal.triggering_evidence),
                proposal.created_at.isoformat(),
                proposal.created_by,
                proposal.status.value,
                json.dumps(proposal.metadata)
            ))
            conn.commit()
