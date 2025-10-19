#!/usr/bin/env python3
"""
自定义节点示例

演示如何创建和使用自定义节点
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_engine import WorkflowEngine, Node, WorkflowContext, NodeExecutionError
from workflow_engine.nodes import StartNode, OutputNode


class EmailNode(Node):
    """
    自定义邮件发送节点
    
    这是一个示例节点，演示如何创建自定义节点
    """
    
    def execute(self, context: WorkflowContext):
        """
        执行邮件发送（模拟）
        
        配置参数:
            - to: 收件人
            - subject: 主题
            - body: 邮件正文
            - template: 是否使用模板
        """
        # 获取配置参数
        to = self.config.get('to')
        subject = self.config.get('subject', 'No Subject')
        body = self.config.get('body', '')
        use_template = self.config.get('template', False)
        
        if not to:
            raise NodeExecutionError(self.node_id, "缺少收件人地址 (to)")
        
        # 获取输入数据（可能来自前面的节点）
        input_data = self.get_input_data(context)
        
        # 如果使用模板，从输入数据填充
        if use_template and input_data:
            # 合并所有输入数据
            template_data = {}
            for node_id, data in input_data.items():
                if isinstance(data, dict):
                    template_data.update(data)
            
            # 使用简单的字符串格式化
            try:
                subject = subject.format(**template_data)
                body = body.format(**template_data)
            except KeyError as e:
                context.log(f"模板变量未找到: {e}", level="WARNING")
        
        # 模拟发送邮件
        context.log(f"准备发送邮件到: {to}")
        context.log(f"主题: {subject}")
        context.log(f"正文长度: {len(body)} 字符")
        
        # 这里应该是实际的邮件发送逻辑
        # import smtplib
        # ...
        
        # 模拟发送成功
        result = {
            'status': 'sent',
            'to': to,
            'subject': subject,
            'timestamp': context.start_time.isoformat(),
            'message_id': f'msg_{self.node_id}_{hash(to)}'
        }
        
        context.log(f"邮件发送成功！消息ID: {result['message_id']}")
        
        return result


class DatabaseNode(Node):
    """
    自定义数据库节点
    
    演示数据库查询操作
    """
    
    def execute(self, context: WorkflowContext):
        """
        执行数据库查询（模拟）
        
        配置参数:
            - operation: 操作类型 (select, insert, update, delete)
            - table: 表名
            - query: SQL查询或条件
        """
        operation = self.config.get('operation', 'select')
        table = self.config.get('table')
        query = self.config.get('query', '')
        
        if not table:
            raise NodeExecutionError(self.node_id, "缺少表名 (table)")
        
        context.log(f"执行数据库操作: {operation} on {table}")
        
        # 模拟数据库操作
        if operation == 'select':
            # 模拟查询结果
            result = {
                'operation': 'select',
                'table': table,
                'rows': [
                    {'id': 1, 'name': '张三', 'score': 95},
                    {'id': 2, 'name': '李四', 'score': 88},
                    {'id': 3, 'name': '王五', 'score': 92}
                ],
                'count': 3
            }
        elif operation == 'insert':
            # 获取要插入的数据
            input_data = self.get_input_data(context)
            result = {
                'operation': 'insert',
                'table': table,
                'affected_rows': 1,
                'inserted_id': 123
            }
        else:
            result = {
                'operation': operation,
                'table': table,
                'affected_rows': 0
            }
        
        context.log(f"数据库操作完成: {result}")
        return result


def run_custom_email_workflow():
    """运行自定义邮件工作流"""
    print("\n" + "="*60)
    print("自定义节点示例: 邮件发送工作流")
    print("="*60 + "\n")
    
    engine = WorkflowEngine()
    
    # 注册节点类型（包括自定义节点）
    engine.register_node_type('start', StartNode)
    engine.register_node_type('email', EmailNode)  # 注册自定义邮件节点
    engine.register_node_type('output', OutputNode)
    
    # 通过代码定义工作流
    config = {
        'workflow': {
            'name': '邮件发送工作流',
            'description': '使用自定义邮件节点发送通知',
            'version': '1.0.0',
            'nodes': [
                {
                    'id': 'start',
                    'type': 'start',
                    'name': '获取用户数据',
                    'data': {
                        'username': '张三',
                        'email': 'zhangsan@example.com',
                        'score': 95,
                        'course': 'Python编程'
                    }
                },
                {
                    'id': 'send_email',
                    'type': 'email',
                    'name': '发送成绩通知邮件',
                    'inputs': ['start'],
                    'to': '{email}',
                    'subject': '【成绩通知】{course}课程成绩',
                    'body': '亲爱的{username}，您好！\n\n您的{course}课程成绩为：{score}分。\n\n祝好！',
                    'template': True
                },
                {
                    'id': 'output',
                    'type': 'output',
                    'name': '输出发送结果',
                    'inputs': ['send_email'],
                    'format': 'json'
                }
            ]
        }
    }
    
    # 执行工作流
    engine.load_config_dict(config)
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


def run_custom_database_workflow():
    """运行自定义数据库工作流"""
    print("\n" + "="*60)
    print("自定义节点示例: 数据库查询工作流")
    print("="*60 + "\n")
    
    engine = WorkflowEngine()
    
    # 注册节点类型
    engine.register_node_type('database', DatabaseNode)  # 注册自定义数据库节点
    engine.register_node_type('output', OutputNode)
    
    # 通过代码定义工作流
    config = {
        'workflow': {
            'name': '数据库查询工作流',
            'description': '使用自定义数据库节点查询数据',
            'version': '1.0.0',
            'nodes': [
                {
                    'id': 'query_students',
                    'type': 'database',
                    'name': '查询学生成绩',
                    'operation': 'select',
                    'table': 'students',
                    'query': 'SELECT * FROM students WHERE score > 85'
                },
                {
                    'id': 'output',
                    'type': 'output',
                    'name': '输出查询结果',
                    'inputs': ['query_students'],
                    'format': 'json'
                }
            ]
        }
    }
    
    # 执行工作流
    engine.load_config_dict(config)
    context = engine.execute()
    
    # 打印日志
    print("\n执行日志:")
    for log in context.get_logs():
        print(f"[{log['level']}] {log['message']}")


if __name__ == '__main__':
    # 运行自定义节点示例
    try:
        run_custom_email_workflow()
        run_custom_database_workflow()
        
        print("\n" + "="*60)
        print("自定义节点示例执行完成！")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
