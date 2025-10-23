"""数据转换节点"""

from typing import Any, Dict
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, NodeExecutionError, register_node

@register_node('transform_node')
class TransformNode(Node):
    """
    数据转换节点
    
    功能：支持多种数据转换操作
    
    输入参数：
        input_data: 输入数据（可选，可以从配置文件或输入获取）
            - data: any - 要转换的数据
            - operation: string - 转换操作类型
            - config: dict - 操作相关配置
    
    输出参数：
        output: 转换后的数据
            - result: any - 转换结果
            - operation: string - 执行的操作类型
            - success: boolean - 转换是否成功
    
    配置参数：
        operation: string - 转换操作类型
            - "extract": 提取字段
            - "map": 映射/重命名字段
            - "filter": 过滤数据
            - "aggregate": 聚合数据
            - "custom": 自定义Python表达式
        config: dict - 操作相关的配置
    """
    
    # 节点执行模式：顺序执行，任务驱动
    EXECUTION_MODE = 'sequential'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=False,
            schema={
                "data": "any",
                "operation": "string",
                "config": "dict"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "output": ParameterSchema(
            is_streaming=False,
            schema={
                "result": "any",
                "operation": "string",
                "success": "boolean"
            }
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
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
        # 1. 从配置文件获取默认值（使用简化的 get_config 方法）
        operation = self.get_config('config.operation') or self.get_config('operation')
        op_config = self.get_config('config.config') or self.get_config('config', {})
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            input_data = self.get_input_value('input_data')
            if input_data:
                data = input_data.get('data')
                operation = input_data.get('operation', operation)
                op_config = input_data.get('config', op_config)
        except (ValueError, KeyError):
            # 没有输入参数，使用配置文件的值
            pass
        
        if not operation:
            raise NodeExecutionError(self.node_id, "缺少必需参数: operation")
        
        # 3. 获取要转换的数据
        if 'data' in locals() and data is not None:
            # 使用输入参数中的数据
            merged_input = data
        else:
            # 使用旧架构的输入数据（向后兼容）
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
        
        # 4. 根据操作类型执行转换
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
            
            # 5. 设置输出值
            self.set_output_value('output', {
                'result': result,
                'operation': operation,
                'success': True
            })
            
            context.log_info(f"数据转换完成，操作类型: {operation}")
            return {
                'result': result,
                'operation': operation,
                'success': True
            }
            
        except Exception as e:
            # 设置失败输出
            self.set_output_value('output', {
                'result': None,
                'operation': operation,
                'success': False
            })
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
