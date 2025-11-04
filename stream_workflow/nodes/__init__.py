"""内置节点模块"""

from .http_node import HttpNode
from .variable import VariableNode


# 内置节点字典（用于自动注册）
BUILTIN_NODES = {
    'http': HttpNode,
    'variable': VariableNode
}


def auto_register_nodes(engine):
    """
    自动注册所有内置节点
    
    Args:
        engine: WorkflowEngine 实例
        
    Example:
        from stream_workflow import WorkflowEngine
        from stream_workflow.nodes import auto_register_nodes
        
        engine = WorkflowEngine()
        auto_register_nodes(engine)
    """
    for node_type, node_class in BUILTIN_NODES.items():
        engine.register_node_type(node_type, node_class)
    print(f"已自动注册 {len(BUILTIN_NODES)} 个内置节点")


__all__ = [
    # 旧架构节点
    'HttpNode',
    'VariableNode',
    # 工具函数
    'BUILTIN_NODES',
    'auto_register_nodes'
]
