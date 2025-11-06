"""HTTP请求节点（异步非流式）"""

import aiohttp
import asyncio
from typing import Any, Dict, Optional
from stream_workflow.core import Node, ParameterSchema, WorkflowContext, NodeExecutionError, register_node


@register_node('http_node')
class HttpNode(Node):
    """HTTP请求节点（异步非流式）
    
    功能：发送HTTP请求并获取响应
    
    输入参数：
        request: 请求配置（可选，可以从配置文件或输入获取）
            - url: string - 请求URL
            - method: string - HTTP方法（GET/POST/PUT/DELETE等）
            - headers: dict - 请求头
            - params: dict - URL参数
            - body: dict - 请求体
    
    输出参数：
        response: HTTP响应
            - status_code: integer - 响应状态码
            - body: dict - 响应体（JSON）
            - headers: dict - 响应头
            - success: boolean - 请求是否成功
    
    配置参数：
        url: string - 默认请求URL
        method: string - 默认HTTP方法（默认 "GET"）
        headers: dict - 默认请求头
        params: dict - 默认URL参数
        body: dict - 默认请求体
        timeout: float - 超时时间（秒，默认 30）
    """
    
    # 节点执行模式：顺序执行，任务驱动，非流式
    EXECUTION_MODE = 'streaming'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "request": ParameterSchema(
            is_streaming=True,
            schema={
                "url": "string",
                "method": "string",
                "headers": "dict",
                "params": "dict",
                "body": "dict"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "response": ParameterSchema(
            is_streaming=True,
            schema={
                "status_code": "integer",
                "body": "any",  # 可以是 dict、string 等
                "headers": "dict",
                "success": "boolean"
            }
        )
    }
    
    
    async def initialize(self, context: WorkflowContext):
        """初始化HTTP会话"""
        # 初始化实例变量
        self._session: Optional[aiohttp.ClientSession] = None
        self._session = aiohttp.ClientSession()
        context.log_info(f"HTTP节点 {self.node_id} 初始化完成")
    
    async def run(self, context: WorkflowContext):
        """
        运行HTTP节点（通用接口）
        """
        return await self.execute(context)
    
    async def execute(self, context: WorkflowContext):
        """
        顺序执行HTTP请求（专门用于顺序执行调用）
        
        配置参数:
            - url: 请求URL
            - method: HTTP方法（默认GET）
            - headers: 请求头
            - params: URL参数
            - body: 请求体
            - timeout: 超时时间（秒，默认30）
        """
        # 1. 从配置文件获取默认值（使用简化的 get_config 方法）
        url = self.get_config('config.url') or self.get_config('url')
        method = (self.get_config('config.method') or self.get_config('method', 'GET')).upper()
        headers = self.get_config('config.headers') or self.get_config('headers', {})
        params = self.get_config('config.params') or self.get_config('params', {})
        body = self.get_config('config.body') or self.get_config('body')
        timeout = self.get_config('config.timeout') or self.get_config('timeout', 30)
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            request = self.get_input_value('request')
            if request:
                url = request.get('url', url)
                method = request.get('method', method).upper()
                headers.update(request.get('headers', {}))
                params.update(request.get('params', {}))
                body = request.get('body', body)
        except (ValueError, KeyError):
            # 没有输入参数，使用配置文件的值
            pass
        
        # 3. 验证必需参数
        if not url:
            raise NodeExecutionError(self.node_id, "缺少必需参数: url")
        
        context.log_info(f"发送 {method} 请求到: {url}")
        
        # 4. 发送异步HTTP请求
        try:
            # 创建会话（如果不存在）
            if self._session is None:
                self._session = aiohttp.ClientSession()
            
            # 发送请求
            async with self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body if isinstance(body, dict) else None,
                data=body if body and not isinstance(body, dict) else None,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                # 获取响应
                status_code = response.status
                response_headers = dict(response.headers)
                
                # 尝试解析响应体
                content_type = response_headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    try:
                        response_body = await response.json()
                    except Exception:
                        response_body = await response.text()
                else:
                    response_body = await response.text()
                
                # 判断是否成功
                success = 200 <= status_code < 300
                
                # 5. 设置输出值
                self.set_output_value('response', {
                    'status_code': status_code,
                    'body': response_body,
                    'headers': response_headers,
                    'success': success
                })
                
                context.log_info(f"HTTP请求成功，状态码: {status_code}")
                
                return {
                    'status_code': status_code,
                    'body': response_body,
                    'headers': response_headers,
                    'success': success
                }
        
        except aiohttp.ClientError as e:
            raise NodeExecutionError(
                self.node_id,
                f"HTTP请求失败: {str(e)}",
                e
            )
        except asyncio.TimeoutError:
            raise NodeExecutionError(
                self.node_id,
                f"HTTP请求超时（{timeout}秒）"
            )
        finally:
            # 清理会话（可选，也可以在节点销毁时关闭）
            if self._session and not self._session.closed:
                # 保持会话打开以支持多次请求
                pass
    
    async def __aenter__(self):
        """支持异步上下文管理器"""
        return self
    
    async def shutdown(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def __del__(self):
        """析构时清理会话"""
        if self._session and not self._session.closed:
            # 注意：在析构函数中清理异步资源需要特殊处理
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._session.close())
                else:
                    loop.run_until_complete(self._session.close())
            except Exception:
                pass
