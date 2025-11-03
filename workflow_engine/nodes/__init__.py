"""内置节点模块"""

from .start_node import StartNode
from .http_node import HttpNode
from .transform_node import TransformNode
from .condition_node import ConditionNode
from .merge_node import MergeNode
from .output_node import OutputNode


# 内置节点字典（用于自动注册）
BUILTIN_NODES = {
    # 旧架构节点
    'start': StartNode,
    'output': OutputNode,
    'http': HttpNode,
    'transform': TransformNode,
    'condition': ConditionNode,
    'merge': MergeNode
}


def auto_register_nodes(engine):
    """
    自动注册所有内置节点
    
    Args:
        engine: WorkflowEngine 实例
        
    Example:
        from workflow_engine import WorkflowEngine
        from workflow_engine.nodes import auto_register_nodes
        
        engine = WorkflowEngine()
        auto_register_nodes(engine)
    """
    for node_type, node_class in BUILTIN_NODES.items():
        engine.register_node_type(node_type, node_class)
    print(f"已自动注册 {len(BUILTIN_NODES)} 个内置节点")


__all__ = [
    # 旧架构节点
    'StartNode',
    'HttpNode',
    'TransformNode',
    'ConditionNode',
    'MergeNode',
    'OutputNode',
    # 工具函数
    'BUILTIN_NODES',
    'auto_register_nodes'
]
