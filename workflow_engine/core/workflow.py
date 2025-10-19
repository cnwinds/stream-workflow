"""工作流引擎实现"""

import yaml
import json
from typing import Dict, Any, List, Type
from pathlib import Path
from .node import Node, NodeStatus
from .context import WorkflowContext
from .exceptions import ConfigurationError, WorkflowException


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
    
    def load_config_dict(self, config: Dict[str, Any]):
        """
        从字典加载工作流配置
        
        Args:
            config: 配置字典
        """
        self._workflow_config = config
        self._validate_config()
        self._build_nodes()
    
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
            
            # 创建节点实例
            node_class = self._node_registry[node_type]
            node_instance = node_class(node_id, node_config)
            
            self._nodes[node_id] = node_instance
            print(f"已创建节点: {node_id} (类型: {node_type})")
    
    def _get_execution_order(self) -> List[str]:
        """
        计算节点执行顺序（拓扑排序）
        
        Returns:
            节点ID列表，按执行顺序排列
        """
        # 构建依赖图
        in_degree = {}  # 入度
        graph = {}  # 邻接表
        
        for node_id, node in self._nodes.items():
            in_degree[node_id] = len(node.inputs)
            graph[node_id] = []
        
        # 构建邻接表
        for node_id, node in self._nodes.items():
            for input_node_id in node.inputs:
                if input_node_id not in self._nodes:
                    raise ConfigurationError(
                        f"节点 '{node_id}' 的输入节点 '{input_node_id}' 不存在"
                    )
                graph[input_node_id].append(node_id)
        
        # 拓扑排序
        execution_order = []
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        
        while queue:
            current = queue.pop(0)
            execution_order.append(current)
            
            # 减少相邻节点的入度
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否存在循环依赖
        if len(execution_order) != len(self._nodes):
            raise ConfigurationError("工作流存在循环依赖")
        
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
