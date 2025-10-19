"""工作流引擎实现"""

import asyncio
import yaml
import json
from typing import Dict, Any, List, Type
from pathlib import Path
from .node import Node, NodeStatus
from .context import WorkflowContext
from .exceptions import ConfigurationError, WorkflowException
from .connection import Connection, ConnectionManager


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
        
        workflow = self._workflow_config['workflow']
        
        for node_config in workflow['nodes']:
            node_id = node_config['id']
            node_type = node_config['type']
            
            # 检查节点类型是否已注册
            if node_type not in self._node_registry:
                raise ConfigurationError(
                    f"未知的节点类型: '{node_type}' (节点ID: {node_id})"
                )
            
            # 创建节点实例（传入连接管理器）
            node_class = self._node_registry[node_type]
            node_instance = node_class(node_id, node_config, self._connection_manager)
            
            self._nodes[node_id] = node_instance
            print(f"已创建节点: {node_id} (类型: {node_type})")
    
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
            
            # 获取参数 schema
            source_schema = source_node.outputs[source_param_name].schema
            target_schema = target_node.inputs[target_param_name].schema
            
            # 创建连接（会自动验证参数结构匹配）
            conn = Connection(
                source_node_id, source_param_name,
                target_node_id, target_param_name,
                source_schema, target_schema
            )
            
            # 如果是流式连接，关联队列
            if conn.is_streaming:
                conn.target_queue = target_node.inputs[target_param_name].stream_queue
            else:
                # 如果是非流式连接，保存目标参数的引用
                conn.target_param_ref = target_node.inputs[target_param_name]
            
            self._connection_manager.add_connection(conn)
            
            print(f"连接已建立: {source_node_id}.{source_param_name} -> "
                  f"{target_node_id}.{target_param_name}")
    
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
    
    def _get_execution_order(self, node_ids: List[str] = None) -> List[str]:
        """
        计算节点执行顺序（拓扑排序）- 只考虑非流式连接
        
        Args:
            node_ids: 需要排序的节点ID列表，如果为None则使用所有节点
        
        Returns:
            节点ID列表，按执行顺序排列
        """
        if node_ids is None:
            node_ids = list(self._nodes.keys())
        
        # 构建依赖图（只使用非流式连接）
        in_degree = {}  # 入度
        graph = {}  # 邻接表
        
        # 初始化入度和图
        for node_id in node_ids:
            in_degree[node_id] = 0
            graph[node_id] = []
        
        # 只使用非流式连接构建依赖图
        for conn in self._connection_manager.get_data_connections():
            source_node_id = conn.source[0]
            target_node_id = conn.target[0]
            
            # 只考虑在 node_ids 范围内的节点
            if source_node_id in node_ids and target_node_id in node_ids:
                in_degree[target_node_id] += 1
                if target_node_id not in graph[source_node_id]:
                    graph[source_node_id].append(target_node_id)
        
        # 旧架构兼容：基于 _legacy_inputs
        for node_id in node_ids:
            node = self._nodes[node_id]
            if hasattr(node, '_legacy_inputs') and node._legacy_inputs:
                for input_node_id in node._legacy_inputs:
                    if input_node_id not in self._nodes:
                        raise ConfigurationError(
                            f"节点 '{node_id}' 的输入节点 '{input_node_id}' 不存在"
                        )
                    if input_node_id in node_ids:
                        in_degree[node_id] += 1
                        if node_id not in graph[input_node_id]:
                            graph[input_node_id].append(node_id)
        
        # Kahn 算法拓扑排序
        execution_order = []
        queue = [node_id for node_id in node_ids if in_degree[node_id] == 0]
        
        while queue:
            current = queue.pop(0)
            execution_order.append(current)
            
            # 减少相邻节点的入度
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否存在循环依赖
        if len(execution_order) != len(node_ids):
            raise ConfigurationError("工作流存在循环依赖（非流式连接）")
        
        return execution_order
    
    def execute(self, initial_data: Dict[str, Any] = None) -> WorkflowContext:
        """
        执行工作流
        
        Args:
            initial_data: 初始全局变量
            
        Returns:
            执行上下文（包含所有节点输出和日志）
        """
        if not self._nodes:
            raise WorkflowException("没有可执行的节点，请先加载配置")
        
        # 创建新的执行上下文
        self._context = WorkflowContext()
        
        # 设置初始数据
        if initial_data:
            for key, value in initial_data.items():
                self._context.set_global_var(key, value)
        
        workflow_name = self._workflow_config['workflow']['name']
        self._context.log(f"开始执行工作流: {workflow_name}")
        
        try:
            # 获取执行顺序
            execution_order = self._get_execution_order()
            self._context.log(f"执行顺序: {' -> '.join(execution_order)}")
            
            # 按顺序执行节点
            for node_id in execution_order:
                node = self._nodes[node_id]
                node.run(self._context)
            
            self._context.log(f"工作流执行完成: {workflow_name}", level="SUCCESS")
            
        except Exception as e:
            self._context.log(f"工作流执行失败: {str(e)}", level="ERROR")
            raise
        
        return self._context
    
    async def execute_async(self, initial_data: Dict[str, Any] = None) -> WorkflowContext:
        """
        异步执行工作流（混合执行模式）
        
        执行策略：
        1. 分类节点：sequential/hybrid vs streaming
        2. 为所有流式输入启动消费任务（后台运行）
        3. 对 sequential/hybrid 节点按拓扑顺序执行
        4. 等待所有流式任务完成（或超时）
        
        Args:
            initial_data: 初始全局变量
            
        Returns:
            执行上下文（包含所有节点输出和日志）
        """
        if not self._nodes:
            raise WorkflowException("没有可执行的节点，请先加载配置")
        
        # 创建新的执行上下文
        context = WorkflowContext()
        
        # 设置初始数据
        if initial_data:
            for key, value in initial_data.items():
                context.set_global_var(key, value)
        
        workflow_name = self._workflow_config['workflow']['name']
        workflow_config = self._workflow_config['workflow'].get('config', {})
        stream_timeout = workflow_config.get('stream_timeout', 300)
        continue_on_error = workflow_config.get('continue_on_error', False)
        
        context.log(f"开始执行工作流: {workflow_name}")
        
        try:
            # 1. 分类节点
            sequential_nodes = []  # 需要顺序执行的节点（sequential 和 hybrid）
            streaming_nodes = []   # 纯流式节点
            
            for node_id, node in self._nodes.items():
                if node.EXECUTION_MODE == 'streaming':
                    streaming_nodes.append(node_id)
                    context.log(f"节点 {node_id} [流式模式]")
                elif node.EXECUTION_MODE == 'hybrid':
                    sequential_nodes.append(node_id)
                    context.log(f"节点 {node_id} [混合模式]")
                else:  # sequential
                    sequential_nodes.append(node_id)
                    context.log(f"节点 {node_id} [顺序模式]")
            
            # 2. 为所有流式输入启动消费任务（包括 streaming 和 hybrid 节点）
            stream_tasks = []
            for node_id, node in self._nodes.items():
                for param_name, param in node.inputs.items():
                    if param.is_streaming:
                        task = asyncio.create_task(node.consume_stream(param_name))
                        stream_tasks.append(task)
                        context.log(f"启动流式消费: {node_id}.{param_name}")
            
            # 3. 拓扑排序（只对 sequential/hybrid 节点排序）
            if sequential_nodes:
                execution_order = self._get_execution_order(sequential_nodes)
                context.log(f"Sequential/Hybrid 执行顺序: {' -> '.join(execution_order)}")
            else:
                execution_order = []
                context.log("没有 sequential/hybrid 节点，跳过拓扑排序")
            
            # 4. 按顺序执行 sequential/hybrid 节点
            for node_id in execution_order:
                node = self._nodes[node_id]
                try:
                    await node.run_async(context)
                    # 传递非流式输出值到连接的下游节点
                    self._transfer_non_streaming_outputs(node)
                    context.log(f"节点 {node_id} 执行完成")
                except Exception as e:
                    context.log(f"节点 {node_id} 执行失败: {e}", level="ERROR")
                    if not continue_on_error:
                        raise
            
            # 5. 等待所有流式任务完成（或超时）
            if stream_tasks:
                context.log(f"等待流式任务完成（超时: {stream_timeout}秒）")
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*stream_tasks, return_exceptions=True),
                        timeout=stream_timeout
                    )
                except asyncio.TimeoutError:
                    context.log("流式任务超时", level="WARNING")
            
            context.log(f"工作流执行完成: {workflow_name}", level="SUCCESS")
            
        except Exception as e:
            context.log(f"工作流执行失败: {str(e)}", level="ERROR")
            raise
        finally:
            # 清理：发送结束信号到所有流式队列
            for node in self._nodes.values():
                for param in node.inputs.values():
                    if param.is_streaming and param.stream_queue:
                        await param.stream_queue.put(None)
        
        return context
    
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
