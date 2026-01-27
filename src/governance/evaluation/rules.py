"""
Evaluation Rules - 评估规则

硬编码的评估规则，将 Signal 转换为 Proposal。
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..signals.models import Signal, SignalType
from .proposal import GovernanceProposal, ProposalType, ProposalStatus


class EvaluationRules:
    """
    评估规则 - 硬编码规则
    
    规则：
    - Reliability < 80% → Proposal(FIX)
    - HUMAN_REJECTED 占比 > 50% → Proposal(SPLIT or UPGRADE_RISK)
    - ROLLBACK_TRIGGERED 高频 → Proposal(FREEZE)
    """
    
    @staticmethod
    def compute_reliability(signals: List[Signal]) -> float:
        """
        计算可靠性分数（0-100）
        
        Args:
            signals: Signal 列表
        
        Returns:
            可靠性分数（0-100）
        """
        if not signals:
            return 100.0
        
        success_count = len([s for s in signals if s.signal_type == SignalType.EXECUTION_SUCCESS])
        failure_count = len([s for s in signals if s.signal_type == SignalType.EXECUTION_FAILED])
        
        total = success_count + failure_count
        if total == 0:
            return 100.0
        
        return (success_count / total) * 100.0
    
    @staticmethod
    def compute_human_intervention_rate(signals: List[Signal]) -> float:
        """
        计算人工干预率（0-100）
        
        Args:
            signals: Signal 列表
        
        Returns:
            人工干预率（0-100）
        """
        if not signals:
            return 0.0
        
        human_rejections = len([s for s in signals if s.signal_type == SignalType.HUMAN_REJECTED])
        total_attempts = len([s for s in signals if s.signal_type in [
            SignalType.EXECUTION_SUCCESS,
            SignalType.EXECUTION_FAILED,
            SignalType.HUMAN_REJECTED
        ]])
        
        if total_attempts == 0:
            return 0.0
        
        return (human_rejections / total_attempts) * 100.0
    
    @staticmethod
    def count_rollbacks(signals: List[Signal]) -> int:
        """
        统计回滚次数
        
        Args:
            signals: Signal 列表
        
        Returns:
            回滚次数
        """
        return len([s for s in signals if s.signal_type == SignalType.ROLLBACK_TRIGGERED])
    
    @staticmethod
    def evaluate(
        capability_id: str,
        signals: List[Signal]
    ) -> List[GovernanceProposal]:
        """
        评估 Signal 并生成 Proposal
        
        Args:
            capability_id: 能力 ID
            signals: Signal 列表
        
        Returns:
            Proposal 列表
        """
        proposals = []
        timestamp = datetime.now()
        
        # 规则 1: Reliability < 80% → Proposal(FIX)
        reliability = EvaluationRules.compute_reliability(signals)
        if reliability < 80.0:
            evidence_ids = [s.signal_id for s in signals if s.signal_type in [
                SignalType.EXECUTION_SUCCESS,
                SignalType.EXECUTION_FAILED
            ]]
            
            proposals.append(GovernanceProposal(
                proposal_id=f"prop_{timestamp.timestamp()}_{capability_id}_fix",
                capability_id=capability_id,
                proposal_type=ProposalType.FIX,
                evidence_signal_ids=evidence_ids,
                confidence=1.0 - (reliability / 100.0),  # 可靠性越低，置信度越高
                reason=f"Reliability score {reliability:.1f}% is below 80% threshold",
                created_at=timestamp,
                status=ProposalStatus.PENDING,
                metadata={"threshold": 80.0, "reliability": reliability}
            ))
        
        # 规则 2: HUMAN_REJECTED 占比 > 50% → Proposal(SPLIT or UPGRADE_RISK)
        human_intervention = EvaluationRules.compute_human_intervention_rate(signals)
        if human_intervention > 50.0:
            evidence_ids = [s.signal_id for s in signals if s.signal_type == SignalType.HUMAN_REJECTED]
            
            # 如果可靠性也低，建议 SPLIT；否则建议 UPGRADE_RISK
            if reliability < 70.0:
                proposal_type = ProposalType.SPLIT
                reason = f"High human intervention ({human_intervention:.1f}%) and low reliability ({reliability:.1f}%)"
            else:
                proposal_type = ProposalType.UPGRADE_RISK
                reason = f"High human intervention rate ({human_intervention:.1f}%) suggests risk level may be too low"
            
            proposals.append(GovernanceProposal(
                proposal_id=f"prop_{timestamp.timestamp()}_{capability_id}_intervention",
                capability_id=capability_id,
                proposal_type=proposal_type,
                evidence_signal_ids=evidence_ids,
                confidence=human_intervention / 100.0,
                reason=reason,
                created_at=timestamp,
                status=ProposalStatus.PENDING,
                metadata={"threshold": 50.0, "human_intervention": human_intervention}
            ))
        
        # 规则 3: ROLLBACK_TRIGGERED 高频 → Proposal(FREEZE)
        rollback_count = EvaluationRules.count_rollbacks(signals)
        if rollback_count >= 3:
            evidence_ids = [s.signal_id for s in signals if s.signal_type == SignalType.ROLLBACK_TRIGGERED]
            
            proposals.append(GovernanceProposal(
                proposal_id=f"prop_{timestamp.timestamp()}_{capability_id}_rollback",
                capability_id=capability_id,
                proposal_type=ProposalType.FREEZE,
                evidence_signal_ids=evidence_ids,
                confidence=min(1.0, rollback_count / 10.0),  # 回滚越多，置信度越高
                reason=f"{rollback_count} rollbacks detected (threshold: 3)",
                created_at=timestamp,
                status=ProposalStatus.PENDING,
                metadata={"rollback_threshold": 3, "rollback_count": rollback_count}
            ))
        
        return proposals
