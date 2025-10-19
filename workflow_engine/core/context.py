"""工作流执行上下文"""

from typing import Any, Dict, Optional
from datetime import datetime


class WorkflowContext:
    """
    工作流执行上下文
    用于在节点之间传递数据和状态
    """
    
    def __init__(self):
        # 存储每个节点的输出结果
        self._node_outputs: Dict[str, Any] = {}
        # 全局变量
        self._global_vars: Dict[str, Any] = {}
        # 执行开始时间
        self.start_time = datetime.now()
        # 执行日志
        self._logs: list = []
    
    def set_node_output(self, node_id: str, output: Any):
        """设置节点的输出"""
        self._node_outputs[node_id] = output
        self.log(f"节点 '{node_id}' 输出已保存")
    
    def get_node_output(self, node_id: str) -> Any:
        """获取指定节点的输出"""
        return self._node_outputs.get(node_id)
    
    def set_global_var(self, key: str, value: Any):
        """设置全局变量"""
        self._global_vars[key] = value
    
    def get_global_var(self, key: str, default: Any = None) -> Any:
        """获取全局变量"""
        return self._global_vars.get(key, default)
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        log_entry = {
            'timestamp': datetime.now(),
            'level': level,
            'message': message
        }
        self._logs.append(log_entry)
    
    def get_logs(self) -> list:
        """获取所有日志"""
        return self._logs
    
    def get_all_outputs(self) -> Dict[str, Any]:
        """获取所有节点的输出"""
        return self._node_outputs.copy()
    
    def clear(self):
        """清空上下文"""
        self._node_outputs.clear()
        self._global_vars.clear()
        self._logs.clear()
        self.start_time = datetime.now()
