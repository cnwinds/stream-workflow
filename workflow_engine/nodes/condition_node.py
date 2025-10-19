"""条件判断节点"""

from typing import Any, Dict
from workflow_engine.core import Node, WorkflowContext, NodeExecutionError


class ConditionNode(Node):
    """
    条件判断节点
    根据条件决定数据流向
    """
    
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行条件判断
        
        配置参数:
            - conditions: 条件列表
            - default_branch: 默认分支（当所有条件都不满足时）
        """
        conditions = self.config.get('conditions', [])
        default_branch = self.config.get('default_branch', 'default')
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        if not input_data:
            raise NodeExecutionError(self.node_id, "没有输入数据")
        
        # 合并输入数据
        merged_input = {}
        for node_id, data in input_data.items():
            if isinstance(data, dict):
                merged_input.update(data)
            else:
                merged_input['value'] = data
        
        # 评估条件
        for condition in conditions:
            branch = condition.get('branch')
            expression = condition.get('expression')
            
            if not branch or not expression:
                continue
            
            try:
                # 评估条件表达式
                if self._evaluate_condition(expression, merged_input):
                    context.log(f"条件满足，选择分支: {branch}")
                    return {
                        'branch': branch,
                        'data': merged_input,
                        'condition': expression
                    }
            except Exception as e:
                context.log(f"条件评估失败: {expression} - {str(e)}", level="WARNING")
        
        # 所有条件都不满足，返回默认分支
        context.log(f"所有条件都不满足，使用默认分支: {default_branch}")
        return {
            'branch': default_branch,
            'data': merged_input,
            'condition': None
        }
    
    def _evaluate_condition(self, expression: str, data: Dict) -> bool:
        """
        评估条件表达式
        
        支持的表达式格式:
            - "key == value"
            - "key > value"
            - "key < value"
            - "key >= value"
            - "key <= value"
            - "key != value"
            - "key in [value1, value2]"
        """
        # 创建安全的执行环境
        safe_globals = {
            '__builtins__': {
                'len': len,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
            }
        }
        safe_globals.update(data)
        
        try:
            result = eval(expression, safe_globals)
            return bool(result)
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"条件表达式评估失败: {expression} - {str(e)}",
                e
            )
