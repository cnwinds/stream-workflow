# 工作流引擎开发者指南

## 📖 概述

本指南面向工作流引擎的开发者和架构师，包含：
- 自定义节点开发
- 异步非流式节点开发
- 流式节点开发
- 系统架构设计
- 扩展和优化指南

---

## 🎨 节点开发基础

### 节点基本结构

所有自定义节点都必须继承 `Node` 基类：

```python
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, register_node
from typing import Any

@register_node('my_custom')  # 使用装饰器自动注册
class MyCustomNode(Node):
    """自定义节点示例"""
    
    # 声明执行模式
    EXECUTION_MODE = 'sequential'  # 或 'streaming' / 'hybrid'
    
    # 定义输入参数（类属性）
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=False,  # 是否流式参数
            schema="dict"        # 参数结构
        )
    }
    
    # 定义输出参数（类属性）
    OUTPUT_PARAMS = {
        "output_data": ParameterSchema(
            is_streaming=False,
            schema="dict"
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
        """执行节点逻辑"""
        # 1. 获取配置参数（简化API）
        param1 = self.get_config('config.param1')
        param2 = self.get_config('config.param2', 'default_value')
        
        # 2. 获取输入数据
        input_data = self.get_input_value("input_data")
        
        # 3. 执行自定义逻辑
        result = await self._process(input_data, param1, param2)
        
        # 4. 设置输出
        self.set_output_value("output_data", result)
        
        # 5. 记录日志
        context.log(f"处理完成: {result}")
        
        return result
    
    async def _process(self, data, param1, param2):
        """实现你的逻辑"""
        return {"processed": True, "data": data}
```

### 节点执行模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **sequential** | 顺序执行，执行完返回 | 数据处理、HTTP请求、数据库查询 |
| **streaming** | 数据驱动，持续运行 | 音视频处理、WebSocket、实时数据流 |
| **hybrid** | 初始化后持续运行 | Agent（需要上下文数据+流式输入） |

### 参数定义规范

#### 支持的数据类型

```python
# 简单类型
schema="string"    # 字符串
schema="integer"   # 整数
schema="float"     # 浮点数
schema="boolean"   # 布尔值
schema="bytes"     # 字节数据
schema="dict"      # 字典
schema="list"      # 列表
schema="any"       # 任意类型

# 结构体（字典类型）
schema={
    "field1": "string",
    "field2": "integer",
    "field3": "float"
}
```

#### 流式 vs 非流式参数

```python
# 非流式参数：一次性传递完整数据
ParameterSchema(
    is_streaming=False,
    schema="string"
)

# 流式参数：数据以 chunk 形式增量传递
ParameterSchema(
    is_streaming=True,
    schema={
        "data": "bytes",
        "timestamp": "float"
    }
)
```

---

## 🔄 异步非流式节点开发

### 什么是异步非流式节点？

异步非流式节点具有以下特征：
- **异步执行**：使用 `async/await` 语法
- **非流式参数**：输入输出都是完整值
- **顺序执行**：按拓扑排序执行
- **适用场景**：HTTP请求、数据库查询、文件读写

### HTTP节点示例

```python
import aiohttp
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, NodeExecutionError, register_node

@register_node('http')
class HttpNode(Node):
    """HTTP请求节点（异步非流式）"""
    
    EXECUTION_MODE = 'sequential'
    
    INPUT_PARAMS = {
        "request": ParameterSchema(
            is_streaming=False,
            schema={
                "url": "string",
                "method": "string",
                "headers": "dict",
                "body": "dict"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "response": ParameterSchema(
            is_streaming=False,
            schema={
                "status_code": "integer",
                "body": "any",
                "headers": "dict",
                "success": "boolean"
            }
        )
    }
    
    async def run(self, context: WorkflowContext):
        """执行HTTP请求"""
        # 1. 获取配置（使用简化API）
        url = self.get_config('config.url') or self.get_config('url')
        method = self.get_config('config.method', 'GET').upper()
        timeout = self.get_config('config.timeout', 30)
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            request = self.get_input_value('request')
            if request:
                url = request.get('url', url)
                method = request.get('method', method)
        except ValueError:
            pass  # 没有输入参数
        
        # 3. 发送异步HTTP请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method, 
                    url=url,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    result = {
                        'status_code': response.status,
                        'body': await response.json(),
                        'headers': dict(response.headers),
                        'success': 200 <= response.status < 300
                    }
        except aiohttp.ClientError as e:
            raise NodeExecutionError(self.node_id, f"HTTP请求失败: {e}")
        except asyncio.TimeoutError:
            raise NodeExecutionError(self.node_id, "请求超时")
        
        # 4. 设置输出值
        self.set_output_value('response', result)
        context.log(f"HTTP请求完成: {method} {url} -> {result['status_code']}")
        
        return result
```

### 关键要点

1. ✅ 使用 `aiohttp` 等真正的异步库（不是 `requests`）
2. ✅ 使用 `self.get_config()` 简化配置获取
3. ✅ 使用 `self.get_input_value()` 获取输入
4. ✅ 使用 `self.set_output_value()` 设置输出
5. ✅ 完善的异常处理和日志记录

---

## 🌊 流式节点开发

### 流式节点结构

```python
from workflow_engine.core import Node, ParameterSchema, StreamChunk, WorkflowContext, register_node
import asyncio

@register_node('audio_processor')
class AudioProcessorNode(Node):
    """音频处理节点（流式）"""
    
    EXECUTION_MODE = 'streaming'
    
    INPUT_PARAMS = {
        "audio_in": ParameterSchema(
            is_streaming=True,
            schema={
                "audio_data": "bytes",
                "sample_rate": "integer",
                "format": "string"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "audio_out": ParameterSchema(
            is_streaming=True,
            schema={
                "audio_data": "bytes",
                "sample_rate": "integer",
                "format": "string",
                "processed": "boolean"
            }
        )
    }
    
    async def run(self, context: WorkflowContext):
        """初始化音频处理器"""
        self.effect = self.get_config('config.effect', 'none')
        context.log(f"音频处理器启动，效果: {self.effect}")
        
        # 流式节点持续运行
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            context.log("音频处理器关闭")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """处理接收到的 chunk"""
        if param_name == "audio_in":
            audio_data = chunk.data["audio_data"]
            sample_rate = chunk.data["sample_rate"]
            
            # 应用音频效果
            processed_audio = self._apply_effect(audio_data)
            
            # 发送处理后的音频
            await self.emit_chunk("audio_out", {
                "audio_data": processed_audio,
                "sample_rate": sample_rate,
                "format": chunk.data["format"],
                "processed": True
            })
    
    def _apply_effect(self, audio_data: bytes) -> bytes:
        """应用音频效果"""
        # 实际实现：应用降噪、均衡器等效果
        return audio_data
```

### 流式节点关键方法

#### `async def run(self, context)`

- 节点初始化逻辑
- 通常持续运行（`await asyncio.sleep(float('inf'))`）
- 可以初始化模型、建立连接等

#### `async def on_chunk_received(self, param_name, chunk)`

- 处理接收到的流式数据
- `param_name`: 输入参数名称
- `chunk.data`: 数据字典（已验证）

#### `async def emit_chunk(self, param_name, chunk_data)`

- 发送流式输出数据
- `param_name`: 输出参数名称
- `chunk_data`: 数据字典（会自动验证）

### 流式节点生命周期

```
1. 引擎启动 → 调用 __init__
2. 启动 consume_stream 后台任务（监听输入）
3. 调用 run（初始化）
4. 持续运行，处理输入 chunk
5. 接收结束信号 → 退出 consume_stream
6. asyncio.CancelledError → run 退出
```

---

## 🔀 混合节点开发

### 什么是混合节点？

混合节点既需要非流式输入（如配置数据），又需要处理流式输入（如实时数据）。

### Agent节点示例

```python
@register_node('agent_node')
class AgentNode(Node):
    """对话代理节点（混合模式）"""
    
    EXECUTION_MODE = 'hybrid'
    
    INPUT_PARAMS = {
        # 非流式输入：上下文数据
        "context_data": ParameterSchema(
            is_streaming=False,
            schema="dict"
        ),
        # 流式输入：用户文本
        "text_input": ParameterSchema(
            is_streaming=True,
            schema={"text": "string"}
        )
    }
    
    OUTPUT_PARAMS = {
        # 流式输出：AI回复
        "response_text": ParameterSchema(
            is_streaming=True,
            schema={"text": "string"}
        )
    }
    
    async def run(self, context: WorkflowContext):
        """初始化和非流式数据处理"""
        # 1. 等待非流式输入准备好
        context_data = self.get_input_value("context_data")
        
        # 2. 初始化模型
        self.model = self._load_model(context_data)
        context.log("Agent 初始化完成")
        
        # 3. 保持运行，处理流式输入
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            context.log("Agent 关闭")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """处理流式输入"""
        if param_name == "text_input":
            user_text = chunk.data["text"]
            
            # 生成回复
            response = await self.model.generate(user_text)
            
            # 发送回复
            await self.emit_chunk("response_text", {"text": response})
    
    def _load_model(self, context_data):
        """加载AI模型"""
        # 实际实现
        return MockModel()
```

---

## 🏗️ 系统架构

### 架构层次

```
┌─────────────────────────────────────────────────┐
│           应用层 (Application Layer)              │
│  - 配置文件定义                                    │
│  - 业务流程编排                                    │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         引擎层 (Engine Layer)                     │
│  - WorkflowEngine: 工作流引擎                     │
│  - 配置解析、节点管理、流程控制                      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         节点层 (Node Layer)                       │
│  - Node 基类: 定义节点接口                         │
│  - 内置节点: Start, HTTP, Transform, 等           │
│  - 自定义节点: 用户扩展                            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         核心组件层 (Core Layer)                   │
│  - Parameter: 参数系统                            │
│  - Connection: 连接系统                           │
│  - Context: 执行上下文                            │
└─────────────────────────────────────────────────┘
```

### 核心组件

#### 1. Parameter System (参数系统)

**文件**: `workflow_engine/core/parameter.py`

```python
class ParameterSchema:
    """参数结构定义"""
    is_streaming: bool          # 是否流式参数
    schema: Union[str, dict]    # 参数结构
    validate_value()            # 验证数据
    matches()                   # 判断schema是否匹配

class StreamChunk:
    """流式数据块"""
    data: dict                  # 数据内容
    schema: ParameterSchema     # 结构
    timestamp: float            # 时间戳

class Parameter:
    """参数实例"""
    name: str                   # 参数名称
    schema: ParameterSchema     # 参数结构
    value: Any                  # 非流式数据
    stream_queue: asyncio.Queue # 流式数据队列
```

#### 2. Connection System (连接系统)

**文件**: `workflow_engine/core/connection.py`

```python
class Connection:
    """参数连接"""
    source: (node_id, param_name)   # 源参数
    target: (node_id, param_name)   # 目标参数
    source_schema: ParameterSchema  # 源结构
    target_schema: ParameterSchema  # 目标结构
    is_streaming: bool              # 是否流式连接
    _validate()                     # 验证连接

class ConnectionManager:
    """连接管理器"""
    add_connection()          # 添加连接
    route_chunk()             # 路由流式数据
    transfer_value()          # 传输非流式数据
    get_streaming_connections()  # 获取流式连接
    get_data_connections()    # 获取非流式连接
```

#### 3. Node Base Class (节点基类)

**文件**: `workflow_engine/core/node.py`

```python
class Node(ABC):
    """节点基类"""
    
    # 类属性
    EXECUTION_MODE = 'sequential'  # 执行模式
    INPUT_PARAMS: Dict[str, ParameterSchema] = {}
    OUTPUT_PARAMS: Dict[str, ParameterSchema] = {}
    
    # 实例属性
    inputs: Dict[str, Parameter]   # 输入参数实例
    outputs: Dict[str, Parameter]  # 输出参数实例
    
    # 核心方法
    async def run(context) -> Any  # 节点运行入口（必须实现）
    async def execute(context)     # 顺序执行接口（可选实现）
    
    # 流式数据处理
    async def emit_chunk(param_name, chunk_data)
    async def consume_stream(param_name)
    async def on_chunk_received(param_name, chunk)
    
    # 非流式数据访问
    def set_output_value(param_name, value)
    def get_input_value(param_name)
    
    # 配置获取（简化API）
    def get_config(key, default=None)
```

#### 4. WorkflowEngine (工作流引擎)

**文件**: `workflow_engine/core/workflow.py`

```python
class WorkflowEngine:
    """工作流引擎"""
    
    # 核心方法
    def register_node_type(type, class)  # 注册节点类型
    def load_config(config_path)         # 加载配置
    async def start(initial_data)        # 启动工作流
    async def execute(**kwargs)          # 执行工作流
    
    # 内部方法
    def _build_connections()             # 构建连接
    def _get_execution_order()           # 拓扑排序
    def _transfer_non_streaming_outputs()  # 传递非流式输出
```

### 混合执行模式设计

#### 节点分类

引擎根据 `EXECUTION_MODE` 自动分类节点：

```python
sequential_nodes = []  # sequential + hybrid
streaming_nodes = []   # streaming

for node_id, node in self._nodes.items():
    if node.EXECUTION_MODE == 'streaming':
        streaming_nodes.append(node_id)
    else:
        sequential_nodes.append(node_id)
```

#### 连接分类

连接管理器根据 `is_streaming` 自动分类连接：

```python
# 流式连接：不影响执行顺序
_streaming_connections = []  # is_streaming == True

# 非流式连接：决定执行顺序
_data_connections = []       # is_streaming == False
```

#### 执行流程

```python
async def start(self, initial_data=None):
    """混合执行模式 - 启动工作流"""
    
    # 1. 分类节点
    sequential_nodes = [...]
    streaming_nodes = [...]
    
    # 2. 启动所有流式消费任务（后台）
    stream_tasks = []
    for node_id, node in self._nodes.items():
        for param_name, param in node.inputs.items():
            if param.is_streaming:
                task = asyncio.create_task(node.consume_stream(param_name))
                stream_tasks.append(task)
    
    # 3. 拓扑排序（只对 sequential/hybrid 节点）
    execution_order = self._get_execution_order(sequential_nodes)
    
    # 4. 按顺序执行 sequential/hybrid 节点
    for node_id in execution_order:
        await self._nodes[node_id].run_async(context)
        self._transfer_non_streaming_outputs(node)
    
    # 5. 等待流式任务完成（或超时）
    await asyncio.wait_for(
        asyncio.gather(*stream_tasks),
        timeout=stream_timeout
    )
```

#### 拓扑排序优化

只使用非流式连接构建依赖图，避免流式连接的循环依赖问题：

```python
def _get_execution_order(self, node_ids):
    """拓扑排序 - 只考虑非流式连接"""
    
    # 只使用非流式连接构建依赖图
    for conn in self._connection_manager.get_data_connections():
        if conn.source[0] in node_ids and conn.target[0] in node_ids:
            in_degree[conn.target[0]] += 1
            graph[conn.source[0]].append(conn.target[0])
    
    # Kahn 算法拓扑排序
    queue = [node_id for node_id in node_ids if in_degree[node_id] == 0]
    execution_order = []
    
    while queue:
        current = queue.pop(0)
        execution_order.append(current)
        
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    return execution_order
```

---

## 🔧 节点注册机制

### 方式 1：装饰器注册（推荐）

```python
from workflow_engine.core import register_node

@register_node('my_node')
class MyNode(Node):
    pass

# 使用
engine = WorkflowEngine()
import my_nodes  # 确保装饰器代码被执行
for node_type, node_class in get_registered_nodes().items():
    engine.register_node_type(node_type, node_class)
```

### 方式 2：手动注册

```python
from workflow_engine import WorkflowEngine
from my_nodes import MyCustomNode

engine = WorkflowEngine()
engine.register_node_type('my_custom', MyCustomNode)
```

### 方式 3：自动注册

```python
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

engine = WorkflowEngine()
auto_register_nodes(engine)  # 自动注册所有内置节点
```

---

## 📈 最佳实践

### 节点开发

1. **保持单一职责**：每个节点只做一件事
2. **使用简化API**：使用 `get_config()` 获取配置
3. **完善错误处理**：捕获并记录详细错误信息
4. **添加详细日志**：记录关键执行步骤
5. **参数验证**：验证输入参数的有效性

### 异步编程

1. ✅ 使用真正的异步库（aiohttp、asyncpg）
2. ✅ 避免阻塞操作
3. ✅ 合理使用 `asyncio.gather()` 并发执行
4. ✅ 设置超时时间防止挂起
5. ❌ 不要在异步函数中使用 `requests`、`time.sleep()`

### 流式节点

1. **持续运行**：使用 `await asyncio.sleep(float('inf'))`
2. **优雅关闭**：捕获 `asyncio.CancelledError`
3. **批处理优化**：合并小chunk提高吞吐量
4. **背压控制**：监控队列大小，防止内存溢出
5. **错误隔离**：单个chunk错误不影响后续处理

### 性能优化

1. **懒加载**：延迟初始化重资源
2. **连接复用**：复用数据库连接、HTTP会话
3. **并发执行**：充分利用异步并发
4. **内存管理**：及时释放大对象
5. **监控指标**：记录执行时间、内存使用

---

## 🧪 测试策略

### 单元测试

```python
import pytest
from workflow_engine.core import WorkflowContext

@pytest.mark.asyncio
async def test_my_node():
    node = MyNode('test_node', {'param': 'value'})
    context = WorkflowContext()
    
    # 设置输入
    node.set_input_value('input_data', {'test': 'data'})
    
    # 执行
    result = await node.run(context)
    
    # 验证输出
    assert result['processed'] == True
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_workflow():
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    engine.load_config('test_workflow.yaml')
    
    context = await engine.start()
    
    # 验证结果
    output = context.get_node_output('output')
    assert output is not None
```

---

## 🚀 扩展开发

### 添加新的执行模式

1. 在 `Node` 类中定义新的 `EXECUTION_MODE`
2. 在 `WorkflowEngine` 中处理新模式
3. 更新文档和示例

### 添加新的参数类型

1. 在 `ParameterSchema` 中添加新类型验证
2. 更新 `validate_value()` 方法
3. 添加类型转换支持

### 自定义连接路由

1. 继承 `ConnectionManager`
2. 重写 `route_chunk()` 方法
3. 实现自定义路由逻辑

---

## 📚 参考资源

- **源代码**: `workflow_engine/` 目录
- **示例代码**: `examples/` 目录
- **用户指南**: `USER_GUIDE.md`
- **变更历史**: `CHANGELOG.md`

---

**文档版本**: 2.0.0  
**最后更新**: 2025-10-20

