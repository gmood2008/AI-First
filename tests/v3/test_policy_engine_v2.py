"""
AI-First Runtime v3.0 - Policy Engine Tests (SPEC COMPLIANT)

Tests for the MANDATORY spec-compliant PolicyEngine implementation.
"""

import pytest
import tempfile
from pathlib import Path

from src.runtime.workflow.policy_engine_v2 import (
    PolicyEngine,
    PolicyDecision,
    RiskLevel,
    Principal,
    PolicyContext,
    PolicyRule
)


class TestCoreDataStructures:
    """Test Phase 1: Core Data Structures"""
    
    def test_policy_decision_enum(self):
        """Test PolicyDecision enum"""
        assert PolicyDecision.ALLOW.value == "ALLOW"
        assert PolicyDecision.DENY.value == "DENY"
        assert PolicyDecision.REQUIRE_APPROVAL.value == "REQUIRE_APPROVAL"
    
    def test_risk_level_enum(self):
        """Test RiskLevel enum"""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"
    
    def test_principal_dataclass(self):
        """Test Principal dataclass"""
        principal = Principal(
            type="agent",
            id="data_processor",
            roles=["reader", "writer"]
        )
        
        assert principal.type == "agent"
        assert principal.id == "data_processor"
        assert principal.roles == ["reader", "writer"]
        assert str(principal) == "agent:data_processor"
    
    def test_policy_context_frozen(self):
        """Test PolicyContext is frozen (immutable)"""
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.read_file",
            risk_level=RiskLevel.LOW
        )
        
        # Verify frozen
        with pytest.raises(Exception):  # FrozenInstanceError
            ctx.capability_id = "io.fs.write_file"
    
    def test_policy_context_with_workflow_info(self):
        """Test PolicyContext with workflow/step info"""
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.HIGH,
            workflow_id="wf-123",
            step_id="step-1",
            inputs={"path": "/data/file.txt"}
        )
        
        assert ctx.workflow_id == "wf-123"
        assert ctx.step_id == "step-1"
        assert ctx.inputs == {"path": "/data/file.txt"}


class TestPolicyRuleMatching:
    """Test Phase 2: Policy Rule Matching"""
    
    def test_rule_matches_exact_capability(self):
        """Test rule matches exact capability"""
        rule = PolicyRule(
            when={"capability": "io.fs.read_file"},
            principal_pattern="agent:*",
            decision=PolicyDecision.ALLOW
        )
        
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.read_file",
            risk_level=RiskLevel.LOW
        )
        
        assert rule.matches(ctx) is True
    
    def test_rule_matches_wildcard_capability(self):
        """Test rule matches wildcard capability"""
        rule = PolicyRule(
            when={"capability": "io.fs.*"},
            principal_pattern="agent:*",
            decision=PolicyDecision.ALLOW
        )
        
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.LOW
        )
        
        assert rule.matches(ctx) is True
    
    def test_rule_matches_risk_level(self):
        """Test rule matches risk level"""
        rule = PolicyRule(
            when={
                "capability": "io.fs.delete_file",
                "risk_level": "HIGH"
            },
            principal_pattern="agent:*",
            decision=PolicyDecision.REQUIRE_APPROVAL
        )
        
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.HIGH
        )
        
        assert rule.matches(ctx) is True
    
    def test_rule_does_not_match_different_risk_level(self):
        """Test rule does not match different risk level"""
        rule = PolicyRule(
            when={
                "capability": "io.fs.delete_file",
                "risk_level": "HIGH"
            },
            principal_pattern="agent:*",
            decision=PolicyDecision.REQUIRE_APPROVAL
        )
        
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.LOW  # Different risk level
        )
        
        assert rule.matches(ctx) is False
    
    def test_rule_matches_principal_pattern(self):
        """Test rule matches principal pattern"""
        rule = PolicyRule(
            when={"capability": "*"},
            principal_pattern="agent:data_processor",
            decision=PolicyDecision.ALLOW
        )
        
        principal = Principal(type="agent", id="data_processor", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.read_file",
            risk_level=RiskLevel.LOW
        )
        
        assert rule.matches(ctx) is True
    
    def test_rule_does_not_match_different_principal(self):
        """Test rule does not match different principal"""
        rule = PolicyRule(
            when={"capability": "*"},
            principal_pattern="agent:data_processor",
            decision=PolicyDecision.ALLOW
        )
        
        principal = Principal(type="agent", id="other_agent", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.read_file",
            risk_level=RiskLevel.LOW
        )
        
        assert rule.matches(ctx) is False


class TestPolicyEngineEvaluation:
    """Test Phase 3: Policy Engine Evaluation"""
    
    def test_first_match_wins(self):
        """Test First Match Wins logic"""
        engine = PolicyEngine()
        
        # Add two conflicting rules
        engine.add_rule(PolicyRule(
            when={"capability": "io.fs.*"},
            principal_pattern="agent:*",
            decision=PolicyDecision.ALLOW
        ))
        
        engine.add_rule(PolicyRule(
            when={"capability": "io.fs.delete_file"},
            principal_pattern="agent:*",
            decision=PolicyDecision.DENY
        ))
        
        # First rule should win
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.LOW
        )
        
        decision = engine.evaluate(ctx)
        assert decision == PolicyDecision.ALLOW  # First rule wins
    
    def test_default_deny(self):
        """Test default DENY when no rule matches"""
        engine = PolicyEngine()
        
        # No rules added
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.read_file",
            risk_level=RiskLevel.LOW
        )
        
        decision = engine.evaluate(ctx)
        assert decision == PolicyDecision.DENY  # Default deny
    
    def test_risk_based_escalation(self):
        """Test risk-based escalation for HIGH/CRITICAL risk"""
        engine = PolicyEngine()
        
        # Add rule that allows everything
        engine.add_rule(PolicyRule(
            when={"capability": "*"},
            principal_pattern="agent:*",
            decision=PolicyDecision.ALLOW
        ))
        
        # HIGH risk should be escalated to REQUIRE_APPROVAL
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.HIGH
        )
        
        decision = engine.evaluate(ctx)
        assert decision == PolicyDecision.REQUIRE_APPROVAL  # Escalated
    
    def test_no_side_effects(self):
        """Test that evaluate() has no side effects"""
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(
            when={"capability": "*"},
            principal_pattern="agent:*",
            decision=PolicyDecision.ALLOW
        ))
        
        principal = Principal(type="agent", id="test", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.read_file",
            risk_level=RiskLevel.LOW,
            inputs={"path": "/data/file.txt"}
        )
        
        # Evaluate multiple times
        decision1 = engine.evaluate(ctx)
        decision2 = engine.evaluate(ctx)
        
        # Should return same result (no side effects)
        assert decision1 == decision2
        
        # Context should be unchanged (frozen)
        assert ctx.inputs == {"path": "/data/file.txt"}


class TestYAMLPolicyLoader:
    """Test Phase 2: YAML Policy Loader"""
    
    def test_load_policies_from_yaml(self):
        """Test loading policies from YAML file"""
        yaml_content = """
default: DENY

rules:
  - when:
      capability: "io.fs.read_file"
    principal: "agent:*"
    decision: "ALLOW"
  
  - when:
      capability: "io.fs.delete_file"
      risk_level: "HIGH"
    principal: "agent:*"
    decision: "REQUIRE_APPROVAL"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = Path(f.name)
        
        try:
            engine = PolicyEngine(policies_path=yaml_path)
            
            # Verify rules loaded
            assert len(engine.rules) == 2
            assert engine.default_decision == PolicyDecision.DENY
            
            # Test first rule
            principal = Principal(type="agent", id="test", roles=[])
            ctx = PolicyContext(
                principal=principal,
                capability_id="io.fs.read_file",
                risk_level=RiskLevel.LOW
            )
            assert engine.evaluate(ctx) == PolicyDecision.ALLOW
            
            # Test second rule
            ctx2 = PolicyContext(
                principal=principal,
                capability_id="io.fs.delete_file",
                risk_level=RiskLevel.HIGH
            )
            assert engine.evaluate(ctx2) == PolicyDecision.REQUIRE_APPROVAL
        
        finally:
            yaml_path.unlink()


class TestAcceptanceCriteria:
    """Test Week 5 Acceptance Criteria"""
    
    def test_policy_denies_file_deletion(self):
        """
        Acceptance Criteria:
        Agent tries to delete a file -> Policy denies -> Workflow halts & rolls back
        """
        engine = PolicyEngine()
        
        # Add rule that denies file deletions
        engine.add_rule(PolicyRule(
            when={"capability": "io.fs.delete_file"},
            principal_pattern="agent:*",
            decision=PolicyDecision.DENY
        ))
        
        # Agent tries to delete a file
        principal = Principal(type="agent", id="test_agent", roles=[])
        ctx = PolicyContext(
            principal=principal,
            capability_id="io.fs.delete_file",
            risk_level=RiskLevel.HIGH,
            inputs={"path": "/important/file.txt"}
        )
        
        # Policy should deny
        decision = engine.evaluate(ctx)
        assert decision == PolicyDecision.DENY
        
        print("✅ Policy correctly denied file deletion")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
