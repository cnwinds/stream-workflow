"""
Python工作流引擎框架

一个类似n8n的工作流引擎，支持通过配置文件定义和执行复杂的数据处理流程。
"""

__version__ = "1.0.6"

from .core import (
    Node,
    NodeStatus,
    WorkflowContext,
    WorkflowEngine,
    WorkflowException,
    NodeExecutionError,
    ConfigurationError
)

__all__ = [
    'Node',
    'NodeStatus',
    'WorkflowContext',
    'WorkflowEngine',
    'WorkflowException',
    'NodeExecutionError',
    'ConfigurationError'
]
