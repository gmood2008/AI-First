"""
Unit tests for CapabilityPackSpec validation
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.specs.capability_pack import (
    CapabilityPackSpec,
    PackIncludes,
    PackRiskProfile,
    PackGovernance,
    PackState
)
from src.specs.v3.capability_schema import RiskLevel


class TestCapabilityPackSpec:
    """Test CapabilityPackSpec validation"""
    
    def test_valid_pack_spec(self):
        """Test creating a valid pack spec"""
        spec = CapabilityPackSpec(
            name="financial-analyst",
            version="1.0.0",
            description="Financial analysis capabilities",
            includes=PackIncludes(
                capabilities=["io.pdf.extract_table", "math.pandas.calculate"],
                workflows=["financial_report"]
            ),
            risk_profile=PackRiskProfile(
                max_risk=RiskLevel.HIGH,
                requires_human_approval=True
            ),
            governance=PackGovernance(
                requires_approval=True,
                approval_roles=["admin", "security"]
            )
        )
        
        assert spec.name == "financial-analyst"
        assert spec.version == "1.0.0"
        assert len(spec.includes.capabilities) == 2
        assert spec.risk_profile.max_risk == RiskLevel.HIGH
        assert spec.governance.requires_approval is True
    
    def test_invalid_name_empty(self):
        """Test that empty name is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityPackSpec(
                name="",
                version="1.0.0",
                description="Test",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
        assert "cannot be empty" in str(exc_info.value)
    
    def test_invalid_name_with_spaces(self):
        """Test that name with spaces is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityPackSpec(
                name="financial analyst",
                version="1.0.0",
                description="Test",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
        assert "cannot contain spaces" in str(exc_info.value)
    
    def test_invalid_version_format(self):
        """Test that invalid version format is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityPackSpec(
                name="test-pack",
                version="1.0",
                description="Test",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
        assert "semantic versioning format" in str(exc_info.value)
    
    def test_invalid_version_non_numeric(self):
        """Test that non-numeric version parts are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CapabilityPackSpec(
                name="test-pack",
                version="1.0.a",
                description="Test",
                includes=PackIncludes(),
                risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
            )
        assert "must be integers" in str(exc_info.value)
    
    def test_created_at_auto_set(self):
        """Test that created_at is automatically set if not provided"""
        spec = CapabilityPackSpec(
            name="test-pack",
            version="1.0.0",
            description="Test",
            includes=PackIncludes(),
            risk_profile=PackRiskProfile(max_risk=RiskLevel.LOW)
        )
        
        assert spec.created_at is not None
        assert isinstance(spec.created_at, datetime)
    
    def test_serialization(self):
        """Test pack spec serialization"""
        spec = CapabilityPackSpec(
            name="test-pack",
            version="1.0.0",
            description="Test",
            includes=PackIncludes(
                capabilities=["cap1", "cap2"]
            ),
            risk_profile=PackRiskProfile(max_risk=RiskLevel.MEDIUM)
        )
        
        # Convert to dict
        spec_dict = spec.to_dict()
        assert spec_dict["name"] == "test-pack"
        assert spec_dict["version"] == "1.0.0"
        assert len(spec_dict["includes"]["capabilities"]) == 2
        
        # Convert back from dict
        spec_restored = CapabilityPackSpec.from_dict(spec_dict)
        assert spec_restored.name == spec.name
        assert spec_restored.version == spec.version
        assert len(spec_restored.includes.capabilities) == 2
