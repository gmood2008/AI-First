# GitHub API 参考文档

## 获取仓库信息

### API 端点
```
GET https://api.github.com/repos/{owner}/{repo}
```

### 认证方式
- 使用 OAuth token
- Header: `Authorization: Bearer {token}` 或 `Authorization: token {token}`

### 请求示例
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.github.com/repos/octocat/Hello-World
```

### 响应示例
```json
{
  "id": 1296269,
  "name": "Hello-World",
  "full_name": "octocat/Hello-World",
  "owner": {
    "login": "octocat",
    "id": 1
  },
  "description": "This your first repo!",
  "private": false,
  "fork": false,
  "stargazers_count": 80,
  "watchers_count": 80,
  "forks_count": 9,
  "open_issues_count": 0,
  "default_branch": "master"
}
```

### 参数说明
- `owner`: 仓库所有者（用户名或组织名）
- `repo`: 仓库名称
- `token`: OAuth token（必需）

### 错误处理
- 401: 认证失败，token 无效
- 404: 仓库不存在
- 403: 权限不足
