"""
自定义节点示例

演示如何创建自定义节点，使用简化的 get_config() API
"""

import sys
import os
import asyncio
import json
from typing import Any

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow_engine import WorkflowEngine
from workflow_engine.core import Node, WorkflowContext, register_node
from workflow_engine.nodes import StartNode, OutputNode


@register_node('calculator')
class CalculatorNode(Node):
    """
    计算器节点示例
    
    功能：执行数学计算
    配置：
        - operation: 操作类型 (add, subtract, multiply, divide)
        - value: 要计算的值
    """
    
    EXECUTION_MODE = 'sequential'
    
    async def execute_async(self, context: WorkflowContext) -> Any:
        """执行计算"""
        # ✨ 使用简化的 get_config() API
        operation = self.get_config('config.operation') or self.get_config('operation')
        value = self.get_config('config.value') or self.get_config('value', 0)
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        # 从输入数据中获取基础值
        base_value = 0
        if input_data:
            # 合并所有输入数据
            for node_id, data in input_data.items():
                if isinstance(data, dict):
                    # 检查是否有 result 字段（来自计算节点）
                    if 'result' in data:
                        base_value = data['result']
                        break
                    # 检查是否有 data 字段（来自 start 节点）
                    elif 'data' in data and isinstance(data['data'], dict):
                        base_value = data['data'].get('value', 0)
                        break
                elif isinstance(data, (int, float)):
                    base_value = data
                    break
        
        # 执行计算
        if operation == 'add':
            result = base_value + value
        elif operation == 'subtract':
            result = base_value - value
        elif operation == 'multiply':
            result = base_value * value
        elif operation == 'divide':
            result = base_value / value if value != 0 else 0
        else:
            result = base_value
        
        context.log(f"计算: {base_value} {operation} {value} = {result}")
        
        return {
            'operation': operation,
            'base_value': base_value,
            'value': value,
            'result': result
        }


@register_node('formatter')
class FormatterNode(Node):
    """
    格式化节点示例
    
    功能：格式化输出数据
    配置：
        - format: 输出格式 (json, text, table)
        - precision: 数字精度
    """
    
    EXECUTION_MODE = 'sequential'
    
    async def execute_async(self, context: WorkflowContext) -> Any:
        """格式化数据"""
        # ✨ 使用简化的 get_config() API
        format_type = self.get_config('config.format') or self.get_config('format', 'json')
        precision = self.get_config('config.precision') or self.get_config('precision', 2)
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        if not input_data:
            return {"error": "没有输入数据"}
        
        # 获取计算结果
        calc_result = None
        for node_id, data in input_data.items():
            if isinstance(data, dict) and 'result' in data:
                calc_result = data
                break
        
        if not calc_result:
            return {"error": "没有找到计算结果"}
        
        # 格式化输出
        if format_type == 'json':
            formatted = {
                "计算表达式": f"{calc_result['base_value']} {calc_result['operation']} {calc_result['value']}",
                "结果": round(calc_result['result'], precision)
            }
        elif format_type == 'text':
            formatted = f"计算结果: {calc_result['base_value']} {calc_result['operation']} {calc_result['value']} = {round(calc_result['result'], precision)}"
        else:
            formatted = calc_result
        
        context.log(f"格式化完成: {format_type}")
        
        return {
            'format': format_type,
            'precision': precision,
            'formatted_result': formatted
        }


async def main():
    # 创建工作流引擎
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('start_node', StartNode)
    engine.register_node_type('calculator', CalculatorNode)
    engine.register_node_type('formatter', FormatterNode)
    engine.register_node_type('output_node', OutputNode)
    
    # 创建工作流配置
    workflow_config = {
        'workflow': {
            'name': '自定义节点示例',
            'description': '演示自定义节点和简化的配置API',
            
            'nodes': [
                # 1. 起始节点 - 提供初始数据
                {
                    'id': 'start',
                    'type': 'start_node',
                    'config': {
                        'data': {
                            'value': 100,
                            'description': '初始值'
                        }
                    }
                },
                
                # 2. 计算器节点 - 执行加法
                {
                    'id': 'add_calc',
                    'type': 'calculator',
                    'inputs': ['start'],
                    'config': {
                        'operation': 'add',
                        'value': 50
                    }
                },
                
                # 3. 计算器节点 - 执行乘法
                {
                    'id': 'multiply_calc',
                    'type': 'calculator',
                    'inputs': ['add_calc'],
                    'config': {
                        'operation': 'multiply',
                        'value': 2
                    }
                },
                
                # 4. 格式化节点 - 格式化输出
                {
                    'id': 'formatter',
                    'type': 'formatter',
                    'inputs': ['multiply_calc'],
                    'config': {
                        'format': 'json',
                        'precision': 2
                    }
                },
                
                # 5. 输出节点
                {
                    'id': 'output',
                    'type': 'output_node',
                    'inputs': ['formatter'],
                    'config': {
                        'format': 'json',
                        'save_to_file': True,
                        'file_path': 'custom_node_output.json'
                    }
                }
            ]
        }
    }
    
    # 加载配置
    engine.load_config_dict(workflow_config)
    
    print("\n" + "="*60)
    print("自定义节点示例")
    print("="*60)
    print("\n演示功能：")
    print("  - 自定义节点开发")
    print("  - 简化的 get_config() API")
    print("  - 节点间数据传递")
    print("  - 计算流程: 100 + 50 = 150, 150 * 2 = 300")
    print("\n")
    
    # 执行工作流
    context = await engine.execute_async()
    
    # 打印节点输出
    print("\n" + "="*60)
    print("节点输出结果：")
    print("="*60)
    
    for node_id, output in context.get_all_outputs().items():
        print(f"\n节点 '{node_id}':")
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    # 验证结果
    print("\n" + "="*60)
    print("验证结果：")
    print("="*60)
    
    formatter_output = context.get_node_output('formatter')
    if formatter_output and 'formatted_result' in formatter_output:
        result = formatter_output['formatted_result']
        print(f"最终结果: {result}")
        
        if '300' in str(result):
            print("\n[PASS] 计算正确！自定义节点功能正常")
        else:
            print("\n[WARN] 结果不符合预期")
    
    print("\n" + "="*60)
    print("演示完成！")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
