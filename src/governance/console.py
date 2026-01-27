"""
Governance Console UI - The Interface

This is the human cockpit of authority, not an observability dashboard.

Required Views:
- Health Leaderboard
- Proposal Queue
- Signal Stream
"""

from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from .signal_bus import SignalBus, SignalType
from .lifecycle_manager import LifecycleManager, CapabilityState
from .health_authority import HealthAuthority, GovernanceProposal, ProposalStatus, ProposalType


class GovernanceConsole:
    """
    Governance Console - The human interface for governance decisions.
    
    This provides views and actions for governance administrators.
    """
    
    def __init__(
        self,
        signal_bus: SignalBus,
        lifecycle_manager: LifecycleManager,
        health_authority: HealthAuthority
    ):
        """
        Initialize Governance Console.
        
        Args:
            signal_bus: SignalBus instance
            lifecycle_manager: LifecycleManager instance
            health_authority: HealthAuthority instance
        """
        self.signal_bus = signal_bus
        self.lifecycle_manager = lifecycle_manager
        self.health_authority = health_authority
    
    def get_health_leaderboard(
        self,
        limit: int = 20,
        window_hours: int = 24
    ) -> List[Dict]:
        """
        Get health leaderboard (top degrading/unhealthy capabilities).
        
        Args:
            limit: Maximum number of capabilities to return
            window_hours: Time window for health evaluation
        
        Returns:
            List of capability health metrics
        """
        # Get all capabilities with lifecycle records
        lifecycles = self.lifecycle_manager.get_all_lifecycles()
        
        leaderboard = []
        
        for capability_id, lifecycle in lifecycles.items():
            # Compute health metrics
            reliability = self.health_authority.compute_reliability_score(
                capability_id, window_hours
            )
            human_intervention = self.health_authority.compute_human_intervention_rate(
                capability_id, window_hours
            )
            rollback_count = self.health_authority.count_rollbacks(
                capability_id, window_hours
            )
            
            # Calculate health score (0-100)
            health_score = reliability - (human_intervention * 0.5) - (rollback_count * 10)
            health_score = max(0, min(100, health_score))
            
            leaderboard.append({
                "capability_id": capability_id,
                "state": lifecycle.state.value,
                "reliability_score": reliability,
                "human_intervention_rate": human_intervention,
                "rollback_count": rollback_count,
                "health_score": health_score,
                "last_changed": lifecycle.changed_at.isoformat()
            })
        
        # Sort by health score (lowest first - most unhealthy)
        leaderboard.sort(key=lambda x: x["health_score"])
        
        return leaderboard[:limit]
    
    def get_proposal_queue(self) -> List[GovernanceProposal]:
        """
        Get proposal queue (pending proposals).
        
        Returns:
            List of pending governance proposals
        """
        return self.health_authority.get_pending_proposals()
    
    def approve_proposal(
        self,
        proposal_id: str,
        admin_id: str,
        reason: str
    ) -> None:
        """
        Approve a governance proposal.
        
        This will:
        1. Update proposal status
        2. Execute the proposal action via LifecycleManager
        3. Emit governance signal
        
        Args:
            proposal_id: Proposal to approve
            admin_id: Admin identity
            reason: Reason for approval
        """
        # Get proposal
        proposals = self.health_authority.get_pending_proposals()
        proposal = next((p for p in proposals if p.proposal_id == proposal_id), None)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found or not pending")
        
        # Update proposal status
        self.health_authority.update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.APPROVED,
            reason=f"Approved by {admin_id}: {reason}"
        )
        
        # Execute proposal action via LifecycleManager
        if proposal.proposal_type == ProposalType.FREEZE:
            self.lifecycle_manager.freeze(
                capability_id=proposal.capability_id,
                changed_by=admin_id,
                reason=f"Approved proposal {proposal_id}: {reason}",
                metadata={"proposal_id": proposal_id}
            )
        elif proposal.proposal_type == ProposalType.UPGRADE_RISK:
            # For now, just transition to DEGRADING
            # In future, could update risk level in spec
            self.lifecycle_manager.transition(
                capability_id=proposal.capability_id,
                new_state=CapabilityState.DEGRADING,
                changed_by=admin_id,
                reason=f"Approved proposal {proposal_id}: {reason}",
                metadata={"proposal_id": proposal_id, "proposal_type": proposal.proposal_type.value}
            )
        # FIX and SPLIT proposals would require more complex actions
        # For now, they remain as proposals for manual handling
    
    def reject_proposal(
        self,
        proposal_id: str,
        admin_id: str,
        reason: str
    ) -> None:
        """
        Reject a governance proposal.
        
        Args:
            proposal_id: Proposal to reject
            admin_id: Admin identity
            reason: Reason for rejection
        """
        self.health_authority.update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.REJECTED,
            reason=f"Rejected by {admin_id}: {reason}"
        )
        
        # Emit governance signal
        proposals = self.health_authority.get_pending_proposals()
        proposal = next((p for p in proposals if p.proposal_id == proposal_id), None)
        if proposal:
            self.signal_bus.emit(
                capability_id=proposal.capability_id,
                signal_type=SignalType.GOVERNANCE_REJECTED,
                severity=SignalSeverity.MEDIUM,
                metadata={
                    "proposal_id": proposal_id,
                    "admin_id": admin_id,
                    "reason": reason,
                    "action": "rejected"
                }
            )
    
    def get_signal_stream(
        self,
        capability_id: Optional[str] = None,
        signal_type: Optional[SignalType] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get signal stream (live governance signals).
        
        Args:
            capability_id: Filter by capability ID
            signal_type: Filter by signal type
            limit: Maximum number of signals
        
        Returns:
            List of signal dictionaries
        """
        signals = self.signal_bus.get_signals(
            capability_id=capability_id,
            signal_type=signal_type,
            limit=limit
        )
        
        return [
            {
                "signal_id": s.signal_id,
                "capability_id": s.capability_id,
                "signal_type": s.signal_type.value,
                "severity": s.severity.value,
                "timestamp": s.timestamp.isoformat(),
                "metadata": s.metadata
            }
            for s in signals
        ]
    
    def freeze_capability(
        self,
        capability_id: str,
        admin_id: str,
        reason: str
    ) -> None:
        """
        Directly freeze a capability (admin action).
        
        Args:
            capability_id: Capability to freeze
            admin_id: Admin identity
            reason: Reason for freezing
        """
        self.lifecycle_manager.freeze(
            capability_id=capability_id,
            changed_by=admin_id,
            reason=reason
        )
        
        # Emit governance signal
        self.signal_bus.emit(
            capability_id=capability_id,
            signal_type=SignalType.GOVERNANCE_REJECTED,
            severity=SignalSeverity.CRITICAL,
            metadata={
                "admin_id": admin_id,
                "reason": reason,
                "action": "freeze"
            }
        )
    
    def unfreeze_capability(
        self,
        capability_id: str,
        admin_id: str,
        reason: str
    ) -> None:
        """
        Unfreeze a capability (admin action).
        
        Args:
            capability_id: Capability to unfreeze
            admin_id: Admin identity
            reason: Reason for unfreezing
        """
        self.lifecycle_manager.unfreeze(
            capability_id=capability_id,
            changed_by=admin_id,
            reason=reason
        )
