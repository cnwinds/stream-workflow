"""节点基类定义"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .context import WorkflowContext
from .exceptions import NodeExecutionError, WorkflowException
from .parameter import Parameter, ParameterSchema, StreamChunk, FieldSchema, FieldSchemaDef

if TYPE_CHECKING:
    from .connection import ConnectionManager
    from .workflow import WorkflowEngine


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
    - 支持配置参数定义（通过 CONFIG_PARAMS 定义，使用 FieldSchema）
    - 支持异步执行（execute_async 方法）
    - 支持流式数据处理（emit_chunk 和 on_chunk_received 方法）
    - 支持混合执行模式（通过 EXECUTION_MODE 定义）
    """
    
    # 节点执行模式（子类可重写）
    EXECUTION_MODE = 'sequential'  # 'sequential' | 'streaming' | 'hybrid'
    
    # 子类定义参数结构（类属性）
    INPUT_PARAMS: Dict[str, ParameterSchema] = {}
    OUTPUT_PARAMS: Dict[str, ParameterSchema] = {}
    CONFIG_PARAMS: Dict[str, FieldSchemaDef] = {}  # 配置参数定义（字段定义结构）
    
    def __init__(self, node_id: str, config: Dict[str, Any], 
                 engine: Optional['WorkflowEngine'] = None):
        """
        初始化节点
        
        Args:
            node_id: 节点唯一标识符
            config: 节点配置字典
            engine: 工作流引擎实例（用于获取连接管理器等）
        """
        self.node_id = node_id
        self.config = config
        self.engine = engine
        # 通过 engine 获取 connection_manager
        self.connection_manager = engine.get_connection_manager() if engine else None
        self.status = NodeStatus.PENDING
        self.name = config.get('name', node_id)
        self.description = config.get('description', '')
        
        # 根据类定义创建参数实例
        self.inputs: Dict[str, Parameter] = {}
        self.outputs: Dict[str, Parameter] = {}
        self._init_parameters()
        
        # 验证配置参数
        self._validate_config_params()
        
        # 存储解析后的配置（在执行时填充）
        self.resolved_config: Dict[str, Any] = {}
    
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
    
    def _validate_config_params(self):
        """
        验证配置参数是否符合 CONFIG_PARAMS 定义
        
        Raises:
            ValueError: 缺少必传配置参数或参数类型不匹配
        """
        for param_name, field_def in self.CONFIG_PARAMS.items():
            # 使用 FieldSchema 类来处理字段定义的验证和默认值应用
            field_schema = FieldSchema.from_def(field_def)
            field_schema.validate_and_apply(self.config, param_name, self.node_id)
    
    # ===== 生命周期方法 =====
    
    async def initialize(self, context: WorkflowContext):
        """
        节点初始化（可选，在run之前调用）
        
        子类可以重写此方法进行初始化工作，如：
        - 加载模型
        - 建立连接
        - 预处理配置
        
        Args:
            context: 工作流执行上下文
        """
        pass
    
    async def run(self, context: WorkflowContext) -> Any:
        """
        节点运行入口（子类必须实现）
        
        不同执行模式的行为：
        - sequential: 执行完返回结果
        - streaming: 持续运行，处理流式数据
        - hybrid: 初始化后持续运行
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        raise NotImplementedError("子类必须实现 run 方法")
    
    async def execute(self, context: WorkflowContext) -> Any:
        """
        顺序执行接口（子类可选实现）
        
        专门用于 sequential 和 hybrid 节点的顺序执行调用。
        如果子类实现了此方法，则优先使用 execute 方法；
        否则回退到 run 方法。
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        # 默认回退到 run 方法
        return await self.run(context)
    
    async def shutdown(self):
        """
        节点关闭（可选，在stop时调用）
        
        子类可以重写此方法进行清理工作，如：
        - 关闭连接
        - 释放资源
        - 保存状态
        """
        pass
    
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
        while True:
            chunk = await param.stream_queue.get()
            if chunk is None:  # 结束信号
                break
            try:
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
        
        # 检查流式队列是否已初始化
        if param.stream_queue is None:
            raise ValueError(
                f"流式参数 {param_name} 的队列未初始化。"
                "请确保节点已调用 initialize() 方法"
            )
        
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
        
        # 检查流式队列是否已初始化
        if param.stream_queue is None:
            raise ValueError(
                f"流式参数 {param_name} 的队列未初始化。"
                "请确保节点已调用 initialize() 方法"
            )
        
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
    
    
    def resolve_config_params(self, context: WorkflowContext, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析配置中的参数引用，使用 Jinja2 模板引擎渲染
        
        支持的语法（Jinja2）：
        - {{ nodes['node_id'] }}: 引用整个节点输出
        - {{ nodes['node_id'].field }}: 引用节点输出的某个字段
        - {{ nodes['node_id'].data.score }}: 引用嵌套字段
        - {{ var_name }}: 引用全局变量（直接使用变量名）
        - {{ get_node_output('node_id', 'field') }}: 使用辅助函数访问节点输出
        
        Args:
            context: 工作流执行上下文
            config: 要解析的配置字典，默认使用 self.config
            
        Returns:
            解析后的配置字典
            
        Examples:
            配置: {"score": "{{ nodes['start'].data.score }}", "threshold": 80}
            解析后: {"score": 85, "threshold": 80}
            
            配置: {"url": "{{ base_url }}/api", "message": "Hello {{ user.name }}"}
            解析后: {"url": "https://api.com/api", "message": "Hello World"}
        """
        if config is None:
            config = self.config
        
        return self._resolve_value(context, config)
    
    def _resolve_value(self, context: WorkflowContext, value: Any) -> Any:
        """
        递归解析值中的参数引用，使用 Jinja2 模板引擎渲染
        
        Args:
            context: 工作流执行上下文
            value: 要解析的值（可以是字符串、字典、列表等）
            
        Returns:
            解析后的值
            
        Raises:
            WorkflowException: 如果 Jinja2 环境未初始化或渲染失败
        """
        if isinstance(value, str):
            # 检查是否包含 Jinja2 语法标记
            if '{{' in value or '{%' in value or '{#' in value:
                # 使用 self.engine 的 render_template 方法渲染
                try:
                    rendered = self.engine.render_template(value)
                    # 尝试将结果转换为合适的类型
                    # 如果渲染后的字符串看起来像数字、布尔值或 null，尝试转换
                    rendered = rendered.strip()
                    if rendered.lower() == 'true':
                        return True
                    elif rendered.lower() == 'false':
                        return False
                    elif rendered.lower() == 'null' or rendered.lower() == 'none':
                        return None
                    elif rendered.isdigit():
                        return int(rendered)
                    elif rendered.replace('.', '', 1).isdigit():
                        return float(rendered)
                    return rendered
                except Exception as e:
                    raise WorkflowException(f"Jinja2 模板渲染失败: {str(e)}")
            # 不包含 Jinja2 语法，直接返回
            return value
        
        elif isinstance(value, dict):
            # 递归解析字典中的所有值
            return {k: self._resolve_value(context, v) for k, v in value.items()}
        
        elif isinstance(value, list):
            # 递归解析列表中的所有元素
            return [self._resolve_value(context, item) for item in value]
        
        else:
            # 其他类型直接返回
            return value
    
    def get_config(self, key: str = None, default: Any = None) -> Any:
        """
        获取配置参数（优先使用解析后的配置）
        
        这是一个便捷方法，简化了配置参数的获取：
        - 自动使用 resolved_config（如果已解析）
        - 支持嵌套键访问（使用点号分隔，如 "config.url"）
        - 提供默认值支持
        
        Args:
            key: 配置键名，支持嵌套访问（如 "config.url"），如果为 None 则返回整个配置
            default: 默认值，当键不存在时返回
            
        Returns:
            配置值或默认值
            
        Examples:
            # 获取顶层配置
            url = self.get_config('url')
            
            # 获取嵌套配置
            url = self.get_config('config.url')
            
            # 使用默认值
            timeout = self.get_config('timeout', 30)
            
            # 获取整个配置字典
            all_config = self.get_config()
        """
        # 使用解析后的配置（如果存在），否则使用原始配置
        config = self.resolved_config if self.resolved_config else self.config
        
        # 如果没有指定 key，返回整个配置
        if key is None:
            return config
        
        # 支持嵌套键访问
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    # 异步运行方法
    async def _execute_async(self, context: WorkflowContext) -> Any:
        """
        异步运行节点（包含状态管理和错误处理）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        if self.status == NodeStatus.RUNNING:
            context.log_warning(f"节点 {self.node_id} 正在运行中")
            return None
        
        try:
            self.status = NodeStatus.RUNNING
            context.log_info(f"开始执行节点: {self.node_id}")
            
            # 1. 执行前解析配置中的参数引用
            try:
                self.resolved_config = self.resolve_config_params(context)
                context.log_info(f"节点 {self.node_id} 配置参数解析完成")
            except Exception as e:
                context.log_warning(f"节点 {self.node_id} 配置参数解析失败: {e}")
                self.resolved_config = self.config.copy()
            
            # 2. 执行节点逻辑（优先使用 execute 方法）
            result = await self.execute(context)
            
            # 3. 保存输出到上下文
            if result is not None:
                context.set_node_output(self.node_id, result)
            
            self.status = NodeStatus.SUCCESS
            context.log_info(f"节点执行成功: {self.node_id}")
            
            return result
            
        except Exception as e:
            self.status = NodeStatus.FAILED
            context.log_error(f"节点执行失败: {self.node_id} - {str(e)}")
            raise NodeExecutionError(self.node_id, str(e), e)
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.node_id} status={self.status.value}>"
