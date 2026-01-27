import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from runtime.types import ActionOutput, ExecutionContext
from runtime.handler import ActionHandler
from runtime.stdlib.generated.net_github_get_repo import GetRepoHandler
import httpx

@pytest.fixture
def spec_dict():
    return {
        "id": "net.github.get_repo",
        "name": "Get Repository Info Github",
        "description": "Capability to get repository info on github. Note: specific_api_endpoint, authentication_method_details, response_data_format may need to be configured.",
        "operation_type": "NETWORK",
        "risk": {
            "level": "LOW",
            "justification": "Read-only operation with no side effects",
            "requires_approval": false
        },
        "side_effects": {
            "reversible": true,
            "scope": "network",
            "description": "Side effects: network_read"
        },
        "compensation": {
            "supported": true,
            "strategy": "automatic",
            "capability_id": null
        },
        "parameters": [
            {
                "name": "owner",
                "type": "string",
                "description": "Owner parameter",
                "required": true,
                "default": null
            },
            {
                "name": "repo",
                "type": "string",
                "description": "Repo parameter",
                "required": true,
                "default": null
            }
        ],
        "returns": {
            "type": "object",
            "properties": {
                "repository_info": {
                    "type": "string",
                    "description": "Repository Info value"
                },
                "metadata": {
                    "type": "string",
                    "description": "Metadata value"
                }
            }
        },
        "metadata": {
            "version": "1.0.0",
            "author": "AutoForge",
            "tags": [
                "github",
                "network",
                "network"
            ],
            "deprecated": false
        },
        "handler": "runtime.stdlib.generated.net_github_get_repo"
    }

@pytest.fixture
def context():
    ctx = Mock(spec=ExecutionContext)
    ctx.workspace_root = Path("/tmp/test_workspace")
    ctx.user_id = "test_user"
    ctx.session_id = "test_session"
    return ctx

@pytest.fixture
def valid_params():
    return {"owner": "test_owner", "repo": "test_repo"}

@pytest.fixture
def mock_repo_data():
    return {"id": 123, "name": "test_repo", "full_name": "test_owner/test_repo"}

class TestGetRepoHandler:
    def test_handler_initialization(self, spec_dict):
        handler = GetRepoHandler(spec_dict)
        assert isinstance(handler, ActionHandler)
        assert handler.spec == spec_dict

    def test_execute_success(self, spec_dict, context, valid_params, mock_repo_data):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_repo_data
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = handler.execute(valid_params, context)
            
            assert isinstance(result, ActionOutput)
            assert result.result["repository_info"] == str(mock_repo_data)
            assert result.result["metadata"] == f"Successfully retrieved repository info for {valid_params['owner']}/{valid_params['repo']}"
            assert result.description == f"Retrieved GitHub repository information for {valid_params['owner']}/{valid_params['repo']}"
            assert callable(result.undo_closure)
            
            expected_url = f"https://api.github.com/repos/{valid_params['owner']}/{valid_params['repo']}"
            mock_client.get.assert_called_once_with(expected_url)

    def test_execute_with_undo(self, spec_dict, context, valid_params, mock_repo_data):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_repo_data
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = handler.execute(valid_params, context)
            
            assert result.undo_closure is not None
            result.undo_closure()

    def test_validate_params_missing_owner(self, spec_dict, context):
        handler = GetRepoHandler(spec_dict)
        params = {"repo": "test_repo"}
        
        with pytest.raises(ValueError, match="Both 'owner' and 'repo' parameters are required"):
            handler.execute(params, context)

    def test_validate_params_missing_repo(self, spec_dict, context):
        handler = GetRepoHandler(spec_dict)
        params = {"owner": "test_owner"}
        
        with pytest.raises(ValueError, match="Both 'owner' and 'repo' parameters are required"):
            handler.execute(params, context)

    def test_validate_params_empty_strings(self, spec_dict, context):
        handler = GetRepoHandler(spec_dict)
        params = {"owner": "", "repo": "test_repo"}
        
        with pytest.raises(ValueError, match="Both 'owner' and 'repo' parameters are required"):
            handler.execute(params, context)
        
        params = {"owner": "test_owner", "repo": ""}
        
        with pytest.raises(ValueError, match="Both 'owner' and 'repo' parameters are required"):
            handler.execute(params, context)

    def test_validate_params_none_values(self, spec_dict, context):
        handler = GetRepoHandler(spec_dict)
        params = {"owner": None, "repo": "test_repo"}
        
        with pytest.raises(ValueError, match="Both 'owner' and 'repo' parameters are required"):
            handler.execute(params, context)

    def test_handle_http_error(self, spec_dict, context, valid_params):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError("HTTP 404 Not Found")
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="HTTP error occurred while fetching repository info"):
                handler.execute(valid_params, context)

    def test_handle_timeout_exception(self, spec_dict, context, valid_params):
        handler = GetRepoHandler(spec_dict)
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
            
            with pytest.raises(RuntimeError, match="Request timed out while fetching repository info"):
                handler.execute(valid_params, context)

    def test_handle_generic_exception(self, spec_dict, context, valid_params):
        handler = GetRepoHandler(spec_dict)
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Generic error")
            
            with pytest.raises(RuntimeError, match="Unexpected error occurred"):
                handler.execute(valid_params, context)

    def test_http_status_error(self, spec_dict, context, valid_params):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response
        )
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="HTTP error occurred while fetching repository info"):
                handler.execute(valid_params, context)

    def test_execute_with_special_characters(self, spec_dict, context, mock_repo_data):
        handler = GetRepoHandler(spec_dict)
        params = {"owner": "owner-with-dash", "repo": "repo.with.dots"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_repo_data
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = handler.execute(params, context)
            
            assert isinstance(result, ActionOutput)
            expected_url = f"https://api.github.com/repos/{params['owner']}/{params['repo']}"
            mock_client.get.assert_called_once_with(expected_url)

    def test_action_output_structure(self, spec_dict, context, valid_params, mock_repo_data):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_repo_data
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = handler.execute(valid_params, context)
            
            assert hasattr(result, 'result')
            assert hasattr(result, 'description')
            assert hasattr(result, 'undo_closure')
            
            assert isinstance(result.result, dict)
            assert 'repository_info' in result.result
            assert 'metadata' in result.result
            assert isinstance(result.result['repository_info'], str)
            assert isinstance(result.result['metadata'], str)
            assert isinstance(result.description, str)
            assert callable(result.undo_closure)

    def test_undo_closure_execution(self, spec_dict, context, valid_params, mock_repo_data):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_repo_data
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = handler.execute(valid_params, context)
            
            undo_result = result.undo_closure()
            assert undo_result is None

    @pytest.mark.parametrize("params", [
        {"owner": "test", "repo": "test"},
        {"owner": "123", "repo": "456"},
        {"owner": "owner_name", "repo": "repo-name"},
        {"owner": "Owner", "repo": "Repo"},
    ])
    def test_execute_various_valid_params(self, spec_dict, context, params, mock_repo_data):
        handler = GetRepoHandler(spec_dict)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_repo_data
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = handler.execute(params, context)
            
            assert isinstance(result, ActionOutput)
            expected_url = f"https://api.github.com/repos/{params['owner']}/{params['repo']}"
            mock_client.get.assert_called_once_with(expected_url)