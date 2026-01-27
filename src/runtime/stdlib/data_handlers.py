"""
Data and text capability handlers.

This module implements JSON parsing, text processing capabilities.
"""

import json
import re
from typing import Any, Dict, List

from ..handler import ActionHandler


class JSONParseHandler(ActionHandler):
    """Handler for data.json.parse"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        json_string = params["json_string"]
        strict = params.get("strict", True)
        
        try:
            # Parse JSON
            if strict:
                data = json.loads(json_string)
            else:
                # Non-strict mode: allow comments, trailing commas (not standard JSON)
                data = json.loads(json_string)
            
            # Convert back to string for output (since spec defines output as string)
            data_str = json.dumps(data)
            
            return {
                "data": data_str,
                "success": True,
            }
        except json.JSONDecodeError as e:
            return {
                "data": "",
                "success": False,
                "error_message": f"JSON decode error: {e}",
            }
        except Exception as e:
            return {
                "data": "",
                "success": False,
                "error_message": str(e),
            }


class JSONStringifyHandler(ActionHandler):
    """Handler for data.json.stringify"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        data_str = params["data"]
        pretty = params.get("pretty", False)
        
        try:
            # Parse data string as JSON first
            data = json.loads(data_str)
            
            # Stringify with formatting
            if pretty:
                json_string = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                json_string = json.dumps(data, ensure_ascii=False)
            
            return {
                "json_string": json_string,
                "success": True,
            }
        except json.JSONDecodeError as e:
            return {
                "json_string": "",
                "success": False,
                "error_message": f"Invalid JSON input: {e}",
            }
        except Exception as e:
            return {
                "json_string": "",
                "success": False,
                "error_message": str(e),
            }


class RegexMatchHandler(ActionHandler):
    """Handler for text.regex.match"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        text = params["text"]
        pattern = params["pattern"]
        flags_list = params.get("flags", [])
        
        try:
            # Convert flags
            flags = 0
            if "ignorecase" in flags_list:
                flags |= re.IGNORECASE
            if "multiline" in flags_list:
                flags |= re.MULTILINE
            if "dotall" in flags_list:
                flags |= re.DOTALL
            
            # Compile pattern
            regex = re.compile(pattern, flags)
            
            # Find matches
            matches = []
            if "global" in flags_list:
                # Find all matches
                for match in regex.finditer(text):
                    matches.append({
                        "match": match.group(0),
                        "groups": list(match.groups()),
                        "start": match.start(),
                        "end": match.end(),
                    })
            else:
                # Find first match only
                match = regex.search(text)
                if match:
                    matches.append({
                        "match": match.group(0),
                        "groups": list(match.groups()),
                        "start": match.start(),
                        "end": match.end(),
                    })
            
            return {
                "matches": matches,
                "success": True,
            }
        except re.error as e:
            return {
                "matches": [],
                "success": False,
                "error_message": f"Invalid regex pattern: {e}",
            }
        except Exception as e:
            return {
                "matches": [],
                "success": False,
                "error_message": str(e),
            }


class TemplateRenderHandler(ActionHandler):
    """Handler for text.template.render"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        template = params["template"]
        variables_str = params["variables"]
        syntax = params.get("syntax", "mustache")
        
        try:
            # Parse variables JSON
            variables = json.loads(variables_str)
            
            # Render based on syntax
            if syntax == "mustache":
                rendered = self._render_mustache(template, variables)
            elif syntax == "jinja2":
                rendered = self._render_jinja2(template, variables)
            else:
                rendered = self._render_simple(template, variables)
            
            return {
                "rendered": rendered,
                "success": True,
            }
        except json.JSONDecodeError as e:
            return {
                "rendered": "",
                "success": False,
                "error_message": f"Invalid variables JSON: {e}",
            }
        except Exception as e:
            return {
                "rendered": "",
                "success": False,
                "error_message": str(e),
            }
    
    def _render_mustache(self, template: str, variables: Dict) -> str:
        """Simple mustache-style rendering"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    
    def _render_jinja2(self, template: str, variables: Dict) -> str:
        """Simple jinja2-style rendering (basic implementation)"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
        return result
    
    def _render_simple(self, template: str, variables: Dict) -> str:
        """Simple variable substitution"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"${key}", str(value))
        return result
