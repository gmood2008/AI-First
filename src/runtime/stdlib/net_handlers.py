"""
Network capability handlers (net.http.* namespace).

This module implements HTTP request capabilities.
"""

from typing import Any, Dict
import httpx

from ..handler import ActionHandler


class HTTPGetHandler(ActionHandler):
    """Handler for net.http.get"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        url = params["url"]
        headers = params.get("headers", {})
        timeout = params.get("timeout", 30)
        follow_redirects = params.get("follow_redirects", True)
        
        try:
            response = httpx.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
            
            return {
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers),
                "success": 200 <= response.status_code < 300,
            }
        except httpx.TimeoutException:
            return {
                "status_code": 0,
                "body": "",
                "headers": {},
                "success": False,
                "error_message": f"Request timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                "status_code": 0,
                "body": "",
                "headers": {},
                "success": False,
                "error_message": str(e),
            }


class HTTPPostHandler(ActionHandler):
    """Handler for net.http.post"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        url = params["url"]
        body = params.get("body", "")
        headers = params.get("headers", {})
        timeout = params.get("timeout", 30)
        content_type = params.get("content_type", "application/json")
        
        # Set content type header
        if "Content-Type" not in headers:
            headers["Content-Type"] = content_type
        
        try:
            response = httpx.post(
                url,
                content=body,
                headers=headers,
                timeout=timeout,
            )
            
            return {
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers),
                "success": 200 <= response.status_code < 300,
            }
        except httpx.TimeoutException:
            return {
                "status_code": 0,
                "body": "",
                "headers": {},
                "success": False,
                "error_message": f"Request timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                "status_code": 0,
                "body": "",
                "headers": {},
                "success": False,
                "error_message": str(e),
            }


class HTTPPutHandler(ActionHandler):
    """Handler for net.http.put"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        url = params["url"]
        body = params.get("body", "")
        headers = params.get("headers", {})
        timeout = params.get("timeout", 30)
        content_type = params.get("content_type", "application/json")
        
        # Set content type header
        if "Content-Type" not in headers:
            headers["Content-Type"] = content_type
        
        try:
            response = httpx.put(
                url,
                content=body,
                headers=headers,
                timeout=timeout,
            )
            
            return {
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers),
                "success": 200 <= response.status_code < 300,
            }
        except httpx.TimeoutException:
            return {
                "status_code": 0,
                "body": "",
                "headers": {},
                "success": False,
                "error_message": f"Request timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                "status_code": 0,
                "body": "",
                "headers": {},
                "success": False,
                "error_message": str(e),
            }
