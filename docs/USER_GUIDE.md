# 工作流引擎用户指南

## 📖 概述

这是一个类似 n8n 的 Python 工作流引擎框架，支持通过配置文件定义和执行复杂的数据处理流程。

### 🌟 核心特性

- 📝 **配置驱动**: 通过 YAML 或 JSON 配置文件定义工作流
- 🔌 **插件化节点**: 轻松扩展自定义节点类型
- 🔄 **自动依赖解析**: 智能的拓扑排序，自动确定节点执行顺序
- 📊 **数据流转**: 节点间自动传递数据，支持多输入多输出
- 🎯 **条件分支**: 支持基于条件的流程分支
- 🌊 **流式处理**: 支持实时音频/视频流、WebSocket 实时通信
- 🔗 **多端口连接**: 参数级精确连接，自动类型验证
- ⚡ **异步并发**: 基于 asyncio 的高性能异步执行
- 🔀 **混合执行模式**: 优雅融合流式和非流式节点，支持反馈回路
- 🔍 **上下文参数引用**: 使用 `${node_id.field}` 语法灵活引用节点输出

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd workflow_engine

# 安装依赖
pip install -r requirements.txt
```

### 基本使用

```python
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

# 创建工作流引擎
engine = WorkflowEngine()

# 自动注册所有内置节点
auto_register_nodes(engine)

# 加载配置
engine.load_config('my_workflow.yaml')

# 执行工作流
context = await engine.start()
```

---

## 📋 配置文件格式

### 基本结构

```yaml
workflow:
  name: "工作流名称"           # 必需
  description: "工作流描述"    # 可选
  version: "1.0.0"            # 可选
  
  config:                     # 可选，工作流级配置
    stream_timeout: 300       # 流式任务超时时间（秒）
    continue_on_error: false  # 错误时是否继续执行
  
  nodes:                      # 必需，节点定义
    - id: "node_id"           # 必需，节点唯一ID
      type: "node_type"       # 必需，节点类型
      name: "节点名称"         # 可选
      config:                 # 可选，节点配置
        # ... 节点特定配置 ...
  
  connections:                # 可选，参数级连接
    - from: "source.output"
      to: "target.input"
```

### 配置示例

```yaml
workflow:
  name: "数据处理流程"
  
  nodes:
    - id: "start"
      type: "start_node"
      config:
        data:
          message: "Hello"
          value: 42
    
    - id: "transform"
      type: "transform_node"
      inputs: ["start"]
      config:
        operation: "custom"
        config:
          expression: "{'total': data['value'] * 2}"
    
    - id: "output"
      type: "output_node"
      inputs: ["transform"]
      config:
        format: "json"
```

---

## 🔍 上下文参数引用

### 为什么需要参数引用？

对于顺序执行的节点，上一个节点的输出格式不一定和下一个节点的输入格式匹配。通过上下文参数引用，顺序节点无需配置连接，可以直接从上下文获取之前节点的输出内容。

### 基本语法

```yaml
# 在节点配置中使用 ${node_id.field} 语法
- id: "processor"
  type: "http_node"
  config:
    url: "https://api.example.com"
    body:
      name: "${data_source.data.name}"    # 引用其他节点的输出
      score: "${data_source.data.score}"  # 支持嵌套字段访问
```

### 支持的引用类型

1. **完整节点输出**: `${node_id}`
2. **字段引用**: `${node_id.field}`
3. **嵌套字段**: `${node_id.user.name}`
4. **数组访问**: `${node_id.items[0]}`
5. **全局变量**: `${global.var_name}`
6. **字符串模板**: `"用户 ${data.name} 的分数是 ${data.score}"`

### 配置示例

```yaml
workflow:
  name: "参数引用示例"
  nodes:
    - id: "student_data"
      type: "start_node"
      config:
        data:
          name: "张三"
          score: 85
    
    - id: "report"
      type: "transform_node"
      inputs: ["student_data"]
      config:
        operation: "custom"
        config:
          expression: |
            {
              'student': '${student_data.data.name}',
              'score': ${student_data.data.score},
              'grade': 'B'
            }
```

---

## 📦 内置节点类型

### StartNode (起始节点)

提供初始数据或从全局变量获取数据。

```yaml
- id: "start"
  type: "start_node"
  config:
    data:
      message: "Hello"
      value: 42
```

### TransformNode (数据转换节点)

支持多种数据转换操作。

**操作类型**：
- `extract`: 提取指定字段
- `map`: 映射/重命名字段
- `filter`: 过滤数据
- `aggregate`: 聚合操作（sum、avg、max、min）
- `custom`: 自定义 Python 表达式

```yaml
- id: "transform"
  type: "transform_node"
  inputs: ["previous_node"]
  config:
    operation: "custom"
    config:
      expression: "{'total': sum(data['values']), 'count': len(data['values'])}"
```

### ConditionNode (条件判断节点)

根据条件决定数据流向。

```yaml
- id: "check"
  type: "condition_node"
  inputs: ["previous_node"]
  config:
    conditions:
      - branch: "high"
        expression: "score >= 90"
      - branch: "medium"
        expression: "score >= 60"
    default_branch: "low"
```

### HttpNode (HTTP请求节点)

发送HTTP请求。

```yaml
- id: "api_call"
  type: "http_node"
  config:
    url: "https://api.example.com/data"
    method: "POST"
    headers:
      Content-Type: "application/json"
    body:
      name: "${data_source.name}"
      score: "${data_source.score}"
```

### MergeNode (合并节点)

合并多个输入。

**合并策略**：
- `merge`: 合并字典
- `concat`: 连接列表
- `first`: 取第一个输入
- `last`: 取最后一个输入

```yaml
- id: "merge"
  type: "merge_node"
  inputs: ["node1", "node2"]
  config:
    strategy: "merge"
```

### OutputNode (输出节点)

输出工作流的最终结果。

```yaml
- id: "output"
  type: "output_node"
  inputs: ["final_node"]
  config:
    format: "json"
    save_to_file: true
    file_path: "output.json"
```

---

## 🌊 流式工作流

### 什么是流式工作流？

流式工作流允许节点并发运行，通过异步队列实时传递数据。适用于：
- 实时音频/视频处理
- WebSocket 实时通信
- 流式AI对话
- 实时数据采集和监控

### 流式 vs 传统工作流

| 特性 | 传统工作流 | 流式工作流 |
|------|----------|----------|
| **执行方式** | 顺序执行 | 并发执行 |
| **数据传递** | 节点完成后传递 | 实时传递 |
| **循环依赖** | 不允许 | 允许（反馈回路） |
| **适用场景** | 批处理、ETL | 实时处理 |

### 流式工作流配置

```yaml
workflow:
  name: "语音对话流程"
  
  nodes:
    - id: "vad"
      type: "vad_node"  # 语音活动检测
    
    - id: "asr"
      type: "asr_node"  # 语音识别
    
    - id: "agent"
      type: "agent_node"  # 对话代理
    
    - id: "tts"
      type: "tts_node"  # 文本转语音
  
  connections:
    # 流式连接：实时传递数据
    - from: "vad.audio_stream"
      to: "asr.audio_in"
    
    - from: "asr.text_stream"
      to: "agent.text_input"
    
    - from: "agent.response_text"
      to: "tts.text_input"
    
    # 反馈回路：允许循环依赖
    - from: "tts.broadcast_status"
      to: "agent.broadcast_status"
```

### 如何向流式节点输入数据

```python
import asyncio
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

async def send_audio_stream():
    # 创建引擎并加载配置
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    engine.load_config('streaming_workflow.yaml')
    
    # 获取入口节点
    vad_node = engine._nodes['vad']
    
    # 启动工作流（后台任务）
    workflow_task = asyncio.create_task(engine.start())
    
    # 等待节点初始化
    await asyncio.sleep(1)
    
    # 发送流式数据
    for i in range(10):
        audio_chunk = {
            "audio_data": f"音频数据-{i}".encode(),
            "audio_type": "opus",
            "sample_rate": 16000
        }
        
        # 使用 feed_input_chunk 方法发送数据
        await vad_node.feed_input_chunk('raw_audio', audio_chunk)
        await asyncio.sleep(0.1)
    
    # 发送结束信号
    await vad_node.close_input_stream('raw_audio')
    
    # 等待工作流完成
    await workflow_task

asyncio.run(send_audio_stream())
```

### 流式工作流最佳实践

✅ **推荐做法**：
1. 纯流式设计：所有参数都是流式的
2. 设置超时：使用 `stream_timeout` 防止无限运行
3. 优雅关闭：发送结束信号关闭流式输入
4. 错误处理：捕获并记录异常
5. 日志记录：记录关键事件

❌ **避免做法**：
1. 混合流式和非流式参数（应使用混合执行模式）
2. 忘记发送结束信号导致挂起
3. 在回调中执行阻塞操作
4. 不设置超时导致资源泄漏

---

## 🔀 混合执行模式

### 什么是混合执行模式？

混合执行模式允许在同一个工作流中同时使用流式节点和非流式节点，引擎会自动处理执行顺序。

### 节点执行模式

每个节点有三种执行模式：

| 模式 | 说明 | 执行方式 | 典型节点 |
|------|------|----------|----------|
| **sequential** | 传统非流式节点 | 按拓扑顺序执行 | HTTP请求、数据库查询 |
| **streaming** | 纯流式节点 | 数据驱动，持续运行 | VAD、ASR、TTS |
| **hybrid** | 混合节点 | 初始化后持续运行 | Agent（需要上下文+流式输入） |

### 混合工作流配置

```yaml
workflow:
  name: "混合工作流"
  
  config:
    stream_timeout: 300  # 流式任务超时时间
  
  nodes:
    # 非流式节点：按顺序执行
    - id: "db_query"
      type: "database_node"  # sequential 模式
    
    - id: "data_transform"
      type: "transform_node"  # sequential 模式
    
    # 流式节点：持续运行
    - id: "asr"
      type: "asr_node"  # streaming 模式
    
    # 混合节点：初始化后持续运行
    - id: "agent"
      type: "agent_node"  # hybrid 模式
  
  connections:
    # 非流式连接：决定执行顺序
    - from: "db_query.result"
      to: "data_transform.input"
    
    - from: "data_transform.output"
      to: "agent.context_data"
    
    # 流式连接：实时传递数据
    - from: "asr.text_stream"
      to: "agent.text_input"
```

### 执行流程

```
1. 分类节点
   ├── Sequential/Hybrid → 需要顺序执行
   └── Streaming → 独立运行

2. 启动所有流式消费任务（后台）

3. 按拓扑顺序执行 Sequential/Hybrid 节点
   ├── Sequential: 执行完返回
   └── Hybrid: 初始化后保持运行

4. 等待流式任务完成（或超时）

5. 返回结果
```

---

## 📊 数据输入指南

### 非流式数据输入

对于非流式参数，使用 `set_input_value` 方法：

```python
engine = WorkflowEngine()
engine.load_config('workflow.yaml')

# 获取目标节点
http_node = engine._nodes['http_request']

# 设置非流式输入值
http_node.set_input_value('url', 'https://api.example.com/data')
http_node.set_input_value('method', 'GET')

# 执行工作流
context = await engine.start()
```

### 流式数据输入

对于流式参数，使用 `feed_input_chunk` 方法：

```python
import asyncio

async def send_data():
    engine = WorkflowEngine()
    engine.load_config('workflow.yaml')
    
    # 获取目标节点
    vad_node = engine._nodes['vad']
    
    # 启动工作流
    workflow_task = asyncio.create_task(engine.start())
    await asyncio.sleep(1)  # 等待节点初始化
    
    # 发送流式数据
    for i in range(100):
        await vad_node.feed_input_chunk('raw_audio', {
            "audio_data": audio_data,
            "audio_type": "pcm",
            "sample_rate": 16000
        })
        await asyncio.sleep(0.02)
    
    # 发送结束信号
    await vad_node.close_input_stream('raw_audio')
    await workflow_task

asyncio.run(send_data())
```

### 通过工作流上下文传递数据

启动工作流时可以传递初始数据：

```python
context = await engine.execute(initial_data={
    'user_id': '12345',
    'session_id': 'abc-def-ghi',
    'config': {'timeout': 30}
})
```

在节点中访问：

```python
class MyNode(Node):
    async def run(self, context):
        user_id = context.get_global_var('user_id')
        session_id = context.get_global_var('session_id')
```

### 数据输入最佳实践

✅ **推荐做法**：
1. 流式数据：使用 `feed_input_chunk()` 方法
2. 非流式数据：使用 `set_input_value()` 方法
3. 关闭流式输入：使用 `close_input_stream()` 方法
4. 节点间传递：使用配置文件定义连接
5. 全局数据：使用 `initial_data` 参数

❌ **避免做法**：
1. 直接操作节点内部队列
2. 手动创建 `StreamChunk` 对象
3. 绕过引擎的连接管理器
4. 在多线程环境中不使用 `asyncio`
5. 忘记发送结束信号导致挂起

---

## 🐛 调试和日志

### 执行日志

在节点中记录日志：

```python
async def run(self, context):
    context.log("处理开始")
    context.log("处理完成", level="SUCCESS")
    context.log("警告信息", level="WARNING")
    context.log("错误信息", level="ERROR")
```

获取所有日志：

```python
logs = context.get_logs()
for log in logs:
    print(f"[{log.level}] {log.message}")
```

### 错误处理

```python
try:
    result = await engine.execute()
except NodeExecutionError as e:
    print(f"节点 {e.node_id} 执行失败: {e.message}")
except Exception as e:
    print(f"工作流执行失败: {e}")
```

---

## 📈 最佳实践

### 配置管理

1. 使用有意义的节点ID和名称
2. 提供清晰的配置参数说明
3. 使用参数引用简化配置
4. 合理设置超时时间

### 错误处理

1. 记录详细的日志信息
2. 提供有意义的错误消息
3. 使用 `continue_on_error` 控制错误传播
4. 在关键节点添加异常处理

### 性能优化

1. 选择合适的执行模式（sequential/streaming/hybrid）
2. 避免在异步函数中使用阻塞操作
3. 合理使用流式处理减少内存占用
4. 并发执行无依赖的节点

### 安全性

1. 限制自定义表达式的执行权限
2. 验证外部输入数据
3. 使用环境变量存储敏感信息
4. 定期更新依赖库

---

## ❓ 常见问题

### Q: 如何知道一个参数是流式还是非流式？

检查参数的 `schema.is_streaming` 属性：

```python
node = engine._nodes['my_node']
param = node.inputs['my_param']

if param.schema.is_streaming:
    await node.feed_input_chunk('my_param', data)
else:
    node.set_input_value('my_param', data)
```

### Q: 流式工作流何时结束？

流式工作流通常持续运行，直到：
1. 手动发送结束信号（`close_input_stream`）
2. 设置超时时间（`stream_timeout`）
3. 外部停止信号

### Q: 可以混合流式和非流式节点吗？

可以！引擎的混合执行模式支持在同一工作流中使用两种类型的节点。引擎会自动处理执行顺序。

### Q: 循环依赖会导致死锁吗？

不会。流式连接允许循环依赖（反馈回路），因为：
- 流式节点是异步的
- 数据通过队列传递，不会阻塞
- 节点并发运行，不互相等待

### Q: 如何调试工作流？

建议：
1. 在节点中添加详细日志
2. 使用 `context.log()` 记录关键事件
3. 监控队列大小和数据流向
4. 使用超时机制防止无限运行
5. 分步测试单个节点

---

## 📚 参考资源

- **项目主页**: https://github.com/your-repo
- **示例代码**: `examples/` 目录
- **开发者指南**: `DEVELOPER_GUIDE.md`
- **变更历史**: `CHANGELOG.md`

---

**文档版本**: 2.0.0  
**最后更新**: 2025-10-20

