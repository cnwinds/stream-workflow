"""合并节点"""

from typing import Any, Dict, List
from workflow_engine.core import Node, WorkflowContext


class MergeNode(Node):
    """
    合并节点
    将多个输入节点的数据合并成一个输出
    """
    
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行数据合并
        
        配置参数:
            - strategy: 合并策略
              - "merge": 合并字典（默认）
              - "concat": 连接列表
              - "first": 只取第一个输入
              - "last": 只取最后一个输入
        """
        strategy = self.config.get('strategy', 'merge')
        
        # 获取所有输入数据
        input_data = self.get_input_data(context)
        
        if not input_data:
            context.log("没有输入数据，返回空字典")
            return {}
        
        # 根据策略合并数据
        if strategy == 'merge':
            result = self._merge_dicts(input_data)
        elif strategy == 'concat':
            result = self._concat_lists(input_data)
        elif strategy == 'first':
            result = list(input_data.values())[0]
        elif strategy == 'last':
            result = list(input_data.values())[-1]
        else:
            result = input_data
        
        context.log(f"使用策略 '{strategy}' 合并了 {len(input_data)} 个输入")
        return result
    
    def _merge_dicts(self, input_data: Dict[str, Any]) -> Dict:
        """合并字典"""
        result = {}
        
        for node_id, data in input_data.items():
            if isinstance(data, dict):
                result.update(data)
            else:
                result[node_id] = data
        
        return result
    
    def _concat_lists(self, input_data: Dict[str, Any]) -> List:
        """连接列表"""
        result = []
        
        for node_id, data in input_data.items():
            if isinstance(data, list):
                result.extend(data)
            else:
                result.append(data)
        
        return result
