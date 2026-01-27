"""
AI-First Runtime v3.0 - Policy Engine Tests

Test the PolicyEngine's ability to enforce access control rules.

Acceptance Criteria (Week 5):
- Agent tries to delete a file -> Policy denies -> Workflow halts & rolls back
"""

import pytest
import tempfile
from pathlib import Path

from src.runtime.workflow.policy_engine import (
    PolicyEngine,
    PolicyDecision,
    PolicyRule
)
from src.specs.v3.workflow_schema import RiskLevel


class TestPolicyEngine:
    """Test PolicyEngine rule matching and decision making"""
    
    def test_load_policies_from_yaml(self):
        """Test loading policies from YAML file"""
        # Create temporary policies file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
default: DENY

rules:
  - principal: "agent:test"
    capabilities: ["io.fs.read_file"]
    action: ALLOW
  
  - principal: "agent:*"
    capabilities: ["io.fs.delete_file"]
    action: DENY
""")
            policies_path = Path(f.name)
        
        try:
            # Load policies
            engine = PolicyEngine(policies_path)
            
            # Verify rules loaded
            assert len(engine.rules) == 2
            assert engine.default_decision == PolicyDecision.DENY
        finally:
            policies_path.unlink()
    
    def test_allow_decision(self):
        """Test ALLOW decision for permitted operations"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.read_file"],
            action="ALLOW"
        ))
        
        decision = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.read_file"
        )
        
        assert decision == PolicyDecision.ALLOW
    
    def test_deny_decision(self):
        """Test DENY decision for forbidden operations"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.delete_file"],
            action="DENY"
        ))
        
        decision = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.delete_file"
        )
        
        assert decision == PolicyDecision.DENY
    
    def test_require_approval_decision(self):
        """Test REQUIRE_APPROVAL decision for high-risk operations"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["db.delete_table"],
            action="REQUIRE_APPROVAL"
        ))
        
        decision = engine.check_permission(
            principal="agent:test",
            capability_id="db.delete_table"
        )
        
        assert decision == PolicyDecision.REQUIRE_APPROVAL
    
    def test_wildcard_principal_matching(self):
        """Test wildcard matching for principals"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:*",
            capabilities=["io.fs.write_file"],
            action="ALLOW"
        ))
        
        # Should match any agent
        decision1 = engine.check_permission(
            principal="agent:test1",
            capability_id="io.fs.write_file"
        )
        decision2 = engine.check_permission(
            principal="agent:test2",
            capability_id="io.fs.write_file"
        )
        
        assert decision1 == PolicyDecision.ALLOW
        assert decision2 == PolicyDecision.ALLOW
    
    def test_wildcard_capability_matching(self):
        """Test wildcard matching for capabilities"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.*"],
            action="ALLOW"
        ))
        
        # Should match any io.fs capability
        decision1 = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.read_file"
        )
        decision2 = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.write_file"
        )
        
        assert decision1 == PolicyDecision.ALLOW
        assert decision2 == PolicyDecision.ALLOW
    
    def test_default_deny(self):
        """Test default DENY when no rule matches"""
        engine = PolicyEngine()
        # No rules added
        
        decision = engine.check_permission(
            principal="agent:unknown",
            capability_id="io.fs.read_file"
        )
        
        assert decision == PolicyDecision.DENY
    
    def test_risk_based_escalation(self):
        """Test automatic escalation to REQUIRE_APPROVAL for HIGH risk"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.delete_file"],
            action="ALLOW"
        ))
        
        # Without risk level: ALLOW
        decision1 = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.LOW
        )
        
        # With HIGH risk: Escalated to REQUIRE_APPROVAL
        decision2 = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.HIGH
        )
        
        assert decision1 == PolicyDecision.ALLOW
        assert decision2 == PolicyDecision.REQUIRE_APPROVAL
    
    def test_first_match_wins(self):
        """Test that first matching rule wins"""
        engine = PolicyEngine()
        
        # Add two conflicting rules
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.read_file"],
            action="ALLOW"
        ))
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.read_file"],
            action="DENY"
        ))
        
        # First rule should win
        decision = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.read_file"
        )
        
        assert decision == PolicyDecision.ALLOW
    
    def test_check_workflow_permission_all_allowed(self):
        """Test workflow permission check when all capabilities allowed"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.*"],
            action="ALLOW"
        ))
        
        decision, error_msg = engine.check_workflow_permission(
            workflow_owner="agent:test",
            workflow_name="test_workflow",
            capabilities=["io.fs.read_file", "io.fs.write_file"]
        )
        
        assert decision == PolicyDecision.ALLOW
        assert error_msg is None
    
    def test_check_workflow_permission_denied(self):
        """Test workflow permission check when a capability is denied"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.read_file"],
            action="ALLOW"
        ))
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.delete_file"],
            action="DENY"
        ))
        
        decision, error_msg = engine.check_workflow_permission(
            workflow_owner="agent:test",
            workflow_name="test_workflow",
            capabilities=["io.fs.read_file", "io.fs.delete_file"]
        )
        
        assert decision == PolicyDecision.DENY
        assert "io.fs.delete_file" in error_msg
    
    def test_check_workflow_permission_requires_approval(self):
        """Test workflow permission check when a capability requires approval"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.read_file"],
            action="ALLOW"
        ))
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["db.delete_table"],
            action="REQUIRE_APPROVAL"
        ))
        
        decision, info_msg = engine.check_workflow_permission(
            workflow_owner="agent:test",
            workflow_name="test_workflow",
            capabilities=["io.fs.read_file", "db.delete_table"]
        )
        
        assert decision == PolicyDecision.REQUIRE_APPROVAL
        assert "db.delete_table" in info_msg


class TestPolicyEngineIntegration:
    """Test PolicyEngine integration with WorkflowEngine"""
    
    def test_policy_denies_workflow_halts_and_rolls_back(self):
        """
        Acceptance Criteria (Week 5):
        Agent tries to delete a file -> Policy denies -> Workflow halts & rolls back
        """
        # This test will be implemented after integrating PolicyEngine with WorkflowEngine
        # For now, we verify that PolicyEngine correctly denies the operation
        
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.delete_file"],
            action="DENY"
        ))
        
        decision = engine.check_permission(
            principal="agent:test",
            capability_id="io.fs.delete_file"
        )
        
        assert decision == PolicyDecision.DENY
        
        # TODO: Add full integration test with WorkflowEngine
        # 1. Create workflow with delete_file step
        # 2. Submit workflow with agent:test as owner
        # 3. Verify workflow fails at delete_file step
        # 4. Verify rollback is triggered
        # 5. Verify previous steps are compensated


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
