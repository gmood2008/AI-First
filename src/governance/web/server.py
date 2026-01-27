"""
Reference Web Governance Console Server

这是一个简单的 HTTP 服务器，用于提供静态文件和 API 代理。

核心原则：
- 所有逻辑在 API 层
- 这个服务器只是提供静态文件和 API 代理
- 可以删除，治理系统仍然完整
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json
import sys
import os

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from governance.api_v3 import GovernanceAPIV3


class GovernanceConsoleHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def __init__(self, *args, **kwargs):
        self.governance_api = GovernanceAPIV3()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path.startswith('/api/governance'):
            # API 请求
            self.handle_api_request()
        else:
            # 静态文件
            self.serve_static_file()
    
    def do_POST(self):
        """处理 POST 请求"""
        if self.path.startswith('/api/governance'):
            self.handle_api_request()
        else:
            self.send_error(404)
    
    def handle_api_request(self):
        """处理 API 请求"""
        try:
            # 解析路径
            path = self.path.replace('/api/governance', '')
            
            # 特殊路径需要优先处理（避免被误认为是 capability_id）
            if path == '/capabilities/risk-distribution':
                result = self.governance_api.platform_api.get_risk_distribution()
                self.send_json_response(result)
                return
            
            # 路由
            if path == '/capabilities' or path == '/capabilities/':
                result = self.governance_api.get_capabilities()
            elif path.startswith('/capabilities/'):
                parts = [p for p in path.split('/') if p]  # 过滤空字符串
                
                if len(parts) == 2:  # /capabilities/{id}
                    capability_id = parts[1]
                    result = self.governance_api.get_capability(capability_id)
                elif len(parts) == 3:  # /capabilities/{id}/{action}
                    capability_id = parts[1]
                    action = parts[2]
                    
                    if action == 'health':
                        result = self.governance_api.get_capability_health(capability_id)
                    elif action == 'signals':
                        query_params = self.parse_query_params()
                        limit = int(query_params.get('limit', 100)) if query_params.get('limit') else None
                        result = self.governance_api.get_capability_signals(capability_id, limit)
                    elif action == 'lifecycle':
                        result = self.governance_api.get_capability_lifecycle(capability_id)
                    else:
                        self.send_error(404)
                        return
                else:
                    self.send_error(404)
                    return
            elif path == '/proposals' or path == '/proposals/' or (path.startswith('/proposals') and '?' in path):
                # 解析查询参数（需要从完整路径解析，因为 path 可能包含查询参数）
                query_params = self.parse_query_params()
                result = self.governance_api.get_proposals(
                    status=query_params.get('status'),
                    proposal_type=query_params.get('proposal_type')
                )
            elif path.startswith('/proposals/'):
                parts = [p for p in path.split('/') if p]
                if len(parts) >= 2:
                    proposal_id = parts[1]
                    if len(parts) == 2:  # /proposals/{id}
                        result = self.governance_api.get_proposal(proposal_id)
                    elif len(parts) == 3:  # /proposals/{id}/approve 或 /proposals/{id}/reject
                        # POST 请求已在 do_POST 中处理
                        self.send_error(404)
                        return
                    else:
                        self.send_error(404)
                        return
                else:
                    self.send_error(404)
                    return
            elif path == '/signals' or path == '/signals/' or (path.startswith('/signals') and '?' in path):
                query_params = self.parse_query_params()
                limit = query_params.get('limit')
                if limit:
                    try:
                        limit = int(limit)
                    except ValueError:
                        limit = 100
                else:
                    limit = 100
                result = self.governance_api.platform_api.get_signals(limit=limit)
            elif path.startswith('/demand/missing-capabilities'):
                query_params = self.parse_query_params()
                result = self.governance_api.platform_api.get_missing_capabilities(
                    window_hours=int(query_params.get('window_hours', 24)),
                    min_frequency=int(query_params.get('min_frequency', 1))
                )
            elif path == '/decisions' or path == '/decisions/':
                query_params = self.parse_query_params()
                result = self.governance_api.get_decisions(
                    limit=int(query_params.get('limit', 100)) if query_params.get('limit') else None
                )
            else:
                self.send_error(404)
                return
            
            # 发送响应
            self.send_json_response(result)
        
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"API Error: {error_msg}")
            self.send_error(500, str(e))
    
    def do_POST(self):
        """处理 POST 请求"""
        if self.path.startswith('/api/governance/proposals/') and '/approve' in self.path:
            proposal_id = self.path.split('/')[4]
            data = self.read_json_body()
            
            result = self.governance_api.approve_proposal(
                proposal_id=proposal_id,
                decided_by=data.get('decided_by', 'admin'),
                rationale=data.get('rationale', ''),
                role=data.get('role')
            )
            self.send_json_response(result)
        
        elif self.path.startswith('/api/governance/proposals/') and '/reject' in self.path:
            proposal_id = self.path.split('/')[4]
            data = self.read_json_body()
            
            result = self.governance_api.reject_proposal(
                proposal_id=proposal_id,
                decided_by=data.get('decided_by', 'admin'),
                rationale=data.get('rationale', ''),
                role=data.get('role')
            )
            self.send_json_response(result)
        
        else:
            self.send_error(404)
    
    def serve_static_file(self):
        """提供静态文件"""
        # 忽略 favicon.ico 请求（返回 204 No Content）
        if self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        
        static_dir = Path(__file__).parent / 'static'
        
        if self.path == '/' or self.path == '/index.html':
            file_path = static_dir / 'index.html'
        else:
            file_path = static_dir / self.path.lstrip('/')
        
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            
            if file_path.suffix == '.html':
                self.send_header('Content-Type', 'text/html')
            elif file_path.suffix == '.js':
                self.send_header('Content-Type', 'application/javascript')
            elif file_path.suffix == '.css':
                self.send_header('Content-Type', 'text/css')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)
    
    def parse_query_params(self):
        """解析查询参数"""
        full_path = self.path
        if '?' not in full_path:
            return {}
        
        query_string = full_path.split('?')[1]
        # 处理 URL 编码
        from urllib.parse import unquote
        params = {}
        
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[unquote(key)] = unquote(value)
        
        return params
    
    def read_json_body(self):
        """读取 JSON 请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))
    
    def send_json_response(self, data):
        """发送 JSON 响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = json.dumps(data, default=str, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """输出日志"""
        print(f"[{self.address_string()}] {format % args}")


def run_server(port=8080):
    """运行服务器"""
    server = HTTPServer(('localhost', port), GovernanceConsoleHandler)
    print(f"🚀 Governance Console running at http://localhost:{port}")
    print("⚠️  This is a Reference Implementation. All logic lives in API.")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
