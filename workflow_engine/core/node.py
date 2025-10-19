"""节点基类定义"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .context import WorkflowContext
from .exceptions import NodeExecutionError
from .parameter import Parameter, ParameterSchema, StreamChunk

if TYPE_CHECKING:
    from .connection import ConnectionManager


# 全局节点注册表（用于装饰器注册）
_node_registry: Dict[str, type] = {}


def register_node(node_type: str):
    """
    节点注册装饰器
    
    Args:
        node_type: 节点类型名称
        
    Returns:
        装饰器函数
        
    Example:
        @register_node('my_node')
        class MyNode(Node):
            ...
    """
    def decorator(cls):
        _node_registry[node_type] = cls
        return cls
    return decorator


def get_registered_nodes() -> Dict[str, type]:
    """
    获取所有已注册的节点
    
    Returns:
        节点类型名称到节点类的映射
    """
    return _node_registry.copy()


class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败
    SKIPPED = "skipped"      # 已跳过


class Node(ABC):
    """
    节点基类
    所有自定义节点都需要继承此类并实现execute方法
    
    新架构特性：
    - 支持多端口输入输出（通过 INPUT_PARAMS 和 OUTPUT_PARAMS 定义）
    - 支持异步执行（execute_async 方法）
    - 支持流式数据处理（emit_chunk 和 on_chunk_received 方法）
    """
    
    # 子类定义参数结构（类属性）
    INPUT_PARAMS: Dict[str, ParameterSchema] = {}
    OUTPUT_PARAMS: Dict[str, ParameterSchema] = {}
    
    def __init__(self, node_id: str, config: Dict[str, Any], 
                 connection_manager: Optional['ConnectionManager'] = None):
        """
        初始化节点
        
        Args:
            node_id: 节点唯一标识符
            config: 节点配置字典
            connection_manager: 连接管理器（用于流式数据路由）
        """
        self.node_id = node_id
        self.config = config
        self.connection_manager = connection_manager
        self.status = NodeStatus.PENDING
        self.name = config.get('name', node_id)
        self.description = config.get('description', '')
        
        # 旧架构兼容：基于节点的输入
        self._legacy_inputs: List[str] = config.get('inputs', [])
        
        # 新架构：根据类定义创建参数实例
        self.inputs: Dict[str, Parameter] = {}
        self.outputs: Dict[str, Parameter] = {}
        self._init_parameters()
    
    def _init_parameters(self):
        """初始化参数实例"""
        for name, schema in self.INPUT_PARAMS.items():
            self.inputs[name] = Parameter(name, schema)
        
        for name, schema in self.OUTPUT_PARAMS.items():
            self.outputs[name] = Parameter(name, schema)
        
        # 运行时为流式参数创建队列
        for param in self.inputs.values():
            if param.is_streaming:
                param.stream_queue = asyncio.Queue()
        
        for param in self.outputs.values():
            if param.is_streaming:
                param.stream_queue = asyncio.Queue()
    
    # 新架构：异步执行方法
    async def execute_async(self, context: WorkflowContext) -> Any:
        """
        异步执行节点逻辑（子类实现）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        # 默认实现：调用同步方法（向后兼容）
        if hasattr(self, 'execute'):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.execute, context)
        raise NotImplementedError("子类必须实现 execute_async 或 execute 方法")
    
    # 旧架构：同步执行方法（保持向后兼容）
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行节点逻辑（旧架构，保持向后兼容）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        raise NotImplementedError("子类必须实现 execute 或 execute_async 方法")
    
    # 流式数据处理方法
    async def emit_chunk(self, param_name: str, chunk_data: Any):
        """
        发送流式 chunk
        
        Args:
            param_name: 输出参数名称
            chunk_data: chunk 数据（通常是字典）
            
        Raises:
            ValueError: 参数不存在或不是流式参数
        """
        if param_name not in self.outputs:
            raise ValueError(f"未知输出参数: {param_name}")
        
        param = self.outputs[param_name]
        if not param.is_streaming:
            raise ValueError(f"参数 {param_name} 不是流式参数")
        
        # 创建并验证 chunk
        chunk = StreamChunk(chunk_data, param.schema)
        
        # 通过连接管理器路由到目标节点
        if self.connection_manager:
            await self.connection_manager.route_chunk(self.node_id, param_name, chunk)
    
    async def consume_stream(self, param_name: str):
        """
        消费流式输入（后台任务持续监听）
        
        Args:
            param_name: 输入参数名称
            
        Raises:
            ValueError: 参数不存在
        """
        if param_name not in self.inputs:
            raise ValueError(f"未知输入参数: {param_name}")
        
        param = self.inputs[param_name]
        try:
            while True:
                chunk = await param.stream_queue.get()
                if chunk is None:  # 结束信号
                    break
                await self.on_chunk_received(param_name, chunk)
        except Exception as e:
            print(f"[{self.node_id}] 流式消费异常: {e}")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """
        处理接收到的 chunk（子类可重写）
        
        Args:
            param_name: 参数名称
            chunk: 流式数据块
        """
        pass
    
    async def feed_input_chunk(self, param_name: str, chunk_data: Any):
        """
        向节点的输入参数发送流式数据（用于外部数据注入）
        
        Args:
            param_name: 输入参数名称
            chunk_data: chunk 数据（字典或简单值）
            
        Raises:
            ValueError: 参数不存在或不是流式参数
        """
        if param_name not in self.inputs:
            raise ValueError(f"未知输入参数: {param_name}")
        
        param = self.inputs[param_name]
        if not param.is_streaming:
            raise ValueError(f"参数 {param_name} 不是流式参数，请使用 set_input_value")
        
        # 创建并验证 StreamChunk
        chunk = StreamChunk(chunk_data, param.schema)
        
        # 放入输入队列
        await param.stream_queue.put(chunk)
    
    async def close_input_stream(self, param_name: str):
        """
        关闭流式输入参数（发送结束信号）
        
        Args:
            param_name: 输入参数名称
            
        Raises:
            ValueError: 参数不存在或不是流式参数
        """
        if param_name not in self.inputs:
            raise ValueError(f"未知输入参数: {param_name}")
        
        param = self.inputs[param_name]
        if not param.is_streaming:
            raise ValueError(f"参数 {param_name} 不是流式参数")
        
        # 发送结束信号
        await param.stream_queue.put(None)
    
    def set_input_value(self, param_name: str, value: Any):
        """
        设置非流式输入值（用于外部数据注入）
        
        Args:
            param_name: 输入参数名称
            value: 输入值
            
        Raises:
            ValueError: 参数不存在或是流式参数
        """
        if param_name not in self.inputs:
            raise ValueError(f"未知输入参数: {param_name}")
        
        param = self.inputs[param_name]
        if param.is_streaming:
            raise ValueError(f"参数 {param_name} 是流式参数，请使用 feed_input_chunk")
        
        # 验证并保存值
        param.schema.validate_value(value)
        param.value = value
    
    # 非流式参数访问方法
    def set_output_value(self, param_name: str, value: Any):
        """
        设置非流式输出值
        
        Args:
            param_name: 输出参数名称
            value: 输出值
            
        Raises:
            ValueError: 参数不存在或是流式参数
        """
        if param_name not in self.outputs:
            raise ValueError(f"未知输出参数: {param_name}")
        
        param = self.outputs[param_name]
        if param.is_streaming:
            raise ValueError(f"参数 {param_name} 是流式参数，请使用 emit_chunk")
        
        # 验证并保存值
        param.schema.validate_value(value)
        param.value = value
    
    def get_input_value(self, param_name: str) -> Any:
        """
        获取非流式输入值
        
        Args:
            param_name: 输入参数名称
            
        Returns:
            参数值
            
        Raises:
            ValueError: 参数不存在
        """
        if param_name not in self.inputs:
            raise ValueError(f"未知输入参数: {param_name}")
        return self.inputs[param_name].value
    
    # 旧架构兼容方法
    def get_input_data(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        从上下文中获取输入数据（旧架构兼容）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            输入数据字典，key为输入节点ID，value为该节点的输出
        """
        input_data = {}
        for input_node_id in self._legacy_inputs:
            output = context.get_node_output(input_node_id)
            input_data[input_node_id] = output
        return input_data
    
    # 异步运行方法
    async def run_async(self, context: WorkflowContext) -> Any:
        """
        异步运行节点（包含状态管理和错误处理）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        try:
            self.status = NodeStatus.RUNNING
            context.log(f"开始执行节点: {self.node_id}")
            
            # 执行节点逻辑
            result = await self.execute_async(context)
            
            self.status = NodeStatus.SUCCESS
            context.log(f"节点执行成功: {self.node_id}")
            
            return result
            
        except Exception as e:
            self.status = NodeStatus.FAILED
            context.log(f"节点执行失败: {self.node_id} - {str(e)}", level="ERROR")
            raise NodeExecutionError(self.node_id, str(e), e)
    
    # 同步运行方法（旧架构兼容）
    def run(self, context: WorkflowContext) -> Any:
        """
        运行节点（旧架构兼容，包含状态管理和错误处理）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        try:
            self.status = NodeStatus.RUNNING
            context.log(f"开始执行节点: {self.name} (ID: {self.node_id})")
            
            # 执行前验证
            self.validate(context)
            
            # 执行节点逻辑
            result = self.execute(context)
            
            # 保存输出到上下文
            context.set_node_output(self.node_id, result)
            
            self.status = NodeStatus.SUCCESS
            context.log(f"节点执行成功: {self.name} (ID: {self.node_id})")
            
            return result
            
        except Exception as e:
            self.status = NodeStatus.FAILED
            context.log(f"节点执行失败: {self.name} (ID: {self.node_id}) - {str(e)}", level="ERROR")
            raise NodeExecutionError(self.node_id, str(e), e)
    
    def validate(self, context: WorkflowContext):
        """
        执行前验证（旧架构兼容，可选，子类可以重写）
        
        Args:
            context: 工作流执行上下文
        """
        # 验证所有输入节点都已执行
        for input_node_id in self._legacy_inputs:
            if context.get_node_output(input_node_id) is None:
                raise NodeExecutionError(
                    self.node_id,
                    f"输入节点 '{input_node_id}' 尚未执行或无输出"
                )
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.node_id} status={self.status.value}>"
