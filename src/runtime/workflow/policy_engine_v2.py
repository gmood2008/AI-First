"""
AI-First Runtime v3.0 - Policy Engine (MANDATORY SPEC COMPLIANT)

This implementation strictly follows the Week 5 directive specification:
- Phase 1: Core Data Structures
- Phase 2: YAML Policy Loader (NO DSL)
- Phase 3: evaluate() with First Match Wins
- Phase 4: Runtime Integration

Principle #9: The Gatekeeper, Not the Commander
- Engine only says Yes or No
- No side effects
- No DB access
- No input modification
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum
import yaml
import logging


logger = logging.getLogger(__name__)


# ============================================================================
# Phase 1: Core Data Structures (MANDATORY)
# ============================================================================

class PolicyDecision(Enum):
    """Result of a policy evaluation"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class RiskLevel(Enum):
    """Risk classification for operations"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Principal:
    """
    Identity executing a capability.
    
    Examples:
    - Principal(type="agent", id="data_processor", roles=["reader", "writer"])
    - Principal(type="user", id="alice", roles=["admin"])
    """
    type: str  # "agent" or "user"
    id: str    # Unique identifier
    roles: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass(frozen=True)
class PolicyContext:
    """
    Immutable context for policy evaluation.
    
    Contains all information needed to make a policy decision.
    Frozen to prevent accidental modification (Principle #9).
    """
    principal: Principal
    capability_id: str
    risk_level: RiskLevel
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"PolicyContext(principal={self.principal}, capability={self.capability_id}, risk={self.risk_level.value})"


# ============================================================================
# Phase 2: YAML Policy Loader (NO DSL, simple rules)
# ============================================================================

@dataclass
class PolicyRule:
    """
    A single policy rule.
    
    Format in YAML:
    - when:
        capability: "io.fs.delete_file"
        risk_level: "HIGH"
      principal_pattern: "agent:*"
      decision: "REQUIRE_APPROVAL"
    """
    when: Dict[str, Any]  # Conditions (capability, risk_level)
    principal_pattern: str  # Pattern to match (supports *)
    decision: PolicyDecision
    
    def matches(self, ctx: PolicyContext) -> bool:
        """
        Check if this rule applies to the given context.
        
        Logic: ALL conditions in 'when' must match.
        """
        # Match principal pattern
        if not self._match_principal(ctx.principal):
            return False
        
        # Match capability (if specified)
        if "capability" in self.when:
            capability_pattern = self.when["capability"]
            if not self._match_pattern(capability_pattern, ctx.capability_id):
                return False
        
        # Match risk_level (if specified)
        if "risk_level" in self.when:
            required_risk = self.when["risk_level"]
            if ctx.risk_level.value != required_risk:
                return False
        
        # All conditions matched
        return True
    
    def _match_principal(self, principal: Principal) -> bool:
        """Match principal against pattern"""
        principal_str = str(principal)
        return self._match_pattern(self.principal_pattern, principal_str)
    
    @staticmethod
    def _match_pattern(pattern: str, value: str) -> bool:
        """Simple wildcard matching (supports * at end)"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return value.startswith(prefix)
        return pattern == value


# ============================================================================
# Phase 3: The Engine Logic (First Match Wins, No Side Effects)
# ============================================================================

class PolicyEngine:
    """
    The Policy Engine enforces access control rules.
    
    MANDATORY CONSTRAINTS (Principle #9):
    - Gatekeeper, not Commander: Only says Yes or No
    - No side effects: Does not modify inputs or state
    - No DB access: Pure function evaluation
    - First Match Wins: Stops at first matching rule
    - Default DENY: Fail-closed security
    """
    
    def __init__(self, policies_path: Optional[Path] = None):
        """
        Initialize the policy engine.
        
        Args:
            policies_path: Path to policies.yaml file
        """
        self.rules: List[PolicyRule] = []
        self.default_decision = PolicyDecision.DENY
        
        if policies_path and policies_path.exists():
            self._load_policies(policies_path)
        else:
            logger.warning("No policies file provided. Using default deny-all policy.")
    
    def _load_policies(self, path: Path):
        """
        Load policies from YAML file.
        
        NO DSL. NO complex expressions. Simple rules only.
        """
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Parse default decision
            default = config.get('default', 'DENY')
            self.default_decision = PolicyDecision(default)
            
            # Parse rules
            for rule_data in config.get('rules', []):
                rule = PolicyRule(
                    when=rule_data['when'],
                    principal_pattern=rule_data['principal'],
                    decision=PolicyDecision(rule_data['decision'])
                )
                self.rules.append(rule)
            
            logger.info(f"Loaded {len(self.rules)} policy rules from {path}")
        
        except Exception as e:
            logger.error(f"Failed to load policies from {path}: {e}")
            raise
    
    def evaluate(self, ctx: PolicyContext) -> PolicyDecision:
        """
        Evaluate a policy context and return a decision.
        
        MANDATORY LOGIC:
        1. First Match Wins: Stop at first matching rule
        2. No Side Effects: Pure function, no state modification
        3. Default DENY: If no rule matches, deny
        
        Args:
            ctx: PolicyContext (frozen, immutable)
        
        Returns:
            PolicyDecision (ALLOW, DENY, REQUIRE_APPROVAL)
        """
        # First Match Wins: Iterate rules in order
        for rule in self.rules:
            if rule.matches(ctx):
                decision = rule.decision
                
                # Risk-based escalation: HIGH/CRITICAL always requires approval
                if ctx.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    if decision == PolicyDecision.ALLOW:
                        logger.info(
                            f"Escalating {ctx.capability_id} to REQUIRE_APPROVAL due to {ctx.risk_level.value} risk")
                        decision = PolicyDecision.REQUIRE_APPROVAL
                
                logger.info(f"Policy decision for {ctx}: {decision.value}")
                return decision
        
        # No matching rule: Default DENY
        logger.warning(f"No policy rule matched for {ctx}. Using default: {self.default_decision.value}")
        return self.default_decision
    
    def add_rule(self, rule: PolicyRule):
        """Add a policy rule dynamically (for testing)"""
        self.rules.append(rule)
        logger.info(f"Added policy rule: {rule.principal_pattern} -> {rule.decision.value}")
    
    def clear_rules(self):
        """Clear all policy rules (for testing)"""
        self.rules = []
        logger.info("Cleared all policy rules")


# ============================================================================
# Example policies.yaml format (NO DSL, simple rules)
# ============================================================================

EXAMPLE_POLICIES_YAML = """
# AI-First Runtime - Policy Configuration
# NO DSL. NO complex expressions. Simple rules only.

default: DENY  # Fail-closed

rules:
  # Allow agents to read files
  - when:
      capability: "io.fs.read_file"
    principal: "agent:*"
    decision: "ALLOW"
  
  # Require approval for file deletions (HIGH risk)
  - when:
      capability: "io.fs.delete_file"
      risk_level: "HIGH"
    principal: "agent:*"
    decision: "REQUIRE_APPROVAL"
  
  # Deny all agents from payment APIs
  - when:
      capability: "api.payment.*"
    principal: "agent:*"
    decision: "DENY"
  
  # Allow human users everything (with risk escalation)
  - when:
      capability: "*"
    principal: "user:*"
    decision: "ALLOW"
"""
