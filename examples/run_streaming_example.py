"""流式工作流示例运行脚本"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes


async def main():
    """主函数"""
    print("=" * 60)
    print("流式工作流示例")
    print("=" * 60)
    print()
    
    # 创建工作流引擎
    engine = WorkflowEngine()
    
    # 自动注册所有内置节点
    auto_register_nodes(engine)
    print()
    
    # 加载流式工作流配置
    config_path = project_root / "examples" / "workflow_streaming.yaml"
    engine.load_config(str(config_path))
    print()
    
    # 显示工作流信息
    workflow_info = engine.get_workflow_info()
    print(f"工作流名称: {workflow_info['name']}")
    print(f"工作流描述: {workflow_info['description']}")
    print(f"节点数量: {workflow_info['node_count']}")
    print()
    
    # 模拟发送音频数据到 VAD 节点
    print("开始执行工作流...")
    print("-" * 60)
    
    # 启动工作流（异步执行）
    # 注意：实际应用中需要有外部数据源向 VAD 节点发送音频数据
    try:
        # 获取 VAD 节点并模拟发送数据
        vad_node = engine.get_node('vad')
        
        # 启动工作流执行任务
        workflow_task = asyncio.create_task(engine.execute_async())
        
        # 等待节点启动
        await asyncio.sleep(1)
        
        # 模拟发送 3 个音频 chunk
        print("\n模拟发送音频数据...")
        for i in range(3):
            # 模拟音频数据
            audio_chunk = {
                "audio_data": f"音频数据-{i}".encode(),
                "audio_type": "opus",
                "sample_rate": 16000
            }
            
            # 直接向 VAD 节点的输入队列发送数据
            await vad_node.inputs['raw_audio'].stream_queue.put(
                type('StreamChunk', (), {
                    'data': audio_chunk,
                    'schema': vad_node.inputs['raw_audio'].schema,
                    'timestamp': asyncio.get_event_loop().time()
                })()
            )
            print(f"  已发送音频 chunk {i+1}/3")
            await asyncio.sleep(0.5)
        
        # 发送结束信号
        await vad_node.inputs['raw_audio'].stream_queue.put(None)
        print("\n等待工作流处理完成...")
        
        # 等待工作流完成（设置超时）
        await asyncio.wait_for(workflow_task, timeout=10)
        
    except asyncio.TimeoutError:
        print("\n工作流执行超时（这是正常的，因为流式节点会持续运行）")
    except Exception as e:
        print(f"\n执行过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("-" * 60)
    print("\n示例执行完成！")
    print("\n注意：")
    print("1. 这是一个演示示例，实际应用中需要真实的音频输入源")
    print("2. 流式节点会持续运行，需要外部控制生命周期")
    print("3. 实际的 ASR、Agent、TTS 需要集成真实的模型/API")


if __name__ == "__main__":
    asyncio.run(main())

