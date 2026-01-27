"""
External Capability Loader

Loads external capabilities (from external/ directory) and registers them
using adapters.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from .registry import CapabilityRegistry


def load_external_capabilities(
    registry: CapabilityRegistry,
    external_dir: Path
) -> int:
    """
    Load external capabilities from directory.
    
    External capabilities are defined by YAML specs that include
    adapter configuration in the spec metadata.
    
    Args:
        registry: CapabilityRegistry to register into
        external_dir: Directory containing external capability YAML files
    
    Returns:
        Number of capabilities loaded
    """
    if not external_dir.exists():
        return 0
    
    loaded_count = 0
    errors = []
    
    print(f"📡 Loading External Capabilities from {external_dir}")
    print("=" * 70)
    
    for yaml_file in external_dir.glob("*.yaml"):
        try:
            # Load spec
            with open(yaml_file, "r") as f:
                spec_dict = yaml.safe_load(f)
            
            # Support both v3 format (meta.id) and legacy format (id)
            if "meta" in spec_dict:
                capability_id = spec_dict["meta"].get("id")
            else:
                capability_id = spec_dict.get("id")
            
            if not capability_id:
                errors.append(f"❌ {yaml_file.name}: Missing capability ID")
                continue
            
            # Check if this is an external capability (has adapter config)
            adapter_config = spec_dict.get("adapter")
            if not adapter_config:
                # Not an external capability, skip
                continue
            
            adapter_type = adapter_config.get("type")
            if not adapter_type:
                errors.append(f"❌ {capability_id}: Missing adapter type")
                continue
            
            # Extract adapter config
            adapter_config_dict = {
                "capability_id": capability_id,
                **adapter_config.get("config", {})
            }
            
            # Register external capability
            registry.register_external(
                capability_id=capability_id,
                adapter_type=adapter_type,
                adapter_config=adapter_config_dict,
                spec_dict=spec_dict
            )
            
            loaded_count += 1
        
        except Exception as e:
            errors.append(f"❌ Failed to load {yaml_file.name}: {e}")
    
    print("=" * 70)
    print(f"✅ Loaded {loaded_count} external capabilities")
    
    if errors:
        print(f"\n⚠️  {len(errors)} errors:")
        for error in errors:
            print(f"  {error}")
    
    return loaded_count
