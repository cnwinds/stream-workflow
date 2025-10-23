"""
外部连接示例
展示节点输出与外部函数之间的连接
"""

import asyncio
import json
import time
from typing import Dict, Any

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, register_node


# 自定义节点
@register_node('external_connected_node')
class ExternalConnectedNode(Node):
    """带外部连接的节点"""
    
    EXECUTION_MODE = 'streaming'
    
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=True,
            schema={"data": "string", "timestamp": "float"}
        )
    }
    
    OUTPUT_PARAMS = {
        "processed_output": ParameterSchema(
            is_streaming=True,
            schema={"result": "string", "processed": "boolean"}
        ),
        "status_output": ParameterSchema(
            is_streaming=True,
            schema={"status": "string", "count": "int"}
        )
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_count = 0
    
    async def run(self, context: WorkflowContext):
        """节点运行"""
        context.log_info(f"外部连接节点 {self.node_id} 启动")

        try:
            # 持续产生数据
            while True:
                # 模拟处理数据
                await asyncio.sleep(1)
                
                # 生成处理结果
                self.processed_count += 1
                result = f"处理结果 {self.processed_count}"
                
                # 发送流式输出（会自动路由到外部函数）
                await self.emit_chunk("processed_output", {
                    "result": result,
                    "processed": True
                })
                
                # 发送状态输出（会自动路由到外部函数）
                await self.emit_chunk("status_output", {
                    "status": "processing",
                    "count": self.processed_count
                })
                
                context.log_info(f"节点 {self.node_id} 发送数据: {result}")
                
        except asyncio.CancelledError:
            context.log_info(f"外部连接节点 {self.node_id} 关闭")


# 外部处理函数
class ExternalHandlers:
    """外部处理函数"""
    
    def __init__(self):
        self.received_data = []
        self.received_status = []
    
    def handle_processed_output(self, data: Any):
        """处理节点输出"""
        print(f"外部函数收到处理结果: {data}")
        self.received_data.append(data)
    
    async def handle_status_output(self, data: Any):
        """处理状态输出"""
        print(f"外部函数收到状态: {data}")
        self.received_status.append(data)
    
    def handle_json_output(self, data: Any):
        """JSON 格式处理"""
        print(f"JSON 外部处理: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    def handle_file_output(self, data: Any):
        """文件输出处理"""
        filename = f"output_{int(time.time())}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到文件: {filename}")


async def main():
    """主函数"""
    print("外部连接示例开始")
    
    # 创建外部处理函数
    external_handlers = ExternalHandlers()
    
    # 创建工作流引擎
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    
    # 加载工作流配置
    workflow_config = {
        "workflow": {
            "name": "外部连接示例工作流",
            "nodes": [
                {
                    "id": "external_node",
                    "type": "external_connected_node"
                }
            ],
            "connections": []
        }
    }
    engine.load_config_dict(workflow_config)
    
    # 创建外部连接
    print("创建外部连接...")
    
    # 创建外部连接
    conn1 = engine.add_external_connection(
        "external_node", "processed_output", external_handlers.handle_processed_output
    )
    
    conn2 = engine.add_external_connection(
        "external_node", "status_output", external_handlers.handle_status_output
    )
    
    # 添加更多外部连接
    conn3 = engine.add_external_connection(
        "external_node", "processed_output", external_handlers.handle_json_output
    )
    
    conn4 = engine.add_external_connection(
        "external_node", "processed_output", external_handlers.handle_file_output
    )
    
    print("外部连接已创建")
    
    # 测试外部处理函数
    print("测试外部处理函数...")
    external_handlers.handle_processed_output({"test": "data"})
    await external_handlers.handle_status_output({"test": "status"})
    
    # 检查连接管理器状态
    connection_manager = engine.get_connection_manager()
    print(f"连接管理器状态:")
    print(f"  总连接数: {len(connection_manager.get_connections())}")
    print(f"  外部连接数: {len(connection_manager.get_external_connections())}")
    print(f"  流式连接数: {len(connection_manager.get_streaming_connections())}")
    print(f"  数据连接数: {len(connection_manager.get_data_connections())}")
    
    # 启动工作流
    context = await engine.start(initial_data={
        "user_id": "connection_demo",
        "session_id": "external_connection_test"
    })
    
    print("工作流已启动")
    
    # 运行一段时间
    print("运行 5 秒...")
    await asyncio.sleep(5)
    
    # 停止工作流
    await engine.stop()
    
    print(f"\n处理统计:")
    print(f"收到处理结果数量: {len(external_handlers.received_data)}")
    print(f"收到状态数量: {len(external_handlers.received_status)}")
    
    print(f"\n收到的数据:")
    for i, data in enumerate(external_handlers.received_data):
        print(f"  数据 {i+1}: {data}")
    
    print(f"\n收到的状态:")
    for i, status in enumerate(external_handlers.received_status):
        print(f"  状态 {i+1}: {status}")
    
    print("\n外部连接示例完成")


if __name__ == "__main__":
    asyncio.run(main())
