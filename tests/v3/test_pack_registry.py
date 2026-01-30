"""
Unit tests for PackRegistry
"""

import pytest
import tempfile
from pathlib import Path

from src.registry.pack_registry import (
    PackRegistry,
    PackRegistryError,
    PackNotFoundError,
    InvalidPackError,
    PackStateTransitionError
)
from src.specs.capability_pack import CapabilityPackSpec, PackIncludes, PackRiskProfile, PackState
from src.specs.v3.capability_schema import RiskLevel
from src.runtime.registry import CapabilityRegistry


class TestPackRegistry:
    """Test PackRegistry functionality"""
    
    def test_register_and_get_pack(self):
        """Test registering and retrieving a pack"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
            
            registry.register_pack(pack_spec, registered_by="test_user")
            
            retrieved = registry.get_pack("test-pack", "1.0.0")
            assert retrieved is not None
            assert retrieved.name == "test-pack"
            assert retrieved.version == "1.0.0"
    
    def test_duplicate_pack_error(self):
        """Test that duplicate pack registration raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
            
            registry.register_pack(pack_spec)
            
            with pytest.raises(PackRegistryError):
                registry.register_pack(pack_spec)
    
    def test_get_pack_latest_version(self):
        """Test getting latest version when version not specified"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            # Register multiple versions
            for version in ["1.0.0", "1.1.0", "2.0.0"]:
                pack_spec = CapabilityPackSpec(
                    pack_id="test-pack",
                    name="test-pack",
                    version=version,
                    description=f"Version {version}",
                    includes=PackIncludes(),
                    risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
                )
                registry.register_pack(pack_spec)
            
            # Get latest (should be 2.0.0)
            latest = registry.get_pack("test-pack")
            assert latest is not None
            assert latest.version == "2.0.0"
    
    def test_pack_state_transitions(self):
        """Test pack state transitions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
            
            registry.register_pack(pack_spec)
            
            # Initial state should be PROPOSED
            assert registry.get_pack_state("test-pack", "1.0.0") == PackState.PROPOSED
            
            # Transition to ACTIVE
            registry.transition_state(
                "test-pack", "1.0.0",
                PackState.ACTIVE,
                changed_by="admin",
                reason="Approved"
            )
            assert registry.get_pack_state("test-pack", "1.0.0") == PackState.ACTIVE
            
            # Transition to FROZEN
            registry.transition_state(
                "test-pack", "1.0.0",
                PackState.FROZEN,
                changed_by="admin",
                reason="Security issue"
            )
            assert registry.get_pack_state("test-pack", "1.0.0") == PackState.FROZEN
    
    def test_invalid_state_transition(self):
        """Test that invalid state transitions raise error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
            
            registry.register_pack(pack_spec)
            
            # Try invalid transition: PROPOSED -> FROZEN (not allowed)
            with pytest.raises(PackStateTransitionError):
                registry.transition_state(
                    "test-pack", "1.0.0",
                    PackState.FROZEN,
                    changed_by="admin",
                    reason="Invalid"
                )
    
    def test_list_packs_with_filters(self):
        """Test listing packs with state and name filters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            # Register multiple packs
            for i, state_name in enumerate(["pack1", "pack2", "pack3"]):
                pack_spec = CapabilityPackSpec(
                    pack_id=state_name,
                    name=state_name,
                    version="1.0.0",
                    description=f"Pack {i}",
                    includes=PackIncludes(),
                    risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
                )
                registry.register_pack(pack_spec)
                
                if i == 1:  # Activate pack2
                    registry.transition_state(
                        state_name, "1.0.0",
                        PackState.ACTIVE,
                        changed_by="admin",
                        reason="Test"
                    )
            
            # List all packs
            all_packs = registry.list_packs()
            assert len(all_packs) == 3
            
            # List only ACTIVE packs
            active_packs = registry.list_packs(state=PackState.ACTIVE)
            assert len(active_packs) == 1
            assert active_packs[0].name == "pack2"
            
            # List by name
            pack1_packs = registry.list_packs(pack_name="pack1")
            assert len(pack1_packs) == 1
            assert pack1_packs[0].name == "pack1"
    
    def test_is_pack_executable(self):
        """Test pack executability check"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path)
            
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
            
            registry.register_pack(pack_spec)
            
            # PROPOSED is executable
            assert registry.is_pack_executable("test-pack", "1.0.0") is True
            
            # ACTIVE is executable
            registry.transition_state(
                "test-pack", "1.0.0",
                PackState.ACTIVE,
                changed_by="admin",
                reason="Test"
            )
            assert registry.is_pack_executable("test-pack", "1.0.0") is True
            
            # FROZEN is not executable
            registry.transition_state(
                "test-pack", "1.0.0",
                PackState.FROZEN,
                changed_by="admin",
                reason="Test"
            )
            assert registry.is_pack_executable("test-pack", "1.0.0") is False

    def test_validate_pack_rejects_empty_workflow_id(self):
        """Test that pack with empty workflow ID in includes.workflows raises InvalidPackError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path, capability_registry=None)
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(capabilities=[], workflows=[""]),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW),
            )
            with pytest.raises(InvalidPackError, match="empty workflow ID"):
                registry.register_pack(pack_spec, registered_by="test_user")

    def test_validate_pack_rejects_whitespace_only_workflow_id(self):
        """Test that pack with whitespace-only workflow ID raises InvalidPackError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PackRegistry(db_path=db_path, capability_registry=None)
            pack_spec = CapabilityPackSpec(
                pack_id="test-pack",
                name="test-pack",
                version="1.0.0",
                description="Test pack",
                includes=PackIncludes(capabilities=[], workflows=["  \t  "]),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW),
            )
            with pytest.raises(InvalidPackError, match="empty workflow ID"):
                registry.register_pack(pack_spec, registered_by="test_user")
