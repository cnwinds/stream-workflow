"""
混合流程参数引用示例

演示混合执行模式和参数引用功能
"""

import sys
import os
import asyncio
import json

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow_engine import WorkflowEngine
from workflow_engine.nodes import StartNode, TransformNode, ConditionNode, OutputNode


async def main():
    # 创建工作流引擎
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('start_node', StartNode)
    engine.register_node_type('transform_node', TransformNode)
    engine.register_node_type('condition_node', ConditionNode)
    engine.register_node_type('output_node', OutputNode)
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'workflow_mixed_example.yaml')
    engine.load_config(config_path)
    
    print("\n" + "="*60)
    print("混合流程参数引用示例")
    print("="*60)
    print("\n演示功能：")
    print("  - 混合执行模式（顺序 + 流式）")
    print("  - 参数引用功能（${node_id.field}）")
    print("  - 节点间数据传递")
    print("  - 条件判断和数据转换")
    print("\n")
    
    # 启动工作流（准备环境）
    context = await engine.start()
    
    # 执行所有节点
    await engine.execute()
    
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
    
    report = context.get_node_output('report')
    if report and 'result' in report:
        result = report['result']
        print(f"学生: {result.get('student')}")
        print(f"分数: {result.get('score')}")
        print(f"等级: {result.get('grade')}")
        print(f"状态: {result.get('status')}")
        
        if result.get('grade') == 'good' and result.get('score') == 85:
            print("\n[PASS] 混合流程和参数引用功能正常工作")
        else:
            print("\n[WARN] 结果不符合预期")
    
    print("\n" + "="*60)
    print("演示完成！")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
