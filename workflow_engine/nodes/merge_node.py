"""合并节点"""

from typing import Any, Dict, List
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, register_node

@register_node('merge_node')
class MergeNode(Node):
    """
    合并节点
    
    功能：将多个输入节点的数据合并成一个输出
    
    输入参数：
        input_data: 输入数据（可选，可以从配置文件或输入获取）
            - data: any - 要合并的数据
            - strategy: string - 合并策略
    
    输出参数：
        output: 合并后的数据
            - result: any - 合并结果
            - strategy: string - 使用的合并策略
            - input_count: integer - 输入数据数量
    
    配置参数：
        strategy: string - 合并策略
            - "merge": 合并字典（默认）
            - "concat": 连接列表
            - "first": 只取第一个输入
            - "last": 只取最后一个输入
    """
    
    # 节点执行模式：顺序执行，任务驱动
    EXECUTION_MODE = 'sequential'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=False,
            schema={
                "data": "any",
                "strategy": "string"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "output": ParameterSchema(
            is_streaming=False,
            schema={
                "result": "any",
                "strategy": "string",
                "input_count": "integer"
            }
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
        """
        执行数据合并
        
        配置参数:
            - strategy: 合并策略
              - "merge": 合并字典（默认）
              - "concat": 连接列表
              - "first": 只取第一个输入
              - "last": 只取最后一个输入
        """
        # 1. 从配置文件获取默认值（使用简化的 get_config 方法）
        strategy = self.get_config('config.strategy') or self.get_config('strategy', 'merge')
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            input_data = self.get_input_value('input_data')
            if input_data:
                data = input_data.get('data')
                strategy = input_data.get('strategy', strategy)
        except (ValueError, KeyError):
            # 没有输入参数，使用配置文件的值
            pass
        
        # 3. 获取要合并的数据
        if 'data' in locals() and data is not None:
            # 使用输入参数中的数据
            input_data = {'input': data}
        else:
            # 使用旧架构的输入数据（向后兼容）
            input_data = self.get_input_data(context)
        
        if not input_data:
            context.log_info("没有输入数据，返回空字典")
            result = {}
            input_count = 0
        else:
            # 4. 根据策略合并数据
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
            
            input_count = len(input_data)
        
        # 5. 设置输出值
        self.set_output_value('output', {
            'result': result,
            'strategy': strategy,
            'input_count': input_count
        })
        
        context.log_info(f"使用策略 '{strategy}' 合并了 {input_count} 个输入")
        return {
            'result': result,
            'strategy': strategy,
            'input_count': input_count
        }
    
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
