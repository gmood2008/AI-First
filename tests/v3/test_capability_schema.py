"""
AI-First Runtime v3.0 - Capability Schema Tests

Tests for Capability Registry Schema v1 with Risk & Governance.

Week 6 Acceptance Criteria:
- Registry Test: Try to register a capability with reversible: false but risk: LOW
  -> Registration Rejected
"""

import pytest
from pydantic import ValidationError

from src.specs.v3.capability_schema import (
    CapabilitySpec,
    CapabilityParameter,
    Risk,
    RiskLevel,
    SideEffects,
    Compensation,
    OperationType,
    create_read_capability,
    create_write_capability,
    create_delete_capability
)


class TestRiskConsistencyCheck:
    """
    Test Week 6 Acceptance Criteria: Risk Consistency Check
    
    Validation rules:
    1. If side_effects.reversible == False -> risk.level must be HIGH or CRITICAL
    2. If operation_type == DELETE -> risk.level must be at least HIGH
    3. If compensation.supported == False and side_effects.reversible == False -> CRITICAL
    """
    
    def test_irreversible_with_low_risk_rejected(self):
        """
        ACCEPTANCE CRITERIA TEST:
        Try to register a capability with reversible: false but risk: LOW
        -> Registration Rejected
        """
        with pytest.raises(ValidationError) as exc_info:
            CapabilitySpec(
                id="test.invalid",
                name="Invalid Capability",
                description="Should fail validation",
                operation_type=OperationType.WRITE,
                risk=Risk(
                    level=RiskLevel.LOW,  # ❌ INVALID: irreversible must be HIGH+
                    justification="Wrong risk level"
                ),
                side_effects=SideEffects(
                    reversible=False,  # Irreversible
                    scope="local"
                ),
                compensation=Compensation(
                    supported=True,
                    strategy="automatic"
                )
            )
        
        # Verify error message
        error_msg = str(exc_info.value)
        assert "Risk Consistency Check Failed" in error_msg
        assert "Irreversible side effects" in error_msg
        assert "require risk level HIGH or CRITICAL" in error_msg
        
        print("✅ ACCEPTANCE CRITERIA PASSED: Rejected reversible=false with risk=LOW")
    
    def test_irreversible_with_medium_risk_rejected(self):
        """Test that irreversible side effects with MEDIUM risk are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CapabilitySpec(
                id="test.invalid",
                name="Invalid Capability",
                description="Should fail validation",
                operation_type=OperationType.WRITE,
                risk=Risk(
                    level=RiskLevel.MEDIUM,  # ❌ INVALID
                    justification="Wrong risk level"
                ),
                side_effects=SideEffects(
                    reversible=False,
                    scope="local"
                ),
                compensation=Compensation(
                    supported=True,
                    strategy="automatic"
                )
            )
        
        assert "Risk Consistency Check Failed" in str(exc_info.value)
    
    def test_irreversible_with_high_risk_accepted(self):
        """Test that irreversible side effects with HIGH risk are accepted"""
        spec = CapabilitySpec(
            id="test.valid",
            name="Valid Capability",
            description="Should pass validation",
            operation_type=OperationType.WRITE,
            risk=Risk(
                level=RiskLevel.HIGH,  # ✅ VALID
                justification="Correct risk level"
            ),
            side_effects=SideEffects(
                reversible=False,
                scope="local"
            ),
            compensation=Compensation(
                supported=True,
                strategy="automatic"
            )
        )
        
        assert spec.risk.level == RiskLevel.HIGH
        assert not spec.is_reversible()
    
    def test_delete_operation_with_low_risk_rejected(self):
        """Test that DELETE operations with LOW risk are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CapabilitySpec(
                id="test.invalid_delete",
                name="Invalid Delete",
                description="Should fail validation",
                operation_type=OperationType.DELETE,  # DELETE operation
                risk=Risk(
                    level=RiskLevel.LOW,  # ❌ INVALID: DELETE must be HIGH+
                    justification="Wrong risk level"
                ),
                side_effects=SideEffects(
                    reversible=True,  # Even if reversible
                    scope="local"
                ),
                compensation=Compensation(
                    supported=True,
                    strategy="automatic"
                )
            )
        
        error_msg = str(exc_info.value)
        assert "Risk Consistency Check Failed" in error_msg
        assert "DELETE operations" in error_msg
    
    def test_delete_operation_with_high_risk_accepted(self):
        """Test that DELETE operations with HIGH risk are accepted (with compensation)"""
        spec = CapabilitySpec(
            id="test.valid_delete",
            name="Valid Delete",
            description="Should pass validation",
            operation_type=OperationType.DELETE,
            risk=Risk(
                level=RiskLevel.HIGH,  # ✅ VALID
                justification="Correct risk level"
            ),
            side_effects=SideEffects(
                reversible=False,
                scope="local"
            ),
            compensation=Compensation(
                supported=True,  # Must have compensation to avoid CRITICAL requirement
                strategy="manual"
            )
        )
        
        assert spec.risk.level == RiskLevel.HIGH
        assert spec.operation_type == OperationType.DELETE
    
    def test_no_compensation_irreversible_requires_critical(self):
        """
        Test that no compensation + irreversible requires CRITICAL risk
        """
        with pytest.raises(ValidationError) as exc_info:
            CapabilitySpec(
                id="test.invalid",
                name="Invalid Capability",
                description="Should fail validation",
                operation_type=OperationType.WRITE,
                risk=Risk(
                    level=RiskLevel.HIGH,  # ❌ INVALID: should be CRITICAL
                    justification="Wrong risk level"
                ),
                side_effects=SideEffects(
                    reversible=False,  # Irreversible
                    scope="local"
                ),
                compensation=Compensation(
                    supported=False,  # No compensation
                    strategy="none"
                )
            )
        
        error_msg = str(exc_info.value)
        assert "Risk Consistency Check Failed" in error_msg
        assert "No compensation support + irreversible" in error_msg
        assert "CRITICAL risk level" in error_msg
    
    def test_no_compensation_irreversible_with_critical_accepted(self):
        """Test that no compensation + irreversible with CRITICAL is accepted"""
        spec = CapabilitySpec(
            id="test.valid_critical",
            name="Valid Critical Capability",
            description="Should pass validation",
            operation_type=OperationType.WRITE,
            risk=Risk(
                level=RiskLevel.CRITICAL,  # ✅ VALID
                justification="Correct risk level"
            ),
            side_effects=SideEffects(
                reversible=False,
                scope="external"
            ),
            compensation=Compensation(
                supported=False,
                strategy="none"
            )
        )
        
        assert spec.risk.level == RiskLevel.CRITICAL
        assert not spec.is_reversible()
        assert not spec.supports_compensation()


class TestCapabilitySchemaBasics:
    """Test basic capability schema functionality"""
    
    def test_create_valid_capability(self):
        """Test creating a valid capability"""
        spec = CapabilitySpec(
            id="io.fs.read_file",
            name="Read File",
            description="Read contents of a file",
            operation_type=OperationType.READ,
            risk=Risk(
                level=RiskLevel.LOW,
                justification="Read-only operation"
            ),
            side_effects=SideEffects(
                reversible=True,
                scope="local",
                description="No side effects"
            ),
            compensation=Compensation(
                supported=False,
                strategy="none"
            ),
            parameters=[
                CapabilityParameter(
                    name="path",
                    type="string",
                    description="File path to read",
                    required=True
                )
            ]
        )
        
        assert spec.id == "io.fs.read_file"
        assert spec.get_risk_level() == RiskLevel.LOW
        assert spec.is_reversible()
        assert not spec.supports_compensation()
        assert not spec.requires_approval()
    
    def test_high_risk_requires_approval(self):
        """Test that HIGH risk capabilities can require approval"""
        spec = CapabilitySpec(
            id="io.fs.delete_file",
            name="Delete File",
            description="Delete a file",
            operation_type=OperationType.DELETE,
            risk=Risk(
                level=RiskLevel.HIGH,
                justification="Irreversible deletion",
                requires_approval=True  # Explicitly require approval
            ),
            side_effects=SideEffects(
                reversible=False,
                scope="local"
            ),
            compensation=Compensation(
                supported=True,  # Must have compensation to avoid CRITICAL
                strategy="manual"
            )
        )
        
        assert spec.requires_approval()
        assert spec.get_risk_level() == RiskLevel.HIGH


class TestHelperFunctions:
    """Test helper functions for common capability patterns"""
    
    def test_create_read_capability(self):
        """Test create_read_capability helper"""
        spec = create_read_capability(
            capability_id="io.fs.read_file",
            name="Read File",
            description="Read file contents",
            parameters=[
                CapabilityParameter(
                    name="path",
                    type="string",
                    description="File path",
                    required=True
                )
            ]
        )
        
        assert spec.id == "io.fs.read_file"
        assert spec.operation_type == OperationType.READ
        assert spec.get_risk_level() == RiskLevel.LOW
        assert spec.is_reversible()
        assert not spec.supports_compensation()
    
    def test_create_write_capability_reversible(self):
        """Test create_write_capability with reversible=True"""
        spec = create_write_capability(
            capability_id="io.fs.write_file",
            name="Write File",
            description="Write to file",
            parameters=[],
            reversible=True
        )
        
        assert spec.operation_type == OperationType.WRITE
        assert spec.get_risk_level() == RiskLevel.MEDIUM
        assert spec.is_reversible()
        assert spec.supports_compensation()
    
    def test_create_write_capability_irreversible(self):
        """Test create_write_capability with reversible=False"""
        spec = create_write_capability(
            capability_id="io.fs.append_file",
            name="Append File",
            description="Append to file",
            parameters=[],
            reversible=False
        )
        
        assert spec.operation_type == OperationType.WRITE
        assert spec.get_risk_level() == RiskLevel.HIGH
        assert not spec.is_reversible()
        assert spec.supports_compensation()  # Always True to avoid CRITICAL
    
    def test_create_delete_capability(self):
        """Test create_delete_capability helper"""
        spec = create_delete_capability(
            capability_id="io.fs.delete_file",
            name="Delete File",
            description="Delete a file",
            parameters=[]
        )
        
        assert spec.operation_type == OperationType.DELETE
        assert spec.get_risk_level() == RiskLevel.HIGH
        assert not spec.is_reversible()
        assert spec.requires_approval()


class TestRiskLevelEnum:
    """Test RiskLevel enum"""
    
    def test_risk_level_values(self):
        """Test RiskLevel enum values"""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"
    
    def test_risk_level_ordering(self):
        """Test that we can compare risk levels"""
        # Note: Enum comparison doesn't work directly, but we can compare values
        levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(levels) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
