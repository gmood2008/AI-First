"""
Capability Registry for managing handler mappings.

This module provides the registry that maps capability IDs to their handler implementations.
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .handler import ActionHandler
from .types import CapabilityInfo, CapabilityNotFoundError


class CapabilityRegistry:
    """
    Central registry for capability handlers.
    
    This class maintains the mapping between capability IDs and their
    corresponding ActionHandler implementations.
    
    ⚠️ GOVERNANCE ENFORCEMENT:
    Capabilities are powers, not code.
    All powers must pass through governance.
    
    Registry is read-only except for governance-approved registrations.
    """
    
    def __init__(self, governance_enforced: bool = True):
        """
        Initialize empty registry
        
        Args:
            governance_enforced: If True, only governance-approved registrations allowed
        """
        self._handlers: Dict[str, ActionHandler] = {}
        self._specs: Dict[str, Dict] = {}
        self._governance_enforced = governance_enforced
        self._governance_approved: Dict[str, str] = {}  # capability_id -> approval_id
    
    def register(
        self, 
        capability_id: str, 
        handler: ActionHandler,
        spec_dict: Optional[Dict] = None
    ) -> None:
        """
        Register a capability handler.
        
        ⚠️ DEPRECATED: Use register_governance_approved() for new capabilities.
        This method is kept for backward compatibility with existing stdlib loading.
        
        Args:
            capability_id: Unique capability identifier (e.g., "io.fs.read_file")
            handler: ActionHandler instance
            spec_dict: Optional specification dictionary
        
        Raises:
            ValueError: If capability_id is already registered
            RuntimeError: If governance is enforced and this is not a governance-approved registration
        """
        if self._governance_enforced and capability_id not in self._governance_approved:
            # Allow stdlib capabilities (loaded at startup)
            # But warn for other registrations
            if not capability_id.startswith(("io.", "net.", "sys.", "data.")):
                raise RuntimeError(
                    f"❌ SECURITY: Direct registration of '{capability_id}' is forbidden. "
                    f"All new capabilities must pass through governance approval. "
                    f"Use CapabilityApprovalService.approve_proposal() instead."
                )
        
        if capability_id in self._handlers:
            raise ValueError(f"Capability '{capability_id}' is already registered")
        
        self._handlers[capability_id] = handler
        
        if spec_dict:
            self._specs[capability_id] = spec_dict
        else:
            # Extract spec from handler
            self._specs[capability_id] = handler.spec
        
        print(f"✅ Registered capability: {capability_id}")
    
    def register_governance_approved(
        self,
        capability_id: str,
        spec_dict: Dict,
        approval_id: str,
        handler: Optional[ActionHandler] = None
    ) -> None:
        """
        Register a governance-approved capability.
        
        This is the ONLY safe way to register new capabilities.
        All other registration paths are forbidden.
        
        Args:
            capability_id: Capability identifier
            spec_dict: Specification dictionary (must include _governance metadata)
            approval_id: Governance approval ID
            handler: Optional handler instance (will be created if not provided)
        
        Raises:
            ValueError: If capability_id is already registered
            RuntimeError: If spec_dict lacks governance metadata
        """
        if capability_id in self._handlers:
            raise ValueError(f"Capability '{capability_id}' is already registered")
        
        # Verify governance metadata
        if '_governance' not in spec_dict:
            raise RuntimeError(
                f"❌ SECURITY: Capability '{capability_id}' lacks governance metadata. "
                f"This registration is forbidden."
            )
        
        # Store approval ID
        self._governance_approved[capability_id] = approval_id
        
        # Register handler if provided
        if handler:
            self._handlers[capability_id] = handler
        else:
            # For now, we'll store the spec and handler will be loaded on demand
            # In a production system, you would create the handler here
            pass
        
        # Store spec
        self._specs[capability_id] = spec_dict
        
        print(f"✅ Registered governance-approved capability: {capability_id} (approval: {approval_id})")
    
    def register_external(
        self,
        capability_id: str,
        adapter_type: str,
        adapter_config: Dict[str, Any],
        spec_dict: Optional[Dict] = None
    ) -> None:
        """
        Register an external capability via adapter.
        
        This method creates a handler from an adapter and registers it.
        
        Args:
            capability_id: Capability identifier
            adapter_type: Type of adapter ("claude_skill", "openai_function", "http_api")
            adapter_config: Adapter configuration dictionary
            spec_dict: Optional specification dictionary (will be created if not provided)
        
        Raises:
            ValueError: If capability_id is already registered
            ImportError: If adapter module is not available
        """
        if capability_id in self._handlers:
            raise ValueError(f"Capability '{capability_id}' is already registered")
        
        try:
            from runtime.adapters import create_adapter
            
            # Create adapter
            adapter = create_adapter(adapter_type, adapter_config)
            
            # Create spec if not provided
            if spec_dict is None:
                # Try to load from file
                spec_path = Path(f"capabilities/validated/external/{capability_id}.yaml")
                if spec_path.exists():
                    import yaml
                    with open(spec_path, "r") as f:
                        spec_dict = yaml.safe_load(f)
                else:
                    raise ValueError(
                        f"Spec not found for external capability '{capability_id}'. "
                        f"Please provide spec_dict or ensure spec file exists at {spec_path}"
                    )
            
            # Create handler from adapter
            handler = adapter.create_handler(spec_dict)
            
            # Register
            self.register(capability_id, handler, spec_dict)
            
            print(f"✅ Registered external capability: {capability_id} (via {adapter_type} adapter)")
        
        except ImportError as e:
            raise ImportError(
                f"Failed to import adapter module: {e}. "
                f"Make sure runtime.adapters is available."
            ) from e
    
    def get_handler(self, capability_id: str) -> ActionHandler:
        """
        Get handler for a capability.
        
        Args:
            capability_id: Capability identifier
        
        Returns:
            ActionHandler instance
        
        Raises:
            CapabilityNotFoundError: If capability not registered
        """
        handler = self._handlers.get(capability_id)
        if handler is None:
            raise CapabilityNotFoundError(
                f"Capability '{capability_id}' not found. "
                f"Available: {list(self._handlers.keys())}"
            )
        return handler
    
    def get_spec(self, capability_id: str) -> Dict:
        """
        Get specification for a capability.
        
        Args:
            capability_id: Capability identifier
        
        Returns:
            Specification dictionary
        
        Raises:
            CapabilityNotFoundError: If capability not registered
        """
        spec = self._specs.get(capability_id)
        if spec is None:
            raise CapabilityNotFoundError(f"Capability '{capability_id}' not found")
        return spec
    
    def has_capability(self, capability_id: str) -> bool:
        """
        Check if capability is registered.
        
        Args:
            capability_id: Capability identifier
        
        Returns:
            True if registered
        """
        return capability_id in self._handlers
    
    def list_capabilities(self) -> List[str]:
        """
        List all registered capability IDs.
        
        Returns:
            List of capability IDs
        """
        return sorted(self._handlers.keys())
    
    def list_capability_info(self) -> List[CapabilityInfo]:
        """
        List detailed information about all capabilities.
        
        Returns:
            List of CapabilityInfo objects
        """
        infos = []
        for capability_id in self.list_capabilities():
            handler = self._handlers[capability_id]
            info_dict = handler.to_info_dict()
            infos.append(CapabilityInfo(**info_dict))
        return infos
    
    def unregister(self, capability_id: str) -> None:
        """
        Unregister a capability.
        
        Args:
            capability_id: Capability identifier
        """
        if capability_id in self._handlers:
            del self._handlers[capability_id]
            del self._specs[capability_id]
            print(f"❌ Unregistered capability: {capability_id}")
    
    def clear(self) -> None:
        """Clear all registered capabilities"""
        self._handlers.clear()
        self._specs.clear()
        print("🗑️  Registry cleared")
    
    def get_by_namespace(self, namespace: str) -> List[str]:
        """
        Get all capabilities in a namespace.
        
        Args:
            namespace: Namespace prefix (e.g., "io.fs")
        
        Returns:
            List of capability IDs in that namespace
        """
        return [
            cap_id for cap_id in self.list_capabilities()
            if cap_id.startswith(namespace + ".")
        ]
    
    def load_from_directory(
        self, 
        specs_dir: Path, 
        handler_factory: callable
    ) -> int:
        """
        Load capabilities from a directory of YAML specs.
        
        Args:
            specs_dir: Directory containing YAML specification files
            handler_factory: Function that creates handler from spec_dict
                            Signature: (spec_dict: Dict) -> ActionHandler
        
        Returns:
            Number of capabilities loaded
        
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        if not specs_dir.exists():
            raise FileNotFoundError(f"Directory not found: {specs_dir}")
        
        count = 0
        for yaml_file in specs_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    spec_dict = yaml.safe_load(f)
                
                capability_id = spec_dict["meta"]["id"]
                handler = handler_factory(spec_dict)
                
                self.register(capability_id, handler, spec_dict)
                count += 1
            except Exception as e:
                print(f"⚠️  Failed to load {yaml_file.name}: {e}")
        
        return count
    
    def __len__(self) -> int:
        """Get number of registered capabilities"""
        return len(self._handlers)
    
    def __contains__(self, capability_id: str) -> bool:
        """Check if capability is registered (supports 'in' operator)"""
        return capability_id in self._handlers
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<CapabilityRegistry: {len(self)} capabilities>"
