"""HTTP请求节点"""

import requests
from typing import Any, Dict
from workflow_engine.core import Node, WorkflowContext, NodeExecutionError


class HttpNode(Node):
    """
    HTTP请求节点
    支持GET、POST、PUT、DELETE等HTTP方法
    """
    
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行HTTP请求
        
        配置参数:
            - url: 请求URL（必需）
            - method: HTTP方法（默认GET）
            - headers: 请求头
            - params: URL参数
            - body: 请求体（POST/PUT等）
            - timeout: 超时时间（秒）
        """
        # 获取配置
        url = self.config.get('url')
        method = self.config.get('method', 'GET').upper()
        headers = self.config.get('headers', {})
        params = self.config.get('params', {})
        body = self.config.get('body')
        timeout = self.config.get('timeout', 30)
        
        if not url:
            raise NodeExecutionError(self.node_id, "缺少必需参数: url")
        
        # 从输入节点获取数据（可以用于动态构建请求）
        input_data = self.get_input_data(context)
        
        # 支持从输入数据中覆盖参数
        if input_data:
            # 如果有输入数据，可以用它来更新请求参数
            first_input = list(input_data.values())[0] if input_data else {}
            if isinstance(first_input, dict):
                if 'url' in first_input:
                    url = first_input['url']
                if 'params' in first_input:
                    params.update(first_input['params'])
                if 'body' in first_input:
                    body = first_input['body']
        
        try:
            context.log(f"发送 {method} 请求到: {url}")
            
            # 发送请求
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body if isinstance(body, dict) else None,
                data=body if not isinstance(body, dict) else None,
                timeout=timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 尝试解析JSON响应
            try:
                result = response.json()
            except ValueError:
                result = {
                    'status_code': response.status_code,
                    'text': response.text,
                    'headers': dict(response.headers)
                }
            
            context.log(f"HTTP请求成功，状态码: {response.status_code}")
            return result
            
        except requests.exceptions.RequestException as e:
            raise NodeExecutionError(
                self.node_id,
                f"HTTP请求失败: {str(e)}",
                e
            )
