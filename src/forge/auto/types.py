"""
Data structures for AutoForge pipeline.

This module defines the internal data structures used to hold the "Blueprint"
of a capability before it becomes code.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """Intent category classification"""
    CRUD = "CRUD"           # Create, Read, Update, Delete operations
    IO = "IO"               # File system operations
    NETWORK = "NETWORK"     # Network/API operations
    COMPUTATION = "COMPUTATION"  # Computational operations


class SideEffectType(str, Enum):
    """Side effect types"""
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"
    SYSTEM_EXEC = "system_exec"
    STATE_MUTATION = "state_mutation"


class RawRequirement(BaseModel):
    """
    Raw user requirement input.
    
    This is the initial input from the user before any processing.
    """
    description: str = Field(
        ...,
        description="User's natural language requirement"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (user ID, environment, etc.)"
    )


class ParsedRequirement(BaseModel):
    """
    The AI's understanding of the requirement.
    
    This is the structured representation after parsing the raw requirement.
    """
    action: str = Field(
        ...,
        description="The action to perform (e.g., 'send_message', 'get_price')"
    )
    target: str = Field(
        ...,
        description="The target system/service (e.g., 'slack', 'coingecko')"
    )
    intent_category: IntentCategory = Field(
        ...,
        description="Category of the intent"
    )
    inputs: List[str] = Field(
        default_factory=list,
        description="List of explicit and implied input parameters"
    )
    outputs: List[str] = Field(
        default_factory=list,
        description="List of expected output fields"
    )
    side_effects: List[SideEffectType] = Field(
        default_factory=list,
        description="Potential side effects based on standard patterns"
    )
    missing_info: List[str] = Field(
        default_factory=list,
        description="What we don't know yet (e.g., API endpoint, auth method)"
    )
