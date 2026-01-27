"""
这是 AutoForge 会生成的 GitHub API 处理器代码示例
实际运行需要 OPENAI_API_KEY 和依赖安装
"""

from typing import Dict, Any, Optional, Callable
from pathlib import Path
from runtime.handler import ActionHandler
from runtime.types import ActionOutput
import httpx


class GetRepoHandler(ActionHandler):
    """从 GitHub API 获取仓库信息"""
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        # 验证参数
        self.validate_params(params)
        
        # 提取参数
        owner = params["owner"]
        repo = params["repo"]
        token = params["token"]
        
        # 构建 API URL
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        # 设置请求头
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-First-Runtime"
        }
        
        try:
            # 发送请求
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                repo_data = response.json()
            
            # 提取关键信息
            result = {
                "id": repo_data.get("id"),
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "description": repo_data.get("description"),
                "stargazers_count": repo_data.get("stargazers_count", 0),
                "forks_count": repo_data.get("forks_count", 0),
                "open_issues_count": repo_data.get("open_issues_count", 0),
            }
            
            description = f"成功获取仓库 {owner}/{repo} 的信息"
            
            return ActionOutput(
                result=result,
                description=description,
                undo_closure=None  # 只读操作，无需撤销
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("认证失败：OAuth token 无效或已过期")
            elif e.response.status_code == 404:
                raise ValueError(f"仓库不存在：{owner}/{repo}")
            elif e.response.status_code == 403:
                raise ValueError("权限不足：token 没有访问该仓库的权限")
            else:
                raise ValueError(f"GitHub API 错误：{e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise ValueError(f"网络请求失败：{str(e)}")
