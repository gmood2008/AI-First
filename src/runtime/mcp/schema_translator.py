"""
Schema Translator - Convert AI-First YAML specs to MCP JSON Schema.

This module translates capability specifications from AI-First format
to Model Context Protocol (MCP) tool definitions.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml


class SchemaTranslator:
    """
    Translates AI-First capability specs to MCP tool definitions.
    
    This class handles the conversion of YAML-based capability specifications
    to MCP's JSON Schema format for tool registration.
    """
    
    def __init__(self):
        """Initialize translator"""
        pass
    
    def translate_capability(self, spec_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a single capability spec to MCP tool definition.
        
        Args:
            spec_dict: AI-First capability specification dictionary
        
        Returns:
            MCP tool definition dictionary
        
        Example:
            >>> translator = SchemaTranslator()
            >>> spec = yaml.safe_load(open("io_fs_read_file.yaml"))
            >>> mcp_tool = translator.translate_capability(spec)
            >>> print(mcp_tool["name"])
            "io.fs.read_file"
        """
        meta = spec_dict["meta"]
        interface = spec_dict["interface"]
        contracts = spec_dict["contracts"]
        behavior = spec_dict.get("behavior", {})
        
        # Build MCP tool definition
        tool_def = {
            "name": meta["id"],
            "title": meta.get("title", meta["id"]),
            "description": self._build_description(meta, contracts, behavior),
            "inputSchema": self._translate_input_schema(interface["inputs"]),
        }
        
        # Add output schema if outputs are defined
        if interface.get("outputs"):
            tool_def["outputSchema"] = self._translate_output_schema(interface["outputs"])
        
        return tool_def
    
    def _build_description(
        self, 
        meta: Dict[str, Any], 
        contracts: Dict[str, Any],
        behavior: Dict[str, Any],
    ) -> str:
        """
        Build comprehensive tool description.
        
        This includes:
        - Base description
        - Side effects warning
        - Undo strategy
        - Confirmation requirement
        
        Args:
            meta: Metadata section
            contracts: Contracts section
            behavior: Behavior section
        
        Returns:
            Formatted description string
        """
        parts = [meta["description"]]
        
        # Add side effects warning
        side_effects = contracts.get("side_effects", [])
        if side_effects and side_effects != ["read_only"]:
            effects_str = ", ".join(side_effects)
            parts.append(f"\n⚠️ Side Effects: {effects_str}")
        
        # Add confirmation requirement
        if contracts.get("requires_confirmation", False):
            parts.append("\n🔒 Requires Confirmation: This operation needs user approval before execution.")
        
        # Add undo strategy
        undo_strategy = behavior.get("undo_strategy")
        if undo_strategy and undo_strategy not in ["not_applicable", "n/a", "none"]:
            parts.append(f"\n↩️ Undo Strategy: {undo_strategy}")
        
        return " ".join(parts)
    
    def _translate_input_schema(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate AI-First input schema to JSON Schema.
        
        Args:
            inputs: AI-First inputs dictionary
        
        Returns:
            JSON Schema object
        """
        properties = {}
        required = []
        
        for param_name, param_spec in inputs.items():
            properties[param_name] = self._translate_property(param_spec)
            
            # Check if required
            if not param_spec.get("optional", False):
                required.append(param_name)
        
        schema = {
            "type": "object",
            "properties": properties,
        }
        
        if required:
            schema["required"] = required
        
        return schema
    
    def _translate_output_schema(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate AI-First output schema to JSON Schema.
        
        Args:
            outputs: AI-First outputs dictionary
        
        Returns:
            JSON Schema object
        """
        properties = {}
        required = list(outputs.keys())  # All outputs are required
        
        for output_name, output_spec in outputs.items():
            properties[output_name] = self._translate_property(output_spec)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    def _translate_property(self, prop_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a single property specification.
        
        Args:
            prop_spec: Property specification
        
        Returns:
            JSON Schema property definition
        """
        prop_type = prop_spec["type"]
        json_prop = {
            "description": prop_spec.get("description", ""),
        }
        
        # Map AI-First types to JSON Schema types
        if prop_type == "string":
            json_prop["type"] = "string"
            
            # Add enum if present
            if "enum" in prop_spec:
                json_prop["enum"] = prop_spec["enum"]
            
            # Add format if present
            if "format" in prop_spec:
                json_prop["format"] = prop_spec["format"]
        
        elif prop_type == "integer":
            json_prop["type"] = "integer"
            
            # Add min/max if present
            if "min" in prop_spec:
                json_prop["minimum"] = prop_spec["min"]
            if "max" in prop_spec:
                json_prop["maximum"] = prop_spec["max"]
        
        elif prop_type == "float":
            json_prop["type"] = "number"
            
            # Add min/max if present
            if "min" in prop_spec:
                json_prop["minimum"] = prop_spec["min"]
            if "max" in prop_spec:
                json_prop["maximum"] = prop_spec["max"]
        
        elif prop_type == "boolean":
            json_prop["type"] = "boolean"
        
        elif prop_type == "array":
            json_prop["type"] = "array"
            
            # Translate items schema
            if "items" in prop_spec:
                json_prop["items"] = self._translate_property(prop_spec["items"])
            else:
                # Default to any type if items not specified
                json_prop["items"] = {}
        
        elif prop_type == "object":
            json_prop["type"] = "object"
            
            # Translate properties if present
            if "properties" in prop_spec and prop_spec["properties"]:
                json_prop["properties"] = {}
                for key, value in prop_spec["properties"].items():
                    json_prop["properties"][key] = self._translate_property(value)
            else:
                # Allow any properties if not specified
                json_prop["additionalProperties"] = True
        
        elif prop_type == "null":
            json_prop["type"] = "null"
        
        else:
            # Unknown type, default to string
            json_prop["type"] = "string"
        
        return json_prop
    
    def translate_from_file(self, yaml_path: Path) -> Dict[str, Any]:
        """
        Load and translate a YAML spec file.
        
        Args:
            yaml_path: Path to YAML specification file
        
        Returns:
            MCP tool definition dictionary
        
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        with open(yaml_path, "r") as f:
            spec_dict = yaml.safe_load(f)
        
        return self.translate_capability(spec_dict)
    
    def translate_multiple(
        self, 
        specs_dir: Path,
        capability_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Translate multiple capability specs.
        
        Args:
            specs_dir: Directory containing YAML specs
            capability_ids: Optional list of specific capability IDs to translate.
                          If None, translates all YAML files in directory.
        
        Returns:
            List of MCP tool definitions
        """
        tools = []
        
        if capability_ids:
            # Translate specific capabilities
            for cap_id in capability_ids:
                yaml_filename = cap_id.replace(".", "_") + ".yaml"
                yaml_path = specs_dir / yaml_filename
                
                if yaml_path.exists():
                    try:
                        tool_def = self.translate_from_file(yaml_path)
                        tools.append(tool_def)
                    except Exception as e:
                        print(f"⚠️  Failed to translate {cap_id}: {e}")
        else:
            # Translate all YAML files
            for yaml_path in specs_dir.glob("*.yaml"):
                try:
                    tool_def = self.translate_from_file(yaml_path)
                    tools.append(tool_def)
                except Exception as e:
                    print(f"⚠️  Failed to translate {yaml_path.name}: {e}")
        
        return tools


def create_mcp_tools_from_stdlib(specs_dir: Path) -> List[Dict[str, Any]]:
    """
    Create MCP tool definitions for all standard library capabilities.
    
    This is a convenience function for quickly generating MCP tools
    from the AI-First standard library.
    
    Args:
        specs_dir: Directory containing stdlib YAML specs
    
    Returns:
        List of MCP tool definitions
    
    Example:
        >>> specs_dir = Path("../ai-first-specs/capabilities/validated/stdlib")
        >>> tools = create_mcp_tools_from_stdlib(specs_dir)
        >>> print(f"Created {len(tools)} MCP tools")
    """
    translator = SchemaTranslator()
    return translator.translate_multiple(specs_dir)
