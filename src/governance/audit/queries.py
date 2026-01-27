"""
Audit Queries - 审计查询

提供高级查询功能，形成治理因果链。
"""

from typing import List, Optional
from datetime import datetime
from pathlib import Path

from .audit_log import AuditLog, AuditEvent


class AuditQueries:
    """
    审计查询 - 高级查询功能
    
    提供跨系统、可追溯的治理因果链查询。
    """
    
    def __init__(self, audit_log: AuditLog):
        """
        初始化审计查询
        
        Args:
            audit_log: AuditLog 实例
        """
        self.audit_log = audit_log
    
    def query_by_capability(
        self,
        capability_id: str,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """
        按能力 ID 查询审计事件
        
        Args:
            capability_id: 能力 ID
            limit: 最大返回数量
        
        Returns:
            审计事件列表（按时间倒序）
        """
        return self.audit_log.get_by_capability(capability_id, limit)
    
    def get_governance_timeline(
        self,
        capability_id: str
    ) -> List[AuditEvent]:
        """
        获取能力的治理时间线
        
        形成完整的治理因果链。
        
        Args:
            capability_id: 能力 ID
        
        Returns:
            审计事件列表（按时间顺序）
        """
        events = self.audit_log.get_by_capability(capability_id)
        # 按时间正序排列（时间线）
        events.sort(key=lambda e: e.timestamp)
        return events
    
    def get_proposal_history(
        self,
        proposal_id: str
    ) -> List[AuditEvent]:
        """
        获取 Proposal 的历史记录
        
        Args:
            proposal_id: Proposal ID
        
        Returns:
            审计事件列表
        """
        return self.audit_log.get_by_proposal(proposal_id)
