"""工作流引擎核心模块"""

from .node import Node, NodeStatus, register_node, get_registered_nodes
from .context import WorkflowContext
from .workflow import WorkflowEngine
from .parameter import Parameter, ParameterSchema, StreamChunk, FieldSchema, FieldSchemaDef
from .connection import Connection, ConnectionManager
from .exceptions import (
    WorkflowException,
    NodeExecutionError,
    ConfigurationError,
    ConnectionError as WorkflowConnectionError
)

__all__ = [
    # 节点相关
    'Node',
    'NodeStatus',
    'register_node',
    'get_registered_nodes',
    # 上下文和引擎
    'WorkflowContext',
    'WorkflowEngine',
    # 参数系统
    'Parameter',
    'ParameterSchema',
    'StreamChunk',
    'FieldSchema',
    'FieldSchemaDef',
    # 连接系统
    'Connection',
    'ConnectionManager',
    # 异常
    'WorkflowException',
    'NodeExecutionError',
    'ConfigurationError',
    'WorkflowConnectionError'
]
