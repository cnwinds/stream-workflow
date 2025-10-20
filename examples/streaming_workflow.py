"""
流式工作流测试
使用 VAD -> ASR -> Agent -> TTS 的完整流式处理链路
"""

import asyncio
import time
import json
from typing import Dict, Any

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes


class MockAudioData:
    """模拟音频数据"""
    
    def __init__(self):
        self.audio_chunks = [
            # 模拟音频数据：用户说"你好，请介绍一下人工智能"
            {
                "audio_data": b"chunk1_hello", 
                "audio_type": "opus",
                "sample_rate": 16000,
                "timestamp": time.time()
            },
            {
                "audio_data": b"chunk2_please", 
                "audio_type": "opus",
                "sample_rate": 16000,
                "timestamp": time.time()
            },
            {
                "audio_data": b"chunk3_introduce", 
                "audio_type": "opus",
                "sample_rate": 16000,
                "timestamp": time.time()
            },
            {
                "audio_data": b"chunk4_ai", 
                "audio_type": "opus",
                "sample_rate": 16000,
                "timestamp": time.time()
            },
            {
                "audio_data": b"chunk5_final", 
                "audio_type": "opus",
                "sample_rate": 16000,
                "timestamp": time.time(),
                "is_final": True
            },
        ]
        self.current_chunk = 0
    
    def get_next_chunk(self):
        """获取下一个音频块"""
        if self.current_chunk < len(self.audio_chunks):
            chunk = self.audio_chunks[self.current_chunk]
            self.current_chunk += 1
            return chunk
        return None


async def simulate_audio_input(workflow_engine: WorkflowEngine, mock_audio: MockAudioData):
    """模拟音频输入到 VAD 节点"""
    print("开始模拟音频输入...")
    
    # 获取 VAD 节点
    vad_node = workflow_engine.get_node('vad')
    if not vad_node:
        print("未找到 VAD 节点")
        return
    
    # 模拟音频数据输入
    for i in range(len(mock_audio.audio_chunks)):
        chunk = mock_audio.get_next_chunk()
        if chunk:
            print(f"发送音频块 {i+1}: {chunk['audio_data']}")
            
            from workflow_engine.core import StreamChunk
            schema = vad_node.INPUT_PARAMS["raw_audio"]
            stream_chunk = StreamChunk({
                "audio_data": chunk["audio_data"],
                "audio_type": chunk["audio_type"],
                "sample_rate": chunk["sample_rate"]
            }, schema)
            
            await vad_node.on_chunk_received("raw_audio", stream_chunk)
            
            # 模拟处理间隔
            await asyncio.sleep(0.5)
    
    print("音频输入完成")


async def streaming_workflow():
    """测试流式工作流"""
    print("开始流式工作流测试")
    print("=" * 60)
    
    # 1. 创建工作流引擎
    engine = WorkflowEngine()
    
    # 2. 自动注册所有内置节点
    auto_register_nodes(engine)
    
    # 3. 定义流式工作流配置
    workflow_config = {
        "workflow": {
            "name": "流式对话工作流",
            "description": "VAD -> ASR -> Agent -> TTS 的完整流式处理链路",
            "config": {
                "stream_timeout": 30,
                "continue_on_error": False
            },
            "nodes": [
                {
                    "id": "vad",
                    "type": "vad_node",
                    "name": "语音活动检测",
                    "config": {
                        "threshold": 0.5,
                        "min_duration": 0.1,
                        "max_duration": 10.0
                    }
                },
                {
                    "id": "asr",
                    "type": "asr_node", 
                    "name": "语音识别",
                    "config": {
                        "model": "whisper",
                        "language": "zh",
                        "stream_mode": True
                    }
                },
                {
                    "id": "agent",
                    "type": "agent_node",
                    "name": "智能对话代理",
                    "config": {
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "stream": True,
                        "system_prompt": "你是一个专业的AI助手，请用简洁明了的方式回答问题。"
                    }
                },
                {
                    "id": "tts",
                    "type": "tts_node",
                    "name": "语音合成",
                    "config": {
                        "voice": "zh-CN-XiaoxiaoNeural",
                        "speed": 1.0,
                        "pitch": 1.0,
                        "audio_format": "opus"
                    }
                }
            ],
            "connections": [
                {
                    "from": "vad.audio_stream",
                    "to": "asr.audio_in"
                },
                {
                    "from": "asr.text_stream", 
                    "to": "agent.text_input"
                },
                {
                    "from": "agent.response_text",
                    "to": "tts.text_input"
                },
                {
                    "from": "tts.broadcast_status",
                    "to": "agent.broadcast_status"
                }
            ]
        }
    }
    
    # 4. 加载工作流配置
    engine.load_config_dict(workflow_config)
    
    print("工作流配置:")
    print(f"  - 节点数量: {len(engine.get_all_nodes())}")
    print(f"  - 连接数量: {len(workflow_config['workflow']['connections'])}")
    print()
    
    # 5. 启动工作流
    print("启动工作流...")
    context = await engine.start()
    
    print("工作流启动完成")
    print(f"  - 流式节点: VAD, ASR, Agent, TTS")
    print(f"  - 初始化状态: 所有节点已初始化")
    print()
    
    # 6. 模拟音频输入
    mock_audio = MockAudioData()
    await simulate_audio_input(engine, mock_audio)
    
    # 7. 等待流式处理完成
    print("等待流式处理完成...")
    await asyncio.sleep(5)  # 等待流式处理
    
    # 8. 检查处理结果
    print("\n处理结果检查:")
    print("=" * 40)
    
    # 检查各节点状态
    for node_id in ['vad', 'asr', 'agent', 'tts']:
        node = engine.get_node(node_id)
        if node:
            print(f"  {node_id.upper()}: {node.status.value}")
        else:
            print(f"  {node_id.upper()}: 未找到")
    
    # 检查日志
    logs = context.get_logs()
    print(f"\n执行日志 ({len(logs)} 条):")
    for log in logs[-10:]:  # 显示最后10条日志
        print(f"  [{log['level']}] {log['message']}")
    
    # 9. 停止工作流
    print("\n停止工作流...")
    await engine.stop()
    
    print("流式工作流测试完成!")
    print("=" * 60)


async def test_individual_nodes():
    """测试单个节点的功能"""
    print("\n测试单个节点功能:")
    print("-" * 40)
    
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    
    # 测试 VAD 节点
    print("1. 测试 VAD 节点...")
    vad_config = {
        "workflow": {
            "name": "VAD测试",
            "nodes": [{
                "id": "vad",
                "type": "vad_node",
                "config": {"threshold": 0.5}
            }]
        }
    }
    engine.load_config_dict(vad_config)
    context = await engine.start()
    await asyncio.sleep(1)
    await engine.stop()
    print("   VAD 节点测试完成")
    
    # 测试 ASR 节点
    print("2. 测试 ASR 节点...")
    asr_config = {
        "workflow": {
            "name": "ASR测试", 
            "nodes": [{
                "id": "asr",
                "type": "asr_node",
                "config": {"model": "whisper", "language": "zh"}
            }]
        }
    }
    engine.load_config_dict(asr_config)
    context = await engine.start()
    await asyncio.sleep(1)
    await engine.stop()
    print("   ASR 节点测试完成")
    
    # 测试 Agent 节点
    print("3. 测试 Agent 节点...")
    agent_config = {
        "workflow": {
            "name": "Agent测试",
            "nodes": [{
                "id": "agent", 
                "type": "agent_node",
                "config": {"model": "gpt-4", "temperature": 0.7}
            }]
        }
    }
    engine.load_config_dict(agent_config)
    context = await engine.start()
    await asyncio.sleep(1)
    await engine.stop()
    print("   Agent 节点测试完成")
    
    # 测试 TTS 节点
    print("4. 测试 TTS 节点...")
    tts_config = {
        "workflow": {
            "name": "TTS测试",
            "nodes": [{
                "id": "tts",
                "type": "tts_node", 
                "config": {"voice": "zh-CN-XiaoxiaoNeural"}
            }]
        }
    }
    engine.load_config_dict(tts_config)
    context = await engine.start()
    await asyncio.sleep(1)
    await engine.stop()
    print("   TTS 节点测试完成")


async def main():
    """主测试函数"""
    print("流式工作流完整测试")
    print("=" * 60)
    print("测试场景: VAD -> ASR -> Agent -> TTS")
    print("模拟数据: 用户语音输入 -> AI对话响应 -> 语音输出")
    print()
    
    try:
        # 1. 测试单个节点
        # await test_individual_nodes()
        
        # 2. 测试完整流式工作流
        await streaming_workflow()
        
        print("\n所有测试完成!")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
