#!/usr/bin/env python3
"""
工作流引擎使用示例

演示如何使用工作流引擎执行不同的工作流配置
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_engine import WorkflowEngine
from workflow_engine.nodes import (
    StartNode,
    HttpNode,
    TransformNode,
    ConditionNode,
    MergeNode,
    OutputNode
)


def run_simple_workflow():
    """运行简单工作流示例"""
    print("\n" + "="*60)
    print("示例1: 简单数据处理流程")
    print("="*60 + "\n")
    
    # 创建引擎实例
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('start', StartNode)
    engine.register_node_type('transform', TransformNode)
    engine.register_node_type('output', OutputNode)
    
    # 加载配置并执行
    engine.load_config('examples/workflow_simple.yaml')
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


def run_http_workflow():
    """运行HTTP请求工作流示例"""
    print("\n" + "="*60)
    print("示例2: API数据获取和处理")
    print("="*60 + "\n")
    
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('http', HttpNode)
    engine.register_node_type('transform', TransformNode)
    engine.register_node_type('output', OutputNode)
    
    # 加载配置并执行
    engine.load_config('examples/workflow_http.yaml')
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


def run_condition_workflow():
    """运行条件判断工作流示例"""
    print("\n" + "="*60)
    print("示例3: 条件判断和分支处理")
    print("="*60 + "\n")
    
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('start', StartNode)
    engine.register_node_type('condition', ConditionNode)
    engine.register_node_type('transform', TransformNode)
    engine.register_node_type('output', OutputNode)
    
    # 加载配置并执行
    engine.load_config('examples/workflow_condition.yaml')
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


def run_complex_workflow():
    """运行复杂工作流示例"""
    print("\n" + "="*60)
    print("示例4: 复杂数据处理流程")
    print("="*60 + "\n")
    
    engine = WorkflowEngine()
    
    # 注册所有节点类型
    engine.register_node_type('start', StartNode)
    engine.register_node_type('merge', MergeNode)
    engine.register_node_type('transform', TransformNode)
    engine.register_node_type('condition', ConditionNode)
    engine.register_node_type('output', OutputNode)
    
    # 加载配置并执行
    engine.load_config('examples/workflow_complex.yaml')
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


def run_custom_workflow():
    """运行自定义工作流（通过代码配置）"""
    print("\n" + "="*60)
    print("示例5: 通过代码定义工作流")
    print("="*60 + "\n")
    
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('start', StartNode)
    engine.register_node_type('transform', TransformNode)
    engine.register_node_type('output', OutputNode)
    
    # 通过字典定义配置
    config = {
        'workflow': {
            'name': '代码定义的工作流',
            'description': '演示通过代码创建工作流配置',
            'version': '1.0.0',
            'nodes': [
                {
                    'id': 'start',
                    'type': 'start',
                    'name': '开始',
                    'data': {
                        'numbers': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                    }
                },
                {
                    'id': 'calculate',
                    'type': 'transform',
                    'name': '计算统计值',
                    'inputs': ['start'],
                    'operation': 'custom',
                    'config': {
                        'expression': """
{
    'numbers': data['numbers'],
    'sum': sum(data['numbers']),
    'avg': sum(data['numbers']) / len(data['numbers']),
    'max': max(data['numbers']),
    'min': min(data['numbers']),
    'count': len(data['numbers'])
}
"""
                    }
                },
                {
                    'id': 'output',
                    'type': 'output',
                    'name': '输出结果',
                    'inputs': ['calculate'],
                    'format': 'json'
                }
            ]
        }
    }
    
    # 加载配置并执行
    engine.load_config_dict(config)
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


if __name__ == '__main__':
    # 运行所有示例
    try:
        # 示例1: 简单数据处理
        run_simple_workflow()
        
        # 示例2: HTTP请求（可能需要网络连接）
        try:
            run_http_workflow()
        except Exception as e:
            print(f"\nHTTP示例跳过（可能无网络连接）: {e}")
        
        # 示例3: 条件判断
        run_condition_workflow()
        
        # 示例4: 复杂工作流
        run_complex_workflow()
        
        # 示例5: 代码定义工作流
        run_custom_workflow()
        
        print("\n" + "="*60)
        print("所有示例执行完成！")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
