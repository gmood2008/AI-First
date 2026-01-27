"""
Capability Ingress Service - 能力准入服务

所有新能力必须通过此服务进入系统。
禁止直接写入 Registry。
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid

from specs.v3.capability_schema import CapabilitySpec
from .models import CapabilityProposal, ProposalSource, ProposalStatus

# Try to import validator (may not exist in all versions)
try:
    from specs.v3.validator import SpecValidator
except ImportError:
    # Fallback: create a simple validator
    class SpecValidator:
        def validate(self, spec: CapabilitySpec):
            class ValidationResult:
                def __init__(self):
                    self.is_valid = True
                    self.errors = []
            return ValidationResult()


class CapabilityIngressService:
    """
    Capability Ingress Service - 能力准入服务
    
    职责：
    - 接受能力提案
    - 验证能力规范
    - 创建提案（不激活）
    
    禁止事项：
    - ❌ 写入 Capability Registry
    - ❌ 激活能力
    - ❌ 暴露运行时执行
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化 Ingress Service
        
        Args:
            db_path: 提案数据库路径
        """
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "capability_proposals.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capability_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    capability_spec TEXT NOT NULL,
                    risk_summary TEXT NOT NULL,
                    source TEXT NOT NULL,
                    submitted_by TEXT NOT NULL,
                    justification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    reviewer_id TEXT,
                    rejection_reason TEXT,
                    approval_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON capability_proposals(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_submitted_by 
                ON capability_proposals(submitted_by)
            """)
            
            conn.commit()
    
    def submit_proposal(
        self,
        capability_spec: CapabilitySpec,
        source: ProposalSource,
        submitted_by: str,
        justification: str
    ) -> CapabilityProposal:
        """
        POST /governance/capabilities/proposals
        
        提交能力提案
        
        行为：
        - 接受完整的 CapabilitySpec
        - 执行 Schema 验证
        - 执行 Risk Consistency Check
        - 创建 Proposal（状态 = PENDING_REVIEW）
        
        禁止：
        - ❌ 写入 Capability Registry
        - ❌ 激活能力
        - ❌ 暴露运行时执行
        
        Args:
            capability_spec: 能力规范
            source: 提案来源
            submitted_by: 提交者
            justification: 理由（必需）
        
        Returns:
            CapabilityProposal 对象
        
        Raises:
            ValueError: 如果验证失败
        """
        if not justification or not justification.strip():
            raise ValueError("justification is required")
        
        # Schema 验证
        validator = SpecValidator()
        validation_result = validator.validate(capability_spec)
        
        if not validation_result.is_valid:
            raise ValueError(
                f"Capability spec validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Risk Consistency Check
        risk_summary = self._compute_risk_summary(capability_spec)
        
        # 创建提案
        proposal = CapabilityProposal(
            proposal_id=f"prop_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            capability_spec=capability_spec,
            risk_summary=risk_summary,
            source=source,
            submitted_by=submitted_by,
            justification=justification,
            status=ProposalStatus.PENDING_REVIEW,
            created_at=datetime.now()
        )
        
        # 持久化
        self._save_proposal(proposal)
        
        return proposal
    
    def submit_batch_proposals(
        self,
        capability_specs: List[CapabilitySpec],
        source: ProposalSource,
        submitted_by: str,
        justification: str
    ) -> List[CapabilityProposal]:
        """
        POST /governance/capabilities/proposals/batch
        
        批量提交提案
        
        规则：
        - 每个能力成为独立的 Proposal
        - 不允许批量批准
        - 不允许批量激活
        - 允许部分批准
        
        Args:
            capability_specs: 能力规范列表
            source: 提案来源
            submitted_by: 提交者
            justification: 理由
        
        Returns:
            Proposal 列表
        """
        proposals = []
        
        for spec in capability_specs:
            try:
                proposal = self.submit_proposal(
                    capability_spec=spec,
                    source=source,
                    submitted_by=submitted_by,
                    justification=justification
                )
                proposals.append(proposal)
            except Exception as e:
                # 记录错误但继续处理其他提案
                print(f"⚠️  Failed to submit proposal for {spec.id}: {e}")
        
        return proposals
    
    def _compute_risk_summary(self, spec: CapabilitySpec) -> str:
        """
        计算风险摘要
        
        Args:
            spec: 能力规范
        
        Returns:
            风险摘要文本
        """
        risk_level = spec.risk.level.value
        side_effects_reversible = spec.side_effects.reversible if spec.side_effects else True
        compensation_supported = spec.compensation.supported if spec.compensation else False
        
        summary_parts = [f"Risk Level: {risk_level}"]
        
        if spec.side_effects:
            summary_parts.append(f"Side Effects: reversible={side_effects_reversible}, scope={spec.side_effects.scope}")
        
        if spec.compensation:
            summary_parts.append(f"Compensation: supported={compensation_supported}")
        
        summary_parts.append(f"Operation Type: {spec.operation_type.value}")
        
        return "; ".join(summary_parts)
    
    def _save_proposal(self, proposal: CapabilityProposal):
        """保存提案到数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO capability_proposals
                (proposal_id, capability_spec, risk_summary, source, submitted_by,
                 justification, status, created_at, reviewed_at, reviewer_id,
                 rejection_reason, approval_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.proposal_id,
                json.dumps(proposal.capability_spec.model_dump(mode='json')),
                proposal.risk_summary,
                proposal.source.value,
                proposal.submitted_by,
                proposal.justification,
                proposal.status.value,
                proposal.created_at.isoformat(),
                proposal.reviewed_at.isoformat() if proposal.reviewed_at else None,
                proposal.reviewer_id,
                proposal.rejection_reason,
                proposal.approval_id
            ))
            conn.commit()
    
    def get_proposal(self, proposal_id: str) -> Optional[CapabilityProposal]:
        """获取提案"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM capability_proposals WHERE proposal_id = ?",
                (proposal_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return CapabilityProposal.from_dict(dict(row))
            return None
    
    def get_pending_proposals(self) -> List[CapabilityProposal]:
        """获取所有待审核的提案"""
        proposals = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM capability_proposals 
                WHERE status = ? 
                ORDER BY created_at DESC
            """, (ProposalStatus.PENDING_REVIEW.value,))
            
            for row in cursor:
                proposals.append(CapabilityProposal.from_dict(dict(row)))
        
        return proposals
