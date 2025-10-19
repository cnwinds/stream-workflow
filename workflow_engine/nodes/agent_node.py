"""智能对话代理（Agent）节点"""

import asyncio
import time
from workflow_engine.core import Node, ParameterSchema, StreamChunk, WorkflowContext, register_node


@register_node('agent_node')
class AgentNode(Node):
    """
    智能对话代理节点
    
    功能：接收文本输入，生成对话响应
    
    输入参数：
        text_input: 输入文本流
            - text: string - 输入文本
            - is_final: boolean - 是否最终输入
            - confidence: float - 置信度
            - timestamp: float - 时间戳
    
    输出参数：
        response_text: 响应文本流
            - text: string - 响应文本
            - is_final: boolean - 是否最终响应
            - confidence: float - 置信度
            - timestamp: float - 时间戳
    
    配置参数：
        model: string - 语言模型名称（默认 "gpt-4"）
        temperature: float - 生成温度（默认 0.7）
        stream: boolean - 是否流式生成（默认 true）
        system_prompt: string - 系统提示词
    """
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "text_input": ParameterSchema(
            is_streaming=True,
            schema={
                "text": "string",
                "is_final": "boolean",
                "confidence": "float",
                "timestamp": "float"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "response_text": ParameterSchema(
            is_streaming=True,
            schema={
                "text": "string",
                "is_final": "boolean",
                "confidence": "float",
                "timestamp": "float"
            }
        )
    }
    
    def __init__(self, node_id, config, connection_manager=None):
        super().__init__(node_id, config, connection_manager)
        self._input_buffer = []  # 累积输入文本
    
    async def execute_async(self, context: WorkflowContext):
        """
        初始化 Agent
        
        Args:
            context: 工作流执行上下文
        """
        model = self.config.get('model', 'gpt-4')
        temperature = self.config.get('temperature', 0.7)
        stream = self.config.get('stream', True)
        system_prompt = self.config.get('system_prompt', '你是一个有帮助的AI助手。')
        
        context.log(f"Agent 节点启动 [{self.node_id}]")
        context.log(f"  - 模型: {model}")
        context.log(f"  - 温度: {temperature}")
        context.log(f"  - 流式生成: {stream}")
        context.log(f"  - 系统提示: {system_prompt}")
        
        # 这里应该初始化语言模型
        # 例如：self.llm = init_llm(model, temperature, system_prompt)
        
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            context.log(f"Agent 节点关闭 [{self.node_id}]")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """
        处理输入文本并生成响应
        
        Args:
            param_name: 参数名称
            chunk: 流式数据块
        """
        if param_name == "text_input":
            text = chunk.data["text"]
            is_final = chunk.data["is_final"]
            
            # 累积输入文本
            self._input_buffer.append(text)
            
            # 如果是最终输入，生成响应
            if is_final:
                full_text = " ".join(self._input_buffer)
                self._input_buffer.clear()
                
                # 生成响应（流式或一次性）
                stream = self.config.get('stream', True)
                if stream:
                    await self._generate_stream_response(full_text)
                else:
                    await self._generate_response(full_text)
    
    async def _generate_stream_response(self, input_text: str):
        """
        流式生成响应
        
        Args:
            input_text: 输入文本
        """
        # 模拟流式生成
        response = await self._call_llm(input_text)
        
        # 逐字发送（实际应该是按 token 发送）
        words = response.split()
        for i, word in enumerate(words):
            is_final = (i == len(words) - 1)
            await self.emit_chunk("response_text", {
                "text": word + (" " if not is_final else ""),
                "is_final": is_final,
                "confidence": 1.0,
                "timestamp": time.time()
            })
            await asyncio.sleep(0.05)  # 模拟生成延迟
    
    async def _generate_response(self, input_text: str):
        """
        一次性生成响应
        
        Args:
            input_text: 输入文本
        """
        response = await self._call_llm(input_text)
        await self.emit_chunk("response_text", {
            "text": response,
            "is_final": True,
            "confidence": 1.0,
            "timestamp": time.time()
        })
    
    async def _call_llm(self, input_text: str) -> str:
        """
        调用语言模型（示例实现）
        
        Args:
            input_text: 输入文本
            
        Returns:
            生成的响应文本
            
        注意：这是一个简单的示例实现，实际应用中应调用真实的 LLM API
        如 OpenAI API、Azure OpenAI、本地模型等
        """
        # 模拟 LLM 调用延迟
        await asyncio.sleep(0.5)
        
        # 实际应用中应该：
        # 1. 调用 LLM API（OpenAI、Claude、GLM 等）
        # 2. 处理流式或非流式响应
        # 3. 错误处理和重试
        
        # 示例：返回模拟响应
        return f"这是对 '{input_text}' 的智能回复。"

