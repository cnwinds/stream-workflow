"""工作流引擎自定义异常"""


class WorkflowException(Exception):
    """工作流基础异常"""
    pass


class NodeExecutionError(WorkflowException):
    """节点执行异常"""
    def __init__(self, node_id: str, message: str, original_error: Exception = None):
        self.node_id = node_id
        self.original_error = original_error
        super().__init__(f"节点 '{node_id}' 执行失败: {message}")


class ConfigurationError(WorkflowException):
    """配置错误异常"""
    pass


class ConnectionError(WorkflowException):
    """连接错误异常"""
    pass
