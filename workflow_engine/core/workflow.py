"""工作流引擎实现"""

import asyncio
import yaml
import json
from typing import Dict, Any, List, Type, Callable
from pathlib import Path
from .node import Node, NodeStatus
from .context import WorkflowContext
from .exceptions import ConfigurationError, WorkflowException
from .connection import Connection, ConnectionManager
import logging

class WorkflowEngine:
    """
    工作流引擎
    负责解析配置、管理节点、执行工作流
    """
    
    def __init__(self):
        # 注册的节点类型字典 {节点类型名: 节点类}
        self._node_registry: Dict[str, Type[Node]] = {}
        # 当前加载的工作流配置
        self._workflow_config: Dict[str, Any] = {}
        # 节点实例字典 {节点ID: 节点实例}
        self._nodes: Dict[str, Node] = {}
        # 执行上下文
        self._context: WorkflowContext = None
        # 连接管理器（新架构）
        self._connection_manager = ConnectionManager()
        # 运行状态
        self._running = False
        # 流式任务列表
        self._stream_tasks: List[asyncio.Task] = []
        # sequential/hybrid 节点列表
        self._sequential_nodes: List[str] = []
    
    def register_node_type(self, node_type: str, node_class: Type[Node]):
        """
        注册节点类型
        
        Args:
            node_type: 节点类型名称（在配置文件中使用）
            node_class: 节点类
        """
        if not issubclass(node_class, Node):
            raise ValueError(f"节点类 {node_class} 必须继承自 Node 基类")
        
        self._node_registry[node_type] = node_class
        print(f"已注册节点类型: {node_type} -> {node_class.__name__}")
    
    def load_config(self, config_path: str):
        """
        从文件加载工作流配置
        
        Args:
            config_path: 配置文件路径（支持YAML和JSON）
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise ConfigurationError(f"配置文件不存在: {config_path}")
        
        # 根据文件扩展名选择解析器
        if config_file.suffix in ['.yaml', '.yml']:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._workflow_config = yaml.safe_load(f)
        elif config_file.suffix == '.json':
            with open(config_file, 'r', encoding='utf-8') as f:
                self._workflow_config = json.load(f)
        else:
            raise ConfigurationError(f"不支持的配置文件格式: {config_file.suffix}")
        
        print(f"已加载配置文件: {config_path}")
        self._validate_config()
        self._build_nodes()
        self._build_connections()  # 新架构：构建连接
    
    def load_config_dict(self, config: Dict[str, Any]):
        """
        从字典加载工作流配置
        
        Args:
            config: 配置字典
        """
        self._workflow_config = config
        self._validate_config()
        self._build_nodes()
        self._build_connections()  # 新架构：构建连接
    
    def _validate_config(self):
        """验证配置文件格式"""
        if 'workflow' not in self._workflow_config:
            raise ConfigurationError("配置文件缺少 'workflow' 字段")
        
        workflow = self._workflow_config['workflow']
        
        if 'name' not in workflow:
            raise ConfigurationError("配置文件缺少 'workflow.name' 字段")
        
        if 'nodes' not in workflow:
            raise ConfigurationError("配置文件缺少 'workflow.nodes' 字段")
        
        # 验证节点配置
        nodes = workflow['nodes']
        if not isinstance(nodes, list) or len(nodes) == 0:
            raise ConfigurationError("'workflow.nodes' 必须是非空列表")
        
        # 检查节点ID唯一性
        node_ids = set()
        for node_config in nodes:
            if 'id' not in node_config:
                raise ConfigurationError("节点配置缺少 'id' 字段")
            
            if 'type' not in node_config:
                raise ConfigurationError(f"节点 '{node_config['id']}' 缺少 'type' 字段")
            
            if node_config['id'] in node_ids:
                raise ConfigurationError(f"节点ID重复: {node_config['id']}")
            
            node_ids.add(node_config['id'])
    
    def _build_nodes(self):
        """根据配置构建节点实例"""
        self._nodes.clear()
        
        # 从全局注册表获取节点类型
        from .node import get_registered_nodes
        global_registry = get_registered_nodes()
        
        workflow = self._workflow_config['workflow']
        
        for node_config in workflow['nodes']:
            node_id = node_config['id']
            node_type = node_config['type']
            
            # 首先检查本地注册表，然后检查全局注册表
            if node_type in self._node_registry:
                node_class = self._node_registry[node_type]
            elif node_type in global_registry:
                node_class = global_registry[node_type]
            else:
                raise ConfigurationError(
                    f"未知的节点类型: '{node_type}' (节点ID: {node_id})"
                )
            
            # 创建节点实例（传入连接管理器）
            node_instance = node_class(node_id, node_config, self._connection_manager)
            
            self._nodes[node_id] = node_instance
    
    def _build_connections(self):
        """构建参数连接并验证类型匹配（新架构）"""
        connections = self._workflow_config['workflow'].get('connections', [])
        
        if not connections:
            print("配置中没有定义连接，跳过连接构建")
            return
        
        for conn_config in connections:
            # 解析 "vad.audio_stream" -> ("vad", "audio_stream")
            if '.' not in conn_config['from'] or '.' not in conn_config['to']:
                raise ConfigurationError(
                    f"连接配置格式错误: {conn_config}\n"
                    f"格式应为: node_id.param_name"
                )
            
            source_node_id, source_param_name = conn_config['from'].split('.', 1)
            target_node_id, target_param_name = conn_config['to'].split('.', 1)
            
            # 检查节点是否存在
            if source_node_id not in self._nodes:
                raise ConfigurationError(f"源节点不存在: {source_node_id}")
            if target_node_id not in self._nodes:
                raise ConfigurationError(f"目标节点不存在: {target_node_id}")
            
            source_node = self._nodes[source_node_id]
            target_node = self._nodes[target_node_id]
            
            # 检查参数是否存在
            if source_param_name not in source_node.outputs:
                raise ConfigurationError(
                    f"节点 {source_node_id} 没有输出参数: {source_param_name}\n"
                    f"可用输出: {list(source_node.outputs.keys())}"
                )
            if target_param_name not in target_node.inputs:
                raise ConfigurationError(
                    f"节点 {target_node_id} 没有输入参数: {target_param_name}\n"
                    f"可用输入: {list(target_node.inputs.keys())}"
                )
            
            # 创建连接（会自动验证参数结构匹配和设置连接属性）
            self._connection_manager.add_connection(
                source_node_id, source_param_name, source_node,
                target_node_id, target_param_name, target_node
            )
            
    
    def _is_streaming_workflow(self) -> bool:
        """
        检查是否为流式工作流
        
        流式工作流的特征：
        1. 所有连接都是流式的
        2. 允许存在循环依赖（反馈回路）
        
        Returns:
            True 如果是流式工作流
        """
        # 检查是否所有节点都只有流式参数
        for node in self._nodes.values():
            # 检查是否有非流式输入或输出参数
            for param in node.inputs.values():
                if not param.is_streaming:
                    return False
            for param in node.outputs.values():
                if not param.is_streaming:
                    return False
        
        # 如果所有参数都是流式的，则认为是流式工作流
        return len(self._nodes) > 0
    
    def _transfer_non_streaming_outputs(self, node: Node):
        """
        传递非流式输出值到连接的下游节点
        
        Args:
            node: 源节点
        """
        # 遍历节点的所有输出参数
        for param_name, param in node.outputs.items():
            if not param.is_streaming and param.value is not None:
                # 通过连接管理器传递值
                self._connection_manager.transfer_value(node.node_id, param_name, param.value)
    
    async def start(self, initial_data: Dict[str, Any] = None) -> WorkflowContext:
        """
        启动工作流（准备执行环境，启动流式任务）
        
        准备策略：
        1. 分类节点：sequential/hybrid vs streaming
        2. 为所有流式输入启动消费任务（后台异步运行，不等待）
        
        Args:
            initial_data: 初始全局变量
            
        Returns:
            执行上下文（包含所有节点输出和日志）
        """
        if not self._nodes:
            raise WorkflowException("没有可执行的节点，请先加载配置")
        
        if self._running:
            raise WorkflowException("工作流已在运行中")
        
        # 创建新的执行上下文
        context = WorkflowContext()
        self._context = context
        self._running = True
        
        # 设置初始数据
        if initial_data:
            for key, value in initial_data.items():
                context.set_global_var(key, value)
        
        workflow_name = self._workflow_config['workflow']['name']
        
        context.log_info(f"开始启动工作流: {workflow_name}")

        try:
            # 1. 分类节点
            self._sequential_nodes = []  # 需要顺序执行的节点（sequential 和 hybrid）
            streaming_nodes = []   # 纯流式节点
            
            for node_id, node in self._nodes.items():
                if node.EXECUTION_MODE == 'streaming':
                    streaming_nodes.append(node_id)
                    context.log_info(f"节点 {node_id} [流式模式]")
                elif node.EXECUTION_MODE == 'hybrid':
                    self._sequential_nodes.append(node_id)
                    context.log_info(f"节点 {node_id} [混合模式]")
                else:  # sequential
                    self._sequential_nodes.append(node_id)
                    context.log_info(f"节点 {node_id} [顺序模式]")
            
            # 2. 初始化所有节点
            for node_id, node in self._nodes.items():
                try:
                    await node.initialize(context)
                    context.log_info(f"节点 {node_id} 初始化完成")
                except Exception as e:
                    context.log_error(f"节点 {node_id} 初始化失败: {e}")
                    raise
            
            # 3. 启动所有异步节点
            for node_id, node in self._nodes.items():
                if node.EXECUTION_MODE == 'streaming' or node.EXECUTION_MODE == 'hybrid':
                    task = asyncio.create_task(node.run(context))
                    self._stream_tasks.append(task)
            
            # 4. 为所有流式输入启动消费任务（后台异步运行）
            self._stream_tasks = []
            for node_id, node in self._nodes.items():
                for param_name, param in node.inputs.items():
                    if param.is_streaming:
                        task = asyncio.create_task(node.consume_stream(param_name))
                        self._stream_tasks.append(task)
                        context.log_info(f"启动流式消费: {node_id}.{param_name}")

            context.log_info(f"Sequential/Hybrid 节点: {', '.join(self._sequential_nodes)}")
            context.log_info(f"工作流启动完成: {workflow_name}")
            
        except Exception as e:
            context.log_error(f"工作流启动失败: {str(e)}")
            raise
        
        return context
    
    async def stop(self):
        """
        停止工作流（优雅关闭所有节点）
        """
        if not self._running:
            return
        
        self._running = False
        
        # 发送结束信号到所有流式队列
        for node in self._nodes.values():
            for param in node.inputs.values():
                if param.is_streaming and param.stream_queue:
                    await param.stream_queue.put(None)
        
        # 取消所有流式任务
        for task in self._stream_tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务完成
        if self._stream_tasks:
            await asyncio.gather(*self._stream_tasks, return_exceptions=True)
        
        # 关闭所有节点
        for node in self._nodes.values():
            try:
                await node.shutdown()
            except Exception as e:
                if self._context:
                    self._context.log_error(f"关闭节点 {node.node_id} 失败: {e}")
        
        if self._context:
            self._context.log_info("工作流已停止")
    
    async def execute(self, **kwargs) -> None:
        """
        按配置顺序执行所有 sequential/hybrid 节点
        
        注意：必须先调用 start() 方法来准备执行环境
        
        Args:
            **kwargs: 传递给节点的参数
        
        Example:
            context = await engine.start()
            await engine.execute()
            await engine.execute(url='https://api.com', message='你好')
        """
        if not self._context:
            raise WorkflowException("工作流未启动，请先调用 start() 方法")
        
        workflow_config = self._workflow_config['workflow'].get('config', {})
        continue_on_error = workflow_config.get('continue_on_error', False)
        
        self._context.log_info("开始执行所有 sequential/hybrid 节点")
        
        try:
            # 按配置顺序执行 sequential/hybrid 节点
            for node_id in self._sequential_nodes:
                node = self._nodes[node_id]
                try:
                    # 临时更新节点配置（传入运行时参数）
                    original_config = node.config.copy()
                    if kwargs:
                        node.config.update(kwargs)
                    
                    await node._execute_async(self._context)
                    
                    # 恢复原配置
                    node.config = original_config
                    
                    # 传递非流式输出值到连接的下游节点
                    self._transfer_non_streaming_outputs(node)
                    self._context.log_info(f"节点 {node_id} 执行完成")
                except Exception as e:
                    # 确保恢复原配置
                    if 'original_config' in locals():
                        node.config = original_config
                    self._context.log_error(f"节点 {node_id} 执行失败: {e}")
                    if not continue_on_error:
                        raise
            
            workflow_name = self._workflow_config['workflow']['name']
            self._context.log_info(f"工作流执行完成: {workflow_name}")
            
        except Exception as e:
            self._context.log_error(f"工作流执行失败: {str(e)}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取工作流运行状态
        
        Returns:
            状态字典
        """
        return {
            'running': self._running,
            'workflow_name': self._workflow_config.get('workflow', {}).get('name', 'Unknown'),
            'nodes': {
                node_id: {
                    'status': node.status.value,
                    'type': node.__class__.__name__,
                    'mode': node.EXECUTION_MODE
                }
                for node_id, node in self._nodes.items()
            },
            'context': {
                'has_errors': bool(self._context and self._context.get_logs()),
                'nodes_completed': len([n for n in self._nodes.values() if n.status == NodeStatus.SUCCESS])
            } if self._context else None
        }
    
    def get_node(self, node_id: str) -> Node:
        """获取节点实例"""
        return self._nodes.get(node_id)
    
    def get_all_nodes(self) -> Dict[str, Node]:
        """获取所有节点"""
        return self._nodes.copy()
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        if not self._workflow_config:
            return {}
        
        workflow = self._workflow_config['workflow']
        return {
            'name': workflow.get('name'),
            'description': workflow.get('description', ''),
            'version': workflow.get('version', '1.0.0'),
            'node_count': len(self._nodes)
        }
    
    def add_external_connection(self, source_node: str, source_param: str, external_handler: Callable) -> bool:
        """添加外部连接"""
        node = self.get_node(source_node)
        if not node:
            return False
        source_schema = node.outputs[source_param].schema
        if not source_schema:
            return False
        return self._connection_manager.add_external_connection(source_node, source_param, source_schema, external_handler)
    
    def get_connection_manager(self) -> ConnectionManager:
        """获取连接管理器"""
        return self._connection_manager
