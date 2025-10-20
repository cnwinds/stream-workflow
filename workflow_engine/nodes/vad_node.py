"""语音活动检测（VAD）节点"""

import asyncio
import time
from workflow_engine.core import Node, ParameterSchema, StreamChunk, WorkflowContext, register_node


@register_node('vad_node')
class VADNode(Node):
    """
    语音活动检测节点
    
    功能：检测音频流中的语音活动，过滤静音部分
    
    输入参数：
        raw_audio: 原始音频流
            - audio_data: bytes - 音频二进制数据
            - audio_type: string - 编码格式（如 opus/pcm）
            - sample_rate: integer - 采样率
    
    输出参数：
        audio_stream: 处理后的音频流（只包含语音部分）
            - audio_data: bytes - 音频二进制数据
            - audio_type: string - 编码格式
            - sample_rate: integer - 采样率
            - timestamp: float - 时间戳
    
    配置参数：
        threshold: float - VAD 检测阈值（默认 0.5）
        min_speech_duration: float - 最小语音持续时间，秒（默认 0.3）
    """
    
    # 节点执行模式：纯流式节点，数据驱动
    EXECUTION_MODE = 'streaming'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "raw_audio": ParameterSchema(
            is_streaming=True,
            schema={
                "audio_data": "bytes",
                "audio_type": "string",
                "sample_rate": "integer"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "audio_stream": ParameterSchema(
            is_streaming=True,
            schema={
                "audio_data": "bytes",
                "audio_type": "string",
                "sample_rate": "integer",
                "timestamp": "float"
            }
        )
    }
    
    async def run(self, context: WorkflowContext):
        """
        主执行逻辑（初始化）
        
        Args:
            context: 工作流执行上下文
        """
        threshold = self.config.get('threshold', 0.5)
        min_duration = self.config.get('min_speech_duration', 0.3)
        
        context.log(f"VAD 节点启动 [{self.node_id}]")
        context.log(f"  - 检测阈值: {threshold}")
        context.log(f"  - 最小语音持续时间: {min_duration}s")
        
        # 流式节点通常持续运行，通过 on_chunk_received 处理数据
        # 这里保持运行状态
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            context.log(f"VAD 节点关闭 [{self.node_id}]")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """
        处理输入的音频 chunk
        
        Args:
            param_name: 参数名称
            chunk: 流式数据块
        """
        if param_name == "raw_audio":
            audio_data = chunk.data["audio_data"]
            audio_type = chunk.data["audio_type"]
            sample_rate = chunk.data["sample_rate"]
            
            # VAD 检测逻辑
            if self._is_speech(audio_data):
                # 发送处理后的 chunk
                await self.emit_chunk("audio_stream", {
                    "audio_data": audio_data,
                    "audio_type": audio_type,
                    "sample_rate": sample_rate,
                    "timestamp": time.time()
                })
    
    def _is_speech(self, audio_data: bytes) -> bool:
        """
        VAD 检测算法（示例实现）
        
        Args:
            audio_data: 音频数据
            
        Returns:
            是否包含语音
            
        注意：这是一个简单的示例实现，实际应用中应使用专业的 VAD 算法
        如 WebRTC VAD、Silero VAD 等
        """
        threshold = self.config.get('threshold', 0.5)
        
        # 简单实现：检查数据长度（实际应计算能量或使用 VAD 模型）
        # 这里仅作为示例
        if len(audio_data) == 0:
            return False
        
        # 实际应用中应该：
        # 1. 计算音频能量
        # 2. 使用 VAD 模型（如 Silero VAD）
        # 3. 根据阈值判断
        
        # 示例：假设所有非空数据都是语音
        return True

