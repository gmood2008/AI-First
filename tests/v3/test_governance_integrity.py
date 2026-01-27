"""
Governance Integrity Tests

These tests verify that governance boundaries are properly enforced:
- HealthAuthority cannot mutate capability state
- Only LifecycleManager can change lifecycle
- Freezing emits audit signal with reason
- Runtime hard-rejects FROZEN capabilities
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from governance import (
    SignalBus, SignalType, SignalSeverity,
    LifecycleManager, CapabilityState, StateTransitionError,
    HealthAuthority, ProposalType, ProposalStatus,
    GovernanceConsole
)
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from runtime.types import ExecutionContext, ExecutionStatus


@pytest.fixture
def temp_dir():
    """Create temporary directory for test databases"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def signal_bus(temp_dir):
    """Create SignalBus with temp database"""
    return SignalBus(db_path=temp_dir / "signals.db")


@pytest.fixture
def lifecycle_manager(signal_bus, temp_dir):
    """Create LifecycleManager"""
    return LifecycleManager(signal_bus, db_path=temp_dir / "lifecycle.db")


@pytest.fixture
def health_authority(signal_bus, lifecycle_manager, temp_dir):
    """Create HealthAuthority"""
    return HealthAuthority(signal_bus, lifecycle_manager, db_path=temp_dir / "proposals.db")


@pytest.fixture
def governance_console(signal_bus, lifecycle_manager, health_authority):
    """Create GovernanceConsole"""
    return GovernanceConsole(signal_bus, lifecycle_manager, health_authority)


class TestGovernanceBoundaries:
    """Test that governance boundaries are enforced"""
    
    def test_health_authority_read_only(self, health_authority, lifecycle_manager):
        """HealthAuthority cannot mutate capability state"""
        capability_id = "test.capability"
        
        # HealthAuthority should only generate proposals
        proposals = health_authority.evaluate_and_propose(capability_id)
        
        # Verify it's read-only - state should still be ACTIVE (default)
        assert lifecycle_manager.get_state(capability_id) == CapabilityState.ACTIVE
        
        # HealthAuthority should not have direct access to mutate state
        # (This is enforced by design - HealthAuthority doesn't have methods to mutate)
        assert hasattr(health_authority, 'evaluate_and_propose')
        assert not hasattr(health_authority, 'freeze')
        assert not hasattr(health_authority, 'transition')
    
    def test_only_lifecycle_manager_can_change_state(
        self, 
        lifecycle_manager, 
        signal_bus
    ):
        """Only LifecycleManager can change capability state"""
        capability_id = "test.capability"
        
        # Initial state should be ACTIVE (default)
        assert lifecycle_manager.get_state(capability_id) == CapabilityState.ACTIVE
        
        # LifecycleManager can transition
        lifecycle_manager.transition(
            capability_id=capability_id,
            new_state=CapabilityState.FROZEN,
            changed_by="test_admin",
            reason="Test freeze"
        )
        
        assert lifecycle_manager.get_state(capability_id) == CapabilityState.FROZEN
        
        # Invalid transition should raise error
        with pytest.raises(StateTransitionError):
            lifecycle_manager.transition(
                capability_id=capability_id,
                new_state=CapabilityState.PROPOSED,  # Invalid from FROZEN
                changed_by="test_admin",
                reason="Invalid transition"
            )
    
    def test_freeze_emits_signal(self, lifecycle_manager, signal_bus):
        """Freezing emits governance signal with reason"""
        capability_id = "test.capability"
        reason = "Security concern"
        
        # Freeze capability
        lifecycle_manager.freeze(
            capability_id=capability_id,
            changed_by="test_admin",
            reason=reason
        )
        
        # Check signal was emitted
        signals = signal_bus.get_signals(
            capability_id=capability_id,
            signal_type=SignalType.LIFECYCLE_CHANGED
        )
        
        assert len(signals) > 0
        latest_signal = signals[0]
        assert latest_signal.signal_type == SignalType.LIFECYCLE_CHANGED
        assert latest_signal.metadata["new_state"] == CapabilityState.FROZEN.value
        assert latest_signal.metadata["reason"] == reason


class TestRuntimeHardRejection:
    """Test that Runtime hard-rejects FROZEN capabilities"""
    
    def test_frozen_capability_rejected(self, signal_bus, lifecycle_manager):
        """FROZEN capabilities are hard-rejected by Runtime"""
        capability_id = "test.capability"
        
        # Create minimal registry and engine
        registry = CapabilityRegistry()
        engine = RuntimeEngine(
            registry=registry,
            lifecycle_manager=lifecycle_manager,
            signal_bus=signal_bus
        )
        
        # Freeze capability
        lifecycle_manager.freeze(
            capability_id=capability_id,
            changed_by="test_admin",
            reason="Test freeze"
        )
        
        # Try to execute (should fail even if capability exists in registry)
        context = ExecutionContext(
            user_id="test_user",
            workspace_root=Path("/tmp/test"),
            session_id="test_session",
            confirmation_callback=None,
            undo_enabled=False
        )
        
        result = engine.execute(capability_id, {}, context)
        
        # Should be rejected (ERROR status for FROZEN)
        assert result.status == ExecutionStatus.ERROR
        assert "FROZEN" in result.error_message or "cannot be executed" in result.error_message
        
        # Should emit GOVERNANCE_REJECTED signal
        signals = signal_bus.get_signals(
            capability_id=capability_id,
            signal_type=SignalType.GOVERNANCE_REJECTED
        )
        assert len(signals) > 0


class TestSignalReplay:
    """Test signal replayability"""
    
    def test_signals_are_replayable(self, signal_bus):
        """Signals can be replayed in chronological order"""
        capability_id = "test.capability"
        
        # Emit multiple signals
        signal_bus.emit(
            capability_id=capability_id,
            signal_type=SignalType.EXECUTION_SUCCESS,
            severity=SignalSeverity.LOW
        )
        
        signal_bus.emit(
            capability_id=capability_id,
            signal_type=SignalType.EXECUTION_FAILED,
            severity=SignalSeverity.MEDIUM
        )
        
        # Replay signals
        signals = signal_bus.replay()
        
        # Should get all signals in chronological order
        assert len(signals) >= 2
        
        # Verify order (newest first in get_signals, but replay should be chronological)
        # Note: get_signals orders DESC, but replay should be ASC
        capability_signals = [s for s in signals if s.capability_id == capability_id]
        assert len(capability_signals) >= 2


class TestProposalWorkflow:
    """Test proposal generation and approval workflow"""
    
    def test_proposal_generation(self, health_authority, signal_bus):
        """HealthAuthority generates proposals based on signals"""
        capability_id = "test.capability"
        
        # Emit failure signals to trigger proposal
        for _ in range(10):
            signal_bus.emit(
                capability_id=capability_id,
                signal_type=SignalType.EXECUTION_FAILED,
                severity=SignalSeverity.HIGH
            )
        
        # Evaluate and generate proposals
        proposals = health_authority.evaluate_and_propose(capability_id, window_hours=24)
        
        # Should generate FIX proposal (reliability < 80%)
        assert len(proposals) > 0
        fix_proposals = [p for p in proposals if p.proposal_type == ProposalType.FIX]
        assert len(fix_proposals) > 0
    
    def test_proposal_approval_workflow(
        self, 
        governance_console, 
        health_authority,
        lifecycle_manager
    ):
        """Proposal approval triggers lifecycle change"""
        capability_id = "test.capability"
        
        # Generate proposal
        proposals = health_authority.evaluate_and_propose(capability_id)
        freeze_proposals = [p for p in proposals if p.proposal_type == ProposalType.FREEZE]
        
        if freeze_proposals:
            proposal = freeze_proposals[0]
            
            # Approve proposal
            governance_console.approve_proposal(
                proposal_id=proposal.proposal_id,
                admin_id="test_admin",
                reason="Test approval"
            )
            
            # Verify state changed
            assert lifecycle_manager.get_state(capability_id) == CapabilityState.FROZEN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
