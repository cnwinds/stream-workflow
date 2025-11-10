"""
Jinja2 模板解析示例

演示 Jinja2 模板引擎在工作流中的使用
"""

import sys
import os
import asyncio
import json

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stream_workflow import WorkflowEngine


async def main():
    # 创建工作流引擎
    engine = WorkflowEngine()
    
    # 创建简单的工作流配置，演示 Jinja2 模板功能
    workflow_config = {
        'workflow': {
            'name': 'Jinja2 模板示例',
            'description': '演示 Jinja2 模板引擎的使用',
            'version': '1.0.0',
            'nodes': [
                {
                    'id': 'init_data',
                    'type': 'variable_node',
                    'name': '初始化数据',
                    'config': {
                        'user': {
                            'profile': {
                                'user_name': 'kity',
                                'age': 25
                            },
                            'score': 85
                        },
                        'base_url': 'https://api.example.com'
                    }
                }
            ]
        }
    }
    
    # 加载配置
    engine.load_config_dict(workflow_config)
    
    print("\n" + "="*60)
    print("Jinja2 模板解析示例")
    print("="*60)
    print("\n演示功能：")
    print("  - Jinja2 模板引擎集成")
    print("  - 全局变量注入")
    print("  - 嵌套字典点号访问")
    print("  - 模板渲染接口")
    print("\n")
    
    # 准备初始全局数据
    initial_data = {
        'user': {
            'profile': {
                'user_name': 'kity',
                'age': 25
            },
            'score': 85
        },
        'base_url': 'https://api.example.com'
    }
    
    # 启动工作流（准备环境，注入全局变量）
    context = await engine.start(initial_data=initial_data)
    
    # 执行节点（初始化全局变量）
    await engine.execute()
    
    # 演示 Jinja2 模板渲染
    print("\n" + "="*60)
    print("Jinja2 模板渲染示例：")
    print("="*60)
    
    # 示例1: 访问全局变量
    template1 = "用户名称: {{ c.user.profile.user_name }}"
    result1 = engine.render_template(template1)
    print(f"\n模板: {template1}")
    print(f"结果: {result1}")
    
    # 示例2: 访问嵌套字段
    template2 = "用户 {{ c.user.profile.user_name }} 的年龄是 {{ c.user.profile.age }} 岁，分数是 {{ c.user.score }}"
    result2 = engine.render_template(template2)
    print(f"\n模板: {template2}")
    print(f"结果: {result2}")
    
    # 示例3: 使用 API URL
    template3 = "API地址: {{ c.base_url }}/users/{{ c.user.profile.user_name }}"
    result3 = engine.render_template(template3)
    print(f"\n模板: {template3}")
    print(f"结果: {result3}")
    
    # 示例4: 传入额外变量
    template4 = "Hello {{ name }}, your score is {{ c.user.score }}"
    result4 = engine.render_template(template4, name="World")
    print(f"\n模板: {template4}")
    print(f"结果: {result4}")
    
    # 示例5: 使用 Jinja2 表达式
    template5 = "总分: {{ c.user.score * 2 }}"
    result5 = engine.render_template(template5)
    print(f"\n模板: {template5}")
    print(f"结果: {result5}")
    
    # 打印全局变量（过滤掉不可序列化的对象）
    print("\n" + "="*60)
    print("全局变量：")
    print("="*60)
    global_vars = context.get_all_global_vars()
    # 过滤掉 engine 等不可序列化的对象
    serializable_vars = {
        k: v for k, v in global_vars.items() 
        if k != 'engine' and not hasattr(v, '__call__')
    }
    print(json.dumps(serializable_vars, indent=2, ensure_ascii=False))
    
    print("\n" + "="*60)
    print("演示完成！")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
