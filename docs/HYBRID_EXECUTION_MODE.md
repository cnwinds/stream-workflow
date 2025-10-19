# 混合执行模式设计文档

## 概述

本文档详细介绍了工作流引擎的**混合执行模式**设计，该设计优雅地融合了流式节点和非流式节点，解决了两种执行模型的根本差异：

- **流式节点**：数据驱动，被动响应，无需执行顺序
- **非流式节点**：任务驱动，主动执行，需要拓扑排序

## 核心设计理念

### 1. 节点执行模式分类

每个节点通过 `EXECUTION_MODE` 类属性声明其执行模式：

```python
class Node(ABC):
    """节点基类"""
    
    # 节点执行模式
    EXECUTION_MODE = 'sequential'  # 'sequential' | 'streaming' | 'hybrid'
    
    INPUT_PARAMS = {}
    OUTPUT_PARAMS = {}
```

#### 三种执行模式

| 模式 | 描述 | 执行方式 | 典型节点 |
|------|------|----------|----------|
| **sequential** | 传统非流式节点 | 按拓扑顺序执行，执行完返回 | HTTP请求、数据库查询、数据转换 |
| **streaming** | 纯流式节点 | 数据驱动，不参与拓扑排序 | VAD、ASR |
| **hybrid** | 混合节点 | 既有初始化逻辑，又能处理流式数据 | Agent（需要上下文数据+处理流式输入） |

### 2. 工作流执行策略

```python
async def execute_async(self, initial_data=None):
    """异步执行工作流（混合执行模式）"""
    
    # 1. 分类节点
    sequential_nodes = []  # 需要顺序执行的节点
    streaming_nodes = []   # 纯流式节点
    
    for node_id, node in self._nodes.items():
        if node.EXECUTION_MODE == 'streaming':
            streaming_nodes.append(node_id)
        else:  # sequential 或 hybrid
            sequential_nodes.append(node_id)
    
    # 2. 为所有流式输入启动消费任务（后台运行）
    stream_tasks = []
    for node_id, node in self._nodes.items():
        for param_name, param in node.inputs.items():
            if param.is_streaming:
                task = asyncio.create_task(node.consume_stream(param_name))
                stream_tasks.append(task)
    
    # 3. 拓扑排序（只对 sequential/hybrid 节点排序）
    execution_order = self._get_execution_order(sequential_nodes)
    
    # 4. 按顺序执行 sequential/hybrid 节点
    for node_id in execution_order:
        await self._nodes[node_id].run_async(context)
        self._transfer_non_streaming_outputs(node)  # 传递非流式输出
    
    # 5. 等待所有流式任务完成（或超时）
    await asyncio.wait_for(
        asyncio.gather(*stream_tasks),
        timeout=stream_timeout
    )
```

### 3. 连接类型自动分类

连接管理器根据参数的 `is_streaming` 属性自动分类连接：

```python
class ConnectionManager:
    def add_connection(self, conn: Connection):
        """添加连接并自动分类"""
        self._connections.append(conn)
        
        # 根据 schema 自动判断连接类型
        if conn.source_schema.is_streaming:
            self._streaming_connections.append(conn)
        else:
            self._data_connections.append(conn)
```

### 4. 拓扑排序优化

只使用**非流式连接**构建依赖图：

```python
def _get_execution_order(self, node_ids):
    """拓扑排序 - 只考虑非流式连接"""
    
    # 只使用非流式连接构建依赖图
    for conn in self._connection_manager.get_data_connections():
        if conn.source[0] in node_ids and conn.target[0] in node_ids:
            in_degree[conn.target[0]] += 1
            graph[conn.source[0]].append(conn.target[0])
    
    # Kahn 算法拓扑排序
    return topological_sort(graph)
```

## 配置示例

### 纯流式工作流

```yaml
workflow:
  name: "纯流式工作流"
  
  nodes:
    - id: "vad"
      type: "vad_node"  # EXECUTION_MODE = 'streaming'
    
    - id: "asr"
      type: "asr_node"  # EXECUTION_MODE = 'streaming'
    
    - id: "agent"
      type: "agent_node"  # EXECUTION_MODE = 'streaming'
  
  connections:
    # 流式连接：不影响执行顺序
    - from: "vad.audio_stream"
      to: "asr.audio_in"
    
    - from: "asr.text_stream"
      to: "agent.text_input"
```

**执行方式**：所有节点并发启动，数据实时传递，无需等待。

### 混合工作流

```yaml
workflow:
  name: "混合工作流"
  
  config:
    stream_timeout: 300
    continue_on_error: false
  
  nodes:
    # 非流式节点
    - id: "db_query"
      type: "database_node"  # EXECUTION_MODE = 'sequential'
    
    - id: "data_transform"
      type: "transform_node"  # EXECUTION_MODE = 'sequential'
    
    # 流式节点
    - id: "asr"
      type: "asr_node"  # EXECUTION_MODE = 'streaming'
    
    # 混合节点
    - id: "agent"
      type: "agent_node"  # EXECUTION_MODE = 'hybrid'
  
  connections:
    # 非流式连接：决定执行顺序
    - from: "db_query.result"
      to: "data_transform.input"
      type: "data"
    
    - from: "data_transform.output"
      to: "agent.context_data"
      type: "data"
    
    # 流式连接：独立运行
    - from: "asr.text_stream"
      to: "agent.text_input"
      type: "streaming"
```

**执行方式**：
1. 顺序执行 `db_query` -> `data_transform`
2. `agent` 等待 `context_data` 准备好后初始化
3. 流式数据 `asr -> agent` 实时传递
4. 支持反馈回路（如 TTS -> Agent）

## 节点实现示例

### 纯流式节点

```python
@register_node('vad_node')
class VADNode(Node):
    EXECUTION_MODE = 'streaming'  # 纯流式
    
    INPUT_PARAMS = {
        "raw_audio": ParameterSchema(is_streaming=True, schema={...})
    }
    OUTPUT_PARAMS = {
        "audio_stream": ParameterSchema(is_streaming=True, schema={...})
    }
    
    async def execute_async(self, context):
        """流式节点的 execute_async 用于初始化"""
        context.log("VAD 节点启动")
        # 流式节点保持运行，等待数据
        await asyncio.sleep(float('inf'))
    
    async def on_chunk_received(self, param_name, chunk):
        """数据驱动的处理逻辑"""
        if param_name == "raw_audio":
            processed_data = self._process(chunk.data)
            await self.emit_chunk("audio_stream", processed_data)
```

### 混合节点

```python
@register_node('agent_node')
class AgentNode(Node):
    EXECUTION_MODE = 'hybrid'  # 混合模式
    
    INPUT_PARAMS = {
        "text_input": ParameterSchema(is_streaming=True, schema={"text": "string"}),
        "context_data": ParameterSchema(is_streaming=False, schema="dict")  # 非流式
    }
    OUTPUT_PARAMS = {
        "response_text": ParameterSchema(is_streaming=True, schema={"text": "string"})
    }
    
    async def execute_async(self, context):
        """混合节点的 execute_async 执行初始化和非流式数据处理"""
        # 1. 等待非流式输入准备好
        context_data = self.get_input_value("context_data")
        
        # 2. 初始化模型
        self.model = self._load_model(context_data)
        context.log("Agent 初始化完成")
        
        # 3. 保持运行，处理流式输入
        await asyncio.sleep(float('inf'))
    
    async def on_chunk_received(self, param_name, chunk):
        """处理流式输入"""
        if param_name == "text_input":
            response = await self.model.generate(chunk.data["text"])
            await self.emit_chunk("response_text", {"text": response})
```

### 传统非流式节点

```python
@register_node('database_node')
class DatabaseNode(Node):
    EXECUTION_MODE = 'sequential'  # 传统顺序执行
    
    INPUT_PARAMS = {
        "query": ParameterSchema(is_streaming=False, schema="string")
    }
    OUTPUT_PARAMS = {
        "result": ParameterSchema(is_streaming=False, schema="dict")
    }
    
    async def execute_async(self, context):
        """传统节点：执行完就结束"""
        query = self.get_input_value("query")
        result = await self._execute_query(query)
        
        # 设置输出
        self.set_output_value("result", result)
        context.log("数据库查询完成")
        
        # 非流式节点执行完就返回，不需要 sleep(inf)
```

## 执行流程可视化

```
启动工作流
    ↓
分类节点
    ├── Sequential/Hybrid 节点 → 拓扑排序
    └── Streaming 节点 → 直接启动消费任务
    ↓
启动所有流式消费任务（后台运行）
    ↓
按拓扑顺序执行 Sequential/Hybrid 节点
    ├── Sequential 节点：执行完立即返回
    └── Hybrid 节点：初始化后保持运行
    ↓
等待流式任务完成（或超时）
    ↓
返回结果
```

## 关键优势

| 特性 | 传统模式 | 混合执行模式 |
|------|----------|-------------|
| **节点类型** | 只支持顺序节点 | 支持 sequential / streaming / hybrid |
| **执行顺序** | 所有节点都需要拓扑排序 | 只对非流式节点排序 |
| **循环依赖** | 不支持（会报错） | 流式连接允许反馈回路 |
| **实时性** | 所有节点顺序执行 | 流式数据实时传递 |
| **配置复杂度** | 需要手动定义顺序 | 自动推断执行顺序 |
| **资源利用** | 串行执行，资源利用率低 | 并发执行，资源利用率高 |

## 配置最佳实践

### ✅ 推荐

**纯流式工作流**（无需考虑顺序）：
```yaml
connections:
  - from: "vad.audio_stream"
    to: "asr.audio_in"
  - from: "asr.text_stream"
    to: "agent.text_input"
```

**混合工作流**（自动处理顺序）：
```yaml
connections:
  # 非流式连接自动决定执行顺序
  - from: "db_query.result"
    to: "transform.input"
  - from: "transform.output"
    to: "agent.context"
  
  # 流式连接独立运行
  - from: "asr.text_stream"
    to: "agent.text_input"
```

### ❌ 避免

**混淆流式和非流式连接**：
```yaml
# 错误：将流式参数用于非流式连接
connections:
  - from: "asr.text_stream"  # 流式输出
    to: "db.query_text"       # 非流式输入
```

**在非流式工作流中使用反馈回路**：
```yaml
# 错误：非流式连接的循环依赖
connections:
  - from: "node_a.output"
    to: "node_b.input"
  - from: "node_b.output"
    to: "node_a.input"  # ❌ 循环依赖
```

## 总结

混合执行模式通过以下设计优雅地融合了两种执行模型：

1. **自动分类**：根据 `EXECUTION_MODE` 自动区分节点类型
2. **双重依赖**：
   - 流式连接：不影响执行顺序
   - 非流式连接：决定拓扑排序
3. **混合节点支持**：`hybrid` 模式节点既能参与拓扑排序，又能处理流式数据
4. **配置简洁**：用户无需关心底层执行模型，只需定义连接关系

这样的设计使得：
- ✅ 流式和非流式节点可以共存
- ✅ 配置文件无需显式指定执行顺序
- ✅ 引擎自动处理依赖关系
- ✅ 开发者只需关注节点类型定义


