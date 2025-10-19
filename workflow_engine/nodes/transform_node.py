"""数据转换节点"""

from typing import Any, Dict
from workflow_engine.core import Node, WorkflowContext, NodeExecutionError


class TransformNode(Node):
    """
    数据转换节点
    支持多种数据转换操作
    """
    
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行数据转换
        
        配置参数:
            - operation: 转换操作类型
              - "extract": 提取字段
              - "map": 映射/重命名字段
              - "filter": 过滤数据
              - "aggregate": 聚合数据
              - "custom": 自定义Python表达式
            - config: 操作相关的配置
        """
        operation = self.config.get('operation')
        op_config = self.config.get('config', {})
        
        if not operation:
            raise NodeExecutionError(self.node_id, "缺少必需参数: operation")
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        if not input_data:
            raise NodeExecutionError(self.node_id, "没有输入数据")
        
        # 合并所有输入数据
        merged_input = {}
        for node_id, data in input_data.items():
            if isinstance(data, dict):
                merged_input.update(data)
            else:
                merged_input[node_id] = data
        
        # 根据操作类型执行转换
        try:
            if operation == "extract":
                result = self._extract(merged_input, op_config)
            elif operation == "map":
                result = self._map_fields(merged_input, op_config)
            elif operation == "filter":
                result = self._filter_data(merged_input, op_config)
            elif operation == "aggregate":
                result = self._aggregate(merged_input, op_config)
            elif operation == "custom":
                result = self._custom_transform(merged_input, op_config, context)
            else:
                raise NodeExecutionError(
                    self.node_id,
                    f"不支持的转换操作: {operation}"
                )
            
            context.log(f"数据转换完成，操作类型: {operation}")
            return result
            
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"数据转换失败: {str(e)}",
                e
            )
    
    def _extract(self, data: Dict, config: Dict) -> Dict:
        """提取指定字段"""
        fields = config.get('fields', [])
        result = {}
        
        for field in fields:
            if field in data:
                result[field] = data[field]
            elif '.' in field:  # 支持嵌套字段
                value = data
                for key in field.split('.'):
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        value = None
                        break
                if value is not None:
                    result[field] = value
        
        return result
    
    def _map_fields(self, data: Dict, config: Dict) -> Dict:
        """映射/重命名字段"""
        mapping = config.get('mapping', {})
        result = {}
        
        for old_key, new_key in mapping.items():
            if old_key in data:
                result[new_key] = data[old_key]
        
        # 保留未映射的字段
        if config.get('keep_unmapped', False):
            for key, value in data.items():
                if key not in mapping:
                    result[key] = value
        
        return result
    
    def _filter_data(self, data: Dict, config: Dict) -> Dict:
        """过滤数据"""
        conditions = config.get('conditions', [])
        result = data.copy()
        
        # 简单的键值过滤
        for condition in conditions:
            key = condition.get('key')
            value = condition.get('value')
            operator = condition.get('operator', '==')
            
            if key in result:
                if operator == '==' and result[key] != value:
                    result.pop(key)
                elif operator == '!=' and result[key] == value:
                    result.pop(key)
        
        return result
    
    def _aggregate(self, data: Dict, config: Dict) -> Any:
        """聚合数据"""
        operation = config.get('operation', 'sum')
        field = config.get('field')
        
        if field and field in data:
            values = data[field]
            if isinstance(values, list):
                if operation == 'sum':
                    return sum(values)
                elif operation == 'avg':
                    return sum(values) / len(values) if values else 0
                elif operation == 'count':
                    return len(values)
                elif operation == 'max':
                    return max(values) if values else None
                elif operation == 'min':
                    return min(values) if values else None
        
        return data
    
    def _custom_transform(self, data: Dict, config: Dict, context: WorkflowContext) -> Any:
        """自定义转换（使用Python表达式）"""
        expression = config.get('expression')
        
        if not expression:
            raise NodeExecutionError(self.node_id, "custom操作缺少expression参数")
        
        # 创建安全的执行环境
        safe_globals = {
            '__builtins__': {
                'len': len,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
                'int': int,
                'float': float,
                'str': str,
                'list': list,
                'dict': dict,
            },
            'data': data,
            'context': context
        }
        
        try:
            result = eval(expression, safe_globals)
            return result
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"自定义表达式执行失败: {str(e)}",
                e
            )
