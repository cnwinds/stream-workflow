# 流式工作流指南

## 概述

流式工作流是一种特殊的工作流模式，所有节点并发运行，通过异步队列实时传递数据。与传统的顺序执行工作流不同，流式工作流允许**循环依赖（反馈回路）**，适用于实时音视频处理、WebSocket 通信等场景。

---

## 流式工作流 vs 传统工作流

### 传统工作流
- **执行方式**：顺序执行，按拓扑排序
- **数据传递**：节点执行完成后传递数据
- **依赖关系**：不允许循环依赖（DAG）
- **适用场景**：批处理、ETL、数据转换

### 流式工作流
- **执行方式**：并发执行，所有节点同时运行
- **数据传递**：实时传递，通过异步队列
- **依赖关系**：允许循环依赖（反馈回路）
- **适用场景**：实时音视频、WebSocket、流式AI对话

---

## 流式工作流的特征

引擎通过以下特征自动识别流式工作流：

1. **所有参数都是流式的**：节点的所有输入和输出参数都定义为 `is_streaming=True`
2. **允许循环依赖**：节点之间可以形成环路（例如：Agent -> TTS -> Agent）
3. **并发执行**：所有节点同时启动，不需要等待前置节点完成

---

## 循环依赖示例

在语音对话场景中，经常需要反馈回路：

```yaml
connections:
  # 主流程：对话 -> 语音合成
  - from: "agent.response_text"
    to: "tts.text_input"
  
  # 反馈回路：语音合成状态 -> 对话代理
  - from: "tts.broadcast_status"
    to: "agent.broadcast_status"
```

这形成了一个循环：`agent -> tts -> agent`

**传统工作流**：会报错"工作流存在循环依赖" ❌  
**流式工作流**：正常运行，支持反馈回路 ✅

---

## 如何创建流式工作流

### 1. 定义流式节点

所有参数都必须是流式的：

```python
from workflow_engine.core import Node, ParameterSchema

class MyStreamingNode(Node):
    INPUT_PARAMS = {
        "stream_in": ParameterSchema(
            is_streaming=True,  # 必须为 True
            schema={"data": "string"}
        )
    }
    
    OUTPUT_PARAMS = {
        "stream_out": ParameterSchema(
            is_streaming=True,  # 必须为 True
            schema={"data": "string"}
        )
    }
    
    async def execute_async(self, context):
        # 流式节点持续运行
        await asyncio.sleep(float('inf'))
    
    async def on_chunk_received(self, param_name, chunk):
        # 处理输入 chunk
        data = chunk.data["data"]
        # 发送输出 chunk
        await self.emit_chunk("stream_out", {"data": data})
```

### 2. 配置工作流

```yaml
workflow:
  name: "流式工作流示例"
  
  nodes:
    - id: "node1"
      type: "my_streaming_node"
    
    - id: "node2"
      type: "my_streaming_node"
  
  connections:
    # 允许循环依赖
    - from: "node1.stream_out"
      to: "node2.stream_in"
    
    - from: "node2.stream_out"
      to: "node1.stream_in"  # 形成循环
```

### 3. 执行工作流

```python
import asyncio
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

async def main():
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    engine.load_config('streaming_workflow.yaml')
    
    # 获取入口节点
    node1 = engine._nodes['node1']
    
    # 启动工作流（后台任务）
    workflow_task = asyncio.create_task(engine.execute_async())
    
    # 等待节点启动
    await asyncio.sleep(1)
    
    # 向入口节点发送数据
    await node1.feed_input_chunk('stream_in', {"data": "Hello"})
    
    # 关闭输入流
    await node1.close_input_stream('stream_in')
    
    # 等待工作流完成（可能需要超时）
    await asyncio.wait_for(workflow_task, timeout=10)

asyncio.run(main())
```

---

## 工作原理

### 引擎如何识别流式工作流

```python
def _is_streaming_workflow(self) -> bool:
    """检查是否为流式工作流"""
    # 检查所有节点的所有参数
    for node in self._nodes.values():
        for param in node.inputs.values():
            if not param.is_streaming:
                return False  # 发现非流式参数
        for param in node.outputs.values():
            if not param.is_streaming:
                return False  # 发现非流式参数
    
    return len(self._nodes) > 0  # 所有参数都是流式的
```

### 执行流程

1. **检测工作流类型**：
   - 流式工作流 → 并发启动所有节点
   - 传统工作流 → 拓扑排序后顺序执行

2. **启动流式消费任务**：
   - 为每个流式输入参数创建消费任务
   - 持续监听队列，处理 chunk

3. **启动节点执行任务**：
   - 所有节点并发执行 `execute_async()`
   - 流式节点通常持续运行

4. **数据路由**：
   - 通过 `ConnectionManager` 路由 chunk
   - 支持一对多广播

---

## 常见问题

### Q: 流式工作流何时结束？

A: 流式工作流通常持续运行，直到：
1. 手动发送结束信号（`close_input_stream`）
2. 设置超时时间
3. 外部停止信号

```python
# 方式1：超时结束
await asyncio.wait_for(workflow_task, timeout=60)

# 方式2：手动结束
await node.close_input_stream('param_name')
```

### Q: 可以混合流式和非流式节点吗？

A: 可以，但需要注意：
- 如果有**任何**非流式参数，引擎会使用拓扑排序
- 此时**不允许**循环依赖
- 建议纯流式工作流和传统工作流分开

### Q: 循环依赖会导致死锁吗？

A: 不会，因为：
- 流式节点是异步的
- 数据通过队列传递，不会阻塞
- 节点并发运行，不互相等待

### Q: 如何调试流式工作流？

A: 建议：
1. 在 `on_chunk_received` 中添加日志
2. 监控队列大小
3. 使用超时机制防止无限运行
4. 分步测试单个节点

---

## 最佳实践

### ✅ 推荐做法

1. **纯流式设计**：流式工作流中所有参数都应该是流式的
2. **设置超时**：使用 `asyncio.wait_for` 防止无限运行
3. **优雅关闭**：发送结束信号关闭流式输入
4. **错误处理**：在 `on_chunk_received` 中捕获异常
5. **日志记录**：记录关键事件便于调试

### ❌ 避免做法

1. ❌ 在流式工作流中混合非流式参数
2. ❌ 忘记发送结束信号导致挂起
3. ❌ 在 `on_chunk_received` 中执行阻塞操作
4. ❌ 过度依赖循环依赖（尽量简化拓扑）
5. ❌ 不设置超时导致资源泄漏

---

## 完整示例

参考以下文件获取完整示例：

- **配置文件**：`examples/workflow_streaming.yaml`
- **运行示例**：`examples/run_streaming_example.py`
- **节点实现**：
  - `workflow_engine/nodes/vad_node.py`
  - `workflow_engine/nodes/asr_node.py`
  - `workflow_engine/nodes/agent_node.py`
  - `workflow_engine/nodes/tts_node.py`

---

## 参考文档

- [节点开发指南](NODE_DEVELOPMENT_GUIDE.md)
- [数据输入指南](DATA_INPUT_GUIDE.md)
- [架构文档](../ARCHITECTURE.md)

