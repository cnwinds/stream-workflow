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
    
    def get_node_output(self, node_id: str, field: str = None) -> Any:
        """
        获取指定节点的输出
        
        Args:
            node_id: 节点ID
            field: 可选的字段路径，支持嵌套访问，如 "data.score" 或 "result.items[0].name"
            
        Returns:
            节点输出数据或指定字段的值
            
        Examples:
            context.get_node_output("start")  # 获取整个输出
            context.get_node_output("start", "score")  # 获取 output["score"]
            context.get_node_output("start", "data.score")  # 获取 output["data"]["score"]
        """
        output = self._node_outputs.get(node_id)
        
        if output is None or field is None:
            return output
        
        # 支持嵌套字段访问
        return self._get_nested_value(output, field)
    
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
    
    def _get_nested_value(self, data: Any, path: str) -> Any:
        """
        从嵌套数据结构中获取值
        
        Args:
            data: 数据对象（字典、列表等）
            path: 字段路径，如 "data.score" 或 "items[0].name"
            
        Returns:
            字段值
            
        Raises:
            KeyError, IndexError, TypeError: 如果路径无效
        """
        if not path:
            return data
        
        # 支持点号分隔和数组索引
        import re
        
        # 分割路径：支持 "data.items[0].name" 这样的路径
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]  # 过滤空字符串
        
        current = data
        for part in parts:
            if part.isdigit():  # 数组索引
                current = current[int(part)]
            elif isinstance(current, dict):  # 字典访问
                current = current[part]
            elif hasattr(current, part):  # 对象属性访问
                current = getattr(current, part)
            else:
                raise KeyError(f"无法访问路径 '{path}' 中的字段 '{part}'")
        
        return current
