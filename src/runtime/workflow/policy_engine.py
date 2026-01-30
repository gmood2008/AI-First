"""
AI-First Runtime v3.0 - Policy Engine

The Policy Engine enforces governance rules for workflow and capability execution.

Key Responsibilities:
1. Load and parse policies from YAML configuration
2. Check if a user/agent has permission to execute a capability
3. Enforce risk-based approval requirements
4. Provide audit trail for policy decisions

Design Philosophy:
- Fail-closed: Deny by default unless explicitly allowed
- Simple YAML-based configuration (no complex DSL)
- Extensible for future enterprise features (RBAC, ABAC)
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml
import logging
from enum import Enum

from specs.v3.workflow_schema import RiskLevel


logger = logging.getLogger(__name__)


class PolicyDecision(Enum):
    """Result of a policy check"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicyRule:
    """
    A single policy rule.

    Format in YAML:
    - principal: "agent:data_processor"
      capabilities: ["io.fs.read_file", "io.fs.write_file"]
      action: ALLOW

    - principal: "agent:*"
      capabilities: ["db.delete_table"]
      action: REQUIRE_APPROVAL
    """

    def __init__(
            self,
            principal: str,
            capabilities: List[str],
            action: str,
            conditions: Optional[Dict] = None):
        self.principal = principal
        self.capabilities = capabilities
        self.action = PolicyDecision(action)
        self.conditions = conditions or {}

    def matches(self, principal: str, capability_id: str) -> bool:
        """Check if this rule applies to the given principal and capability"""
        # Match principal (support wildcards)
        principal_match = self._match_pattern(self.principal, principal)

        # Match capability (support wildcards)
        capability_match = any(
            self._match_pattern(pattern, capability_id)
            for pattern in self.capabilities
        )

        return principal_match and capability_match

    @staticmethod
    def _match_pattern(pattern: str, value: str) -> bool:
        """Simple wildcard matching (supports * at end)"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return value.startswith(prefix)
        return pattern == value


class PolicyEngine:
    """
    The Policy Engine enforces access control and governance rules.

    This is the "gatekeeper" that sits between WorkflowEngine and RuntimeEngine.
    """

    def __init__(self, policies_path: Optional[Path] = None):
        """
        Initialize the policy engine.

        Args:
            policies_path: Path to policies.yaml file. If None, uses default deny-all policy.
        """
        self.policies_path = policies_path
        self.rules: List[PolicyRule] = []
        self.default_decision = PolicyDecision.DENY

        if policies_path and policies_path.exists():
            self._load_policies(policies_path)
        else:
            logger.warning(
                "No policies file provided. Using default deny-all policy.")

    def _load_policies(self, path: Path):
        """Load policies from YAML file"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)

            # Parse rules
            for rule_data in config.get('rules', []):
                rule = PolicyRule(
                    principal=rule_data['principal'],
                    capabilities=rule_data['capabilities'],
                    action=rule_data['action'],
                    conditions=rule_data.get('conditions')
                )
                self.rules.append(rule)

            # Parse default decision
            default = config.get('default', 'DENY')
            self.default_decision = PolicyDecision(default)

            logger.info(f"Loaded {len(self.rules)} policy rules from {path}")

        except Exception as e:
            logger.error(f"Failed to load policies from {path}: {e}")
            raise

    def check_permission(
        self,
        principal: str,
        capability_id: str,
        risk_level: Optional[RiskLevel] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyDecision:
        """
        Check if a principal has permission to execute a capability.

        Args:
            principal: The identity executing the capability (e.g., "agent:data_processor", "user:alice")
            capability_id: The capability being executed (e.g., "io.fs.write_file")
            risk_level: The risk level of the operation (LOW, MEDIUM, HIGH, CRITICAL)
            context: Additional context for policy evaluation

        Returns:
            PolicyDecision (ALLOW, DENY, REQUIRE_APPROVAL)
        """
        # Find matching rules (first match wins)
        for rule in self.rules:
            if rule.matches(principal, capability_id):
                decision = rule.action

                # Apply risk-based escalation
                if risk_level and risk_level in [
                        RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    if decision == PolicyDecision.ALLOW:
                        logger.info(
                            f"Escalating {capability_id} to REQUIRE_APPROVAL due to {risk_level} risk")
                        decision = PolicyDecision.REQUIRE_APPROVAL

                logger.info(
                    f"Policy decision for {principal} -> {capability_id}: {decision.value}")
                return decision

        # No matching rule, use default
        logger.warning(
            f"No policy rule matched for {principal} -> {capability_id}. Using default: {self.default_decision.value}")
        return self.default_decision

    def check_workflow_permission(
        self,
        workflow_owner: str,
        workflow_name: str,
        capabilities: List[str]
    ) -> tuple[PolicyDecision, Optional[str]]:
        """
        Check if a workflow owner has permission to execute all capabilities in a workflow.

        Args:
            workflow_owner: The owner of the workflow (e.g., "agent:orchestrator")
            workflow_name: Name of the workflow (for logging)
            capabilities: List of capability IDs used in the workflow

        Returns:
            (PolicyDecision, Optional[error_message])
        """
        denied_capabilities = []
        requires_approval = []

        for capability_id in capabilities:
            decision = self.check_permission(workflow_owner, capability_id)

            if decision == PolicyDecision.DENY:
                denied_capabilities.append(capability_id)
            elif decision == PolicyDecision.REQUIRE_APPROVAL:
                requires_approval.append(capability_id)

        if denied_capabilities:
            error_msg = f"Workflow '{workflow_name}' denied: {workflow_owner} lacks permission for {denied_capabilities}"
            logger.error(error_msg)
            return (PolicyDecision.DENY, error_msg)

        if requires_approval:
            info_msg = f"Workflow '{workflow_name}' requires approval for: {requires_approval}"
            logger.info(info_msg)
            return (PolicyDecision.REQUIRE_APPROVAL, info_msg)

        logger.info(f"Workflow '{workflow_name}' allowed for {workflow_owner}")
        return (PolicyDecision.ALLOW, None)

    def add_rule(self, rule: PolicyRule):
        """Add a policy rule dynamically (for testing or runtime configuration)"""
        self.rules.append(rule)
        logger.info(
            f"Added policy rule: {rule.principal} -> {rule.capabilities} = {rule.action.value}")

    def clear_rules(self):
        """Clear all policy rules (for testing)"""
        self.rules = []
        logger.info("Cleared all policy rules")


# Example policies.yaml format:
"""
# AI-First Runtime - Policy Configuration

default: DENY  # Deny by default (fail-closed)

rules:
  # Allow data processing agents to read/write files
  - principal: "agent:data_processor"
    capabilities: ["io.fs.read_file", "io.fs.write_file", "io.fs.create_directory"]
    action: ALLOW

  # Allow orchestrator to execute workflows
  - principal: "agent:orchestrator"
    capabilities: ["workflow.*"]
    action: ALLOW

  # Require approval for database deletions
  - principal: "agent:*"
    capabilities: ["db.delete_table", "db.drop_database"]
    action: REQUIRE_APPROVAL

  # Deny all agents from accessing sensitive APIs
  - principal: "agent:*"
    capabilities: ["api.payment.*", "api.auth.*"]
    action: DENY

  # Allow human users to do anything (with approval for high-risk)
  - principal: "user:*"
    capabilities: ["*"]
    action: ALLOW
"""
