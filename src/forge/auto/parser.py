"""
Requirement Parser - Converts natural language into structured ParsedRequirement.

This module uses LLM to understand user requirements and extract structured information.
"""

import json
from typing import Optional, Dict

from .llm_client import LLMClient
from .types import ParsedRequirement, IntentCategory, SideEffectType, RawRequirement


class RequirementParser:
    """
    Parse natural language requirements into structured ParsedRequirement.
    
    Uses LLM to analyze user requests and extract:
    - Action and target
    - Intent category
    - Inputs and outputs
    - Side effects
    - Missing information
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "auto"):
        """
        Initialize parser.
        
        Args:
            model: Model name to use (default: gpt-4o-mini)
            provider: LLM provider ("openai", "deepseek", or "auto" for auto-detect)
        """
        self.model = model
        self.provider = provider
        self._llm_client = None  # Lazy initialization
    
    @property
    def client(self):
        """Lazy initialization of LLM client"""
        if self._llm_client is None:
            from .llm_client import create_llm_client
            self._llm_client = create_llm_client(
                provider=self.provider,
                model=self.model
            )
        return self._llm_client.client
    
    def parse(
        self, 
        requirement: str, 
        context: Optional[Dict] = None,
        references: Optional[str] = None
    ) -> ParsedRequirement:
        """
        Parse a natural language requirement into ParsedRequirement.
        
        Args:
            requirement: Natural language requirement string
            context: Optional context dictionary
            references: Optional reference materials (formatted string)
        
        Returns:
            ParsedRequirement with structured information
        """
        prompt = self._build_parse_prompt(requirement, context or {}, references)
        parsed_dict = self._call_llm(prompt)
        return self._dict_to_parsed(parsed_dict)
    
    def _build_parse_prompt(self, requirement: str, context: Dict, references: Optional[str] = None) -> str:
        """Build prompt for requirement parsing"""
        context_str = ""
        if context:
            context_str = f"\n**Context:**\n{json.dumps(context, indent=2)}\n"
        
        references_str = ""
        if references:
            references_str = f"\n{references}\n"
        
        return f"""You are a system architect analyzing user requirements for AI-First Runtime capabilities.
{references_str}

Analyze the following user requirement and extract structured information:

**Requirement:** {requirement}
{context_str}

**Your Task:**
1. Identify the action (verb) and target (noun/system)
2. Classify the intent category: CRUD, IO, NETWORK, or COMPUTATION
3. List all explicit inputs mentioned in the requirement
4. List all implied inputs (e.g., API tokens, authentication, configuration)
5. List expected outputs based on the action
6. Identify potential side effects based on standard patterns:
   - "send", "post", "create", "write" → network_write or filesystem_write
   - "get", "fetch", "read", "retrieve" → network_read or filesystem_read
   - "delete", "remove" → filesystem_delete or network_write
   - "execute", "run" → system_exec
7. List any missing information (e.g., API endpoints, authentication methods, data formats)

**Output JSON Schema:**
{{
  "action": "verb describing the action (e.g., 'send_message', 'get_price')",
  "target": "target system or service (e.g., 'slack', 'coingecko', 'filesystem')",
  "intent_category": "CRUD|IO|NETWORK|COMPUTATION",
  "inputs": ["list", "of", "input", "parameters"],
  "outputs": ["list", "of", "expected", "outputs"],
  "side_effects": ["filesystem_read", "filesystem_write", "network_read", "network_write", "system_exec", "state_mutation"],
  "missing_info": ["list", "of", "missing", "information"]
}}

**Valid side_effects values:**
- filesystem_read
- filesystem_write
- filesystem_delete
- network_read
- network_write
- system_exec
- state_mutation

**Examples:**
- "Create a capability to get the current Bitcoin price from CoinGecko API"
  → action: "get_price", target: "coingecko", intent_category: "NETWORK", 
    inputs: ["symbol"], outputs: ["price", "currency"], side_effects: ["network_read"]
  
- "Send a message to Slack channel"
  → action: "send_message", target: "slack", intent_category: "NETWORK",
    inputs: ["channel", "message", "token"], outputs: ["message_id", "timestamp"],
    side_effects: ["network_write"], missing_info: ["Slack API endpoint", "authentication method"]

Output ONLY valid JSON, no explanations or markdown.
"""
    
    def _call_llm(self, prompt: str) -> dict:
        """
        Call LLM to parse requirement.
        
        Args:
            prompt: Parsing prompt
        
        Returns:
            Parsed requirement as dictionary
        """
        # Get actual model name (may be mapped for DeepSeek)
        if self._llm_client is None:
            from .llm_client import create_llm_client
            self._llm_client = create_llm_client(
                provider=self.provider,
                model=self.model
            )
        actual_model = self._llm_client.get_model_name()
        
        response = self.client.chat.completions.create(
            model=actual_model,
            messages=[
                {"role": "system", "content": "You are a system architect. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nContent: {content}")
    
    def _dict_to_parsed(self, parsed_dict: dict) -> ParsedRequirement:
        """Convert dictionary to ParsedRequirement object"""
        # Map intent category
        intent_str = parsed_dict.get("intent_category", "NETWORK")
        try:
            intent_category = IntentCategory(intent_str)
        except ValueError:
            # Default to NETWORK if invalid
            intent_category = IntentCategory.NETWORK
        
        # Map side effects
        side_effects = []
        for effect_str in parsed_dict.get("side_effects", []):
            try:
                side_effects.append(SideEffectType(effect_str))
            except ValueError:
                # Skip invalid side effects
                pass
        
        return ParsedRequirement(
            action=parsed_dict.get("action", "unknown"),
            target=parsed_dict.get("target", "unknown"),
            intent_category=intent_category,
            inputs=parsed_dict.get("inputs", []),
            outputs=parsed_dict.get("outputs", []),
            side_effects=side_effects,
            missing_info=parsed_dict.get("missing_info", [])
        )
