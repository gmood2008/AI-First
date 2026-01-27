from typing import Dict, Any, Optional, Callable
import httpx
from pathlib import Path
from runtime.handler import ActionHandler
from runtime.types import ActionOutput

class GetRepoHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        try:
            self.validate_params(params)
            
            owner = params.get("owner")
            repo = params.get("repo")
            
            if not owner or not repo:
                raise ValueError("Both 'owner' and 'repo' parameters are required")
            
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            
            with httpx.Client(timeout=30.0) as client:
                response = client.get(api_url)
                response.raise_for_status()
                repo_data = response.json()
            
            result = {
                "repository_info": str(repo_data),
                "metadata": f"Successfully retrieved repository info for {owner}/{repo}"
            }
            
            description = f"Retrieved GitHub repository information for {owner}/{repo}"
            
            def undo_closure() -> None:
                pass
            
            return ActionOutput(
                result=result,
                description=description,
                undo_closure=undo_closure
            )
            
        except httpx.HTTPError as e:
            error_msg = f"HTTP error occurred while fetching repository info: {str(e)}"
            raise RuntimeError(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = "Request timed out while fetching repository info"
            raise RuntimeError(error_msg) from e
        except ValueError as e:
            raise
        except Exception as e:
            error_msg = f"Unexpected error occurred: {str(e)}"
            raise RuntimeError(error_msg) from e