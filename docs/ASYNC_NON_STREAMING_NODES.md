# 异步非流式节点开发指南

## 概述

异步非流式节点是一种特殊的节点类型，它具有以下特征：
- **异步执行**：使用 `async/await` 语法，支持非阻塞 I/O 操作
- **非流式参数**：输入和输出都是完整的数据值，不是数据流
- **顺序执行**：在工作流中按拓扑排序顺序执行
- **适用场景**：HTTP请求、数据库查询、文件读写等 I/O 密集型操作

---

## HTTP节点示例

### 节点定义

```python
import aiohttp
import asyncio
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, NodeExecutionError, register_node


@register_node('http')
class HttpNode(Node):
    """HTTP请求节点（异步非流式）"""
    
    # 定义输入输出参数
    INPUT_PARAMS = {
        "request": ParameterSchema(
            is_streaming=False,  # 非流式
            schema={
                "url": "string",
                "method": "string",
                "headers": "dict",
                "params": "dict",
                "body": "dict"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "response": ParameterSchema(
            is_streaming=False,  # 非流式
            schema={
                "status_code": "integer",
                "body": "any",
                "headers": "dict",
                "success": "boolean"
            }
        )
    }
    
    async def execute_async(self, context: WorkflowContext):
        """执行HTTP请求"""
        # 1. 从配置获取参数
        actual_config = self.config.get('config', self.config)
        url = actual_config.get('url')
        method = actual_config.get('method', 'GET').upper()
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            request = self.get_input_value('request')
            if request:
                url = request.get('url', url)
                method = request.get('method', method)
        except ValueError:
            pass  # 没有输入参数
        
        # 3. 发送异步HTTP请求
        async with aiohttp.ClientSession() as session:
            async with session.request(method=method, url=url) as response:
                result = {
                    'status_code': response.status,
                    'body': await response.json(),
                    'headers': dict(response.headers),
                    'success': 200 <= response.status < 300
                }
        
        # 4. 设置输出值
        self.set_output_value('response', result)
        
        return result
```

### 关键点

1. **参数是非流式的**：`is_streaming=False`
2. **使用 `async def execute_async`**：支持异步操作
3. **使用 `self.get_input_value()`**：获取输入参数值
4. **使用 `self.set_output_value()`**：设置输出参数值
5. **使用 `aiohttp`**：真正的异步HTTP库（不是 `requests`）

---

## 配置文件

```yaml
workflow:
  name: "异步HTTP工作流"
  
  nodes:
    - id: "get_user"
      type: "http"
      config:
        url: "https://api.example.com/users/1"
        method: "GET"
        timeout: 10
    
    - id: "process"
      type: "transform"
      inputs: ["get_user"]
    
    - id: "output"
      type: "output"
      inputs: ["process"]
```

---

## 执行流程

### 非流式工作流执行特点

1. **顺序执行**：节点按拓扑排序顺序依次执行
2. **等待完成**：每个节点执行完成后才执行下一个节点
3. **自动传递值**：节点输出值自动传递到下游节点的输入参数

```python
# 引擎执行逻辑（简化版）
for node_id in execution_order:
    node = nodes[node_id]
    
    # 执行节点
    await node.run_async(context)
    
    # 传递输出值到下游节点
    for output_param_name, output_param in node.outputs.items():
        if not output_param.is_streaming and output_param.value is not None:
            # 查找连接
            for conn in connections:
                if conn.source == (node_id, output_param_name):
                    # 设置目标节点的输入值
                    target_node.inputs[conn.target[1]].value = output_param.value
```

---

## 与流式节点的对比

| 特性 | 异步非流式节点 | 流式节点 |
|------|---------------|---------|
| **参数类型** | `is_streaming=False` | `is_streaming=True` |
| **执行方式** | 顺序执行 | 并发执行 |
| **数据传递** | 完整值 | 数据块（chunks） |
| **输入方法** | `get_input_value()` | `on_chunk_received()` |
| **输出方法** | `set_output_value()` | `emit_chunk()` |
| **生命周期** | 执行完成即结束 | 持续运行 |
| **适用场景** | HTTP请求、数据库查询 | 音视频处理、WebSocket |

---

## 最佳实践

### 1. 使用异步I/O库

```python
# ✅ 推荐：使用异步库
async with aiohttp.ClientSession() as session:
    response = await session.get(url)

# ❌ 不推荐：使用同步库（会阻塞事件循环）
response = requests.get(url)  # 阻塞！
```

### 2. 错误处理

```python
async def execute_async(self, context: WorkflowContext):
    try:
        result = await self._do_async_operation()
        self.set_output_value('result', result)
    except aiohttp.ClientError as e:
        raise NodeExecutionError(self.node_id, f"HTTP请求失败: {e}")
    except asyncio.TimeoutError:
        raise NodeExecutionError(self.node_id, "请求超时")
```

### 3. 资源管理

```python
class MyNode(Node):
    def __init__(self, node_id, config, connection_manager=None):
        super().__init__(node_id, config, connection_manager)
        self._session = None
    
    async def execute_async(self, context):
        # 创建会话（如果不存在）
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        # 使用会话
        async with self._session.get(url) as response:
            ...
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 清理资源
        if self._session:
            await self._session.close()
```

### 4. 配置灵活性

```python
# 支持两种配置方式
async def execute_async(self, context):
    # 方式1：从配置文件获取
    actual_config = self.config.get('config', self.config)
    url = actual_config.get('url')
    
    # 方式2：从输入参数获取（优先级更高）
    try:
        request = self.get_input_value('request')
        if request:
            url = request.get('url', url)
    except ValueError:
        pass  # 没有输入参数，使用配置文件的值
```

---

## 常见问题

### Q: 为什么HTTP节点要使用aiohttp而不是requests？

A: `requests` 是同步库，会阻塞事件循环，导致整个异步工作流性能下降。`aiohttp` 是真正的异步HTTP库，支持并发请求。

### Q: 非流式节点可以有多个输入参数吗？

A: 可以！定义多个输入参数，然后通过 `get_input_value()` 分别获取：

```python
INPUT_PARAMS = {
    "data": ParameterSchema(is_streaming=False, schema="dict"),
    "config": ParameterSchema(is_streaming=False, schema="dict")
}

async def execute_async(self, context):
    data = self.get_input_value('data')
    config = self.get_input_value('config')
```

### Q: 如何在配置文件中指定参数连接？

A: 使用 `connections` 字段：

```yaml
connections:
  - from: "node1.output"
    to: "node2.input"
```

或者使用传统的 `inputs` 字段（向后兼容）：

```yaml
nodes:
  - id: "node2"
    inputs: ["node1"]
```

### Q: 非流式节点执行失败会怎样？

A: 引擎会捕获异常并终止工作流执行，下游节点不会执行。

---

## 完整示例

参考以下文件：
- **节点实现**：`workflow_engine/nodes/http_node.py`
- **配置文件**：`examples/workflow_http_async.yaml`
- **运行示例**：`examples/run_http_async_example.py`

---

## 参考文档

- [节点开发指南](NODE_DEVELOPMENT_GUIDE.md)
- [流式工作流指南](STREAMING_WORKFLOW_GUIDE.md)
- [数据输入指南](DATA_INPUT_GUIDE.md)

