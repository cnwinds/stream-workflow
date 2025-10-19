# 数据输入指南

## 如何向节点输入参数发送数据

在工作流中，有多种方式向节点的输入参数发送数据。本文档介绍推荐的最佳实践。

---

## 1. 流式数据输入

### ✅ 推荐方式：使用 `feed_input_chunk` 方法

这是向节点输入参数发送流式数据的**标准方法**：

```python
import asyncio
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

async def send_audio_stream():
    # 创建引擎并加载配置
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    engine.load_config('workflow.yaml')
    
    # 获取目标节点
    vad_node = engine._nodes['vad']
    
    # 启动工作流
    workflow_task = asyncio.create_task(engine.execute_async())
    
    # 等待节点初始化
    await asyncio.sleep(1)
    
    # 发送流式数据
    for i in range(10):
        audio_chunk = {
            "audio_data": f"音频数据-{i}".encode(),
            "audio_type": "opus",
            "sample_rate": 16000
        }
        
        # ✅ 使用 feed_input_chunk 方法
        await vad_node.feed_input_chunk('raw_audio', audio_chunk)
        await asyncio.sleep(0.1)
    
    # 发送结束信号（使用 close_input_stream 方法）
    await vad_node.close_input_stream('raw_audio')
```

**优点**：
- ✅ 封装良好，符合面向对象原则
- ✅ 自动创建和验证 `StreamChunk`
- ✅ 自动进行参数类型验证
- ✅ 清晰的错误提示

**方法签名**：
```python
async def feed_input_chunk(self, param_name: str, chunk_data: Any)
```

**参数说明**：
- `param_name`: 输入参数名称（必须是流式参数）
- `chunk_data`: chunk 数据，必须符合参数的 schema 定义

**异常**：
- `ValueError`: 参数不存在或不是流式参数
- `TypeError`: 数据类型不匹配
- `ValidationError`: 数据验证失败

---

### ❌ 不推荐方式：直接操作队列

```python
# ❌ 不推荐：直接操作内部队列
from workflow_engine.core.parameter import StreamChunk

chunk = StreamChunk(audio_chunk, vad_node.inputs['raw_audio'].schema)
await vad_node.inputs['raw_audio'].stream_queue.put(chunk)
```

**缺点**：
- ❌ 破坏封装性
- ❌ 需要手动创建 `StreamChunk`
- ❌ 需要手动获取 schema
- ❌ 容易出错

---

## 2. 非流式数据输入

### ✅ 推荐方式：使用 `set_input_value` 方法

对于非流式参数，使用 `set_input_value` 方法设置值：

```python
from workflow_engine import WorkflowEngine

# 创建引擎并加载配置
engine = WorkflowEngine()
engine.load_config('workflow.yaml')

# 获取目标节点
http_node = engine._nodes['http_request']

# 设置非流式输入值
http_node.set_input_value('url', 'https://api.example.com/data')
http_node.set_input_value('method', 'GET')

# 执行工作流
context = engine.execute(initial_data={'key': 'value'})
```

**方法签名**：
```python
def set_input_value(self, param_name: str, value: Any)
```

**参数说明**：
- `param_name`: 输入参数名称（必须是非流式参数）
- `value`: 输入值，必须符合参数的 schema 定义

**异常**：
- `ValueError`: 参数不存在或是流式参数
- `TypeError`: 数据类型不匹配
- `ValidationError`: 数据验证失败

---

## 3. 通过工作流上下文传递数据

### 使用 `initial_data` 参数

启动工作流时可以传递初始数据：

```python
# 传递初始数据到工作流上下文
context = await engine.execute_async(initial_data={
    'user_id': '12345',
    'session_id': 'abc-def-ghi',
    'config': {'timeout': 30}
})

# 在节点中访问全局数据
class MyNode(Node):
    async def execute_async(self, context):
        user_id = context.get_global_var('user_id')
        session_id = context.get_global_var('session_id')
        # ... 使用数据
```

---

## 4. 通过节点连接传递数据

### 自动数据传递

在配置文件中定义连接后，引擎会自动处理数据传递：

```yaml
workflow:
  connections:
    # 流式连接：自动路由 chunk
    - from: "vad.audio_stream"
      to: "asr.audio_in"
    
    # 非流式连接：自动传递值
    - from: "http.response"
      to: "parser.input_data"
```

**流式连接**：
- 源节点通过 `emit_chunk()` 发送数据
- 引擎自动路由到目标节点的输入队列
- 目标节点通过 `on_chunk_received()` 接收数据

**非流式连接**：
- 源节点通过 `set_output_value()` 设置输出
- 引擎在节点执行完成后传递数据
- 目标节点通过 `get_input_value()` 获取输入

---

## 5. 完整示例

### 示例1：流式音频处理

```python
import asyncio
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

async def process_audio_stream():
    """流式音频处理示例"""
    
    # 初始化引擎
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    engine.load_config('audio_workflow.yaml')
    
    # 获取入口节点
    vad_node = engine._nodes['vad']
    
    # 启动工作流（异步后台任务）
    workflow_task = asyncio.create_task(engine.execute_async())
    
    # 等待节点启动
    await asyncio.sleep(1)
    
    # 模拟音频流输入
    try:
        for i in range(100):
            # 从麦克风或文件读取音频数据
            audio_data = read_audio_from_microphone()  # 你的音频源
            
            # 发送到工作流
            await vad_node.feed_input_chunk('raw_audio', {
                "audio_data": audio_data,
                "audio_type": "pcm",
                "sample_rate": 16000
            })
            
            await asyncio.sleep(0.02)  # 20ms 间隔
        
    finally:
        # 发送结束信号
        await vad_node.close_input_stream('raw_audio')
        
        # 等待工作流完成
        await workflow_task

asyncio.run(process_audio_stream())
```

### 示例2：非流式 HTTP 请求

```python
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

def process_http_request():
    """非流式 HTTP 请求示例"""
    
    # 初始化引擎
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    engine.load_config('http_workflow.yaml')
    
    # 设置初始数据（可选）
    context = engine.execute(initial_data={
        'api_key': 'your-api-key',
        'base_url': 'https://api.example.com'
    })
    
    # 获取结果
    result = context.get_node_output('output')
    print(f"处理结果: {result}")

process_http_request()
```

---

## 6. 最佳实践总结

### ✅ 推荐做法

1. **流式数据输入**：使用 `feed_input_chunk()` 方法
2. **非流式数据输入**：使用 `set_input_value()` 方法
3. **关闭流式输入**：使用 `close_input_stream()` 方法
4. **节点间数据传递**：使用配置文件定义连接
5. **全局数据共享**：使用 `WorkflowContext` 的 `initial_data`

### ❌ 避免做法

1. ❌ 直接操作节点的内部队列
2. ❌ 手动创建 `StreamChunk` 对象
3. ❌ 绕过引擎的连接管理器
4. ❌ 在多线程环境中不使用 `asyncio`
5. ❌ 忘记发送结束信号导致流式节点挂起

---

## 7. 常见问题

### Q: 如何知道一个参数是流式还是非流式？

A: 检查参数的 `schema.is_streaming` 属性：

```python
node = engine._nodes['my_node']
param = node.inputs['my_param']

if param.schema.is_streaming:
    # 使用 feed_input_chunk
    await node.feed_input_chunk('my_param', data)
else:
    # 使用 set_input_value
    node.set_input_value('my_param', data)
```

### Q: 如何发送结束信号给流式节点？

A: 使用 `close_input_stream` 方法（推荐）：

```python
# ✅ 推荐方式
await node.close_input_stream('param_name')

# ❌ 不推荐：直接操作队列
await node.inputs['param_name'].stream_queue.put(None)
```

### Q: 可以向一个节点的多个输入参数同时发送数据吗？

A: 可以，每个参数都有独立的队列：

```python
# 同时向多个参数发送数据
await node.feed_input_chunk('audio_in', audio_data)
await node.feed_input_chunk('control_in', control_data)
```

### Q: 如何在发送数据前验证数据格式？

A: 使用参数的 `schema.validate_value()` 方法：

```python
try:
    param = node.inputs['my_param']
    param.schema.validate_value(my_data)
    await node.feed_input_chunk('my_param', my_data)
except ValueError as e:
    print(f"数据验证失败: {e}")
```

---

## 8. 参考文档

- [节点开发指南](NODE_DEVELOPMENT_GUIDE.md)
- [流式架构说明](../ARCHITECTURE.md#流式多端口架构)
- [API 参考文档](API_REFERENCE.md)

