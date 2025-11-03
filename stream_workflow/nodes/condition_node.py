"""条件判断节点"""

from typing import Any, Dict
from stream_workflow.core import Node, ParameterSchema, WorkflowContext, NodeExecutionError, register_node

@register_node('condition_node')
class ConditionNode(Node):
    """
    条件判断节点
    
    功能：根据条件决定数据流向
    
    输入参数：
        input_data: 输入数据（可选，可以从配置文件或输入获取）
            - data: any - 要判断的数据
            - conditions: list - 条件列表
            - default_branch: string - 默认分支
    
    输出参数：
        output: 条件判断结果
            - branch: string - 选择的分支
            - data: any - 传递的数据
            - condition: string - 满足的条件表达式
            - matched: boolean - 是否有条件匹配
    
    配置参数：
        conditions: list - 条件列表
            - branch: string - 分支名称
            - expression: string - 条件表达式
        default_branch: string - 默认分支（当所有条件都不满足时）
    """
    
    # 节点执行模式：顺序执行，任务驱动
    EXECUTION_MODE = 'sequential'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=False,
            schema={
                "data": "any",
                "conditions": "list",
                "default_branch": "string"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "output": ParameterSchema(
            is_streaming=False,
            schema={
                "branch": "string",
                "data": "any",
                "condition": "any",  # 允许 None
                "matched": "boolean"
            }
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
        """
        执行条件判断
        
        配置参数:
            - conditions: 条件列表
            - default_branch: 默认分支（当所有条件都不满足时）
        """
        # 1. 从配置文件获取默认值（使用简化的 get_config 方法）
        conditions = self.get_config('config.conditions') or self.get_config('conditions', [])
        default_branch = self.get_config('config.default_branch') or self.get_config('default_branch', 'default')
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            input_data = self.get_input_value('input_data')
            if input_data:
                data = input_data.get('data')
                conditions = input_data.get('conditions', conditions)
                default_branch = input_data.get('default_branch', default_branch)
        except (ValueError, KeyError):
            # 没有输入参数，使用配置文件的值
            pass
        
        # 3. 获取要判断的数据
        if 'data' in locals() and data is not None:
            # 使用输入参数中的数据
            merged_input = data
        else:
            # 使用旧架构的输入数据（向后兼容）
            input_data = self.get_input_data(context)
            
            if not input_data:
                raise NodeExecutionError(self.node_id, "没有输入数据")
            
            # 合并输入数据
            merged_input = {}
            for node_id, data in input_data.items():
                if isinstance(data, dict):
                    # 如果数据包含result字段（来自transform节点），展平它
                    if 'result' in data and isinstance(data['result'], dict):
                        merged_input.update(data['result'])
                    else:
                        merged_input.update(data)
                else:
                    merged_input['value'] = data
        
        # 4. 评估条件
        matched = False
        selected_branch = default_branch
        matched_condition = None
        
        for condition in conditions:
            branch = condition.get('branch')
            expression = condition.get('expression')
            
            if not branch or not expression:
                continue
            
            try:
                # 评估条件表达式
                if self._evaluate_condition(expression, merged_input):
                    context.log_info(f"条件满足，选择分支: {branch}")
                    selected_branch = branch
                    matched_condition = expression
                    matched = True
                    break
            except Exception as e:
                context.log_warning(f"条件评估失败: {expression} - {str(e)}")
        
        # 5. 设置输出值
        result = {
            'branch': selected_branch,
            'data': merged_input,
            'condition': matched_condition or "",
            'matched': matched
        }
        
        self.set_output_value('output', result)
        
        if not matched:
            context.log_info(f"所有条件都不满足，使用默认分支: {default_branch}")
        
        return result
    
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
