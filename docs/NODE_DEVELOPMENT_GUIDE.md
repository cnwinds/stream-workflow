# 节点开发指南

本指南将帮助您开发自定义节点，支持流式和非流式数据处理。

## 目录

1. [节点基础](#节点基础)
2. [节点注册](#节点注册)
3. [参数定义规范](#参数定义规范)
4. [流式节点开发](#流式节点开发)
5. [非流式节点开发](#非流式节点开发)
6. [最佳实践](#最佳实践)
7. [完整示例](#完整示例)

---

## 节点基础

### 继承 Node 基类

所有自定义节点都必须继承 `Node` 基类：

```python
from workflow_engine.core import Node, ParameterSchema, WorkflowContext

class MyCustomNode(Node):
    """我的自定义节点"""
    
    # 定义输入参数（类属性）
    INPUT_PARAMS = {}
    
    # 定义输出参数（类属性）
    OUTPUT_PARAMS = {}
    
    async def execute_async(self, context: WorkflowContext):
        """执行节点逻辑"""
        pass
```

### 必需实现的方法

- `execute_async(self, context)`: 异步执行节点逻辑（新架构）
- 或 `execute(self, context)`: 同步执行节点逻辑（旧架构兼容）

---

## 节点注册

节点开发完成后，需要注册到工作流引擎才能使用。支持三种注册方式：

### 方式 1：手动注册（灵活）

```python
from workflow_engine import WorkflowEngine
from my_nodes import MyCustomNode

engine = WorkflowEngine()
engine.register_node_type('my_custom', MyCustomNode)
```

**优点**：完全控制注册过程，适合动态加载节点  
**缺点**：需要手动管理注册代码

### 方式 2：自动注册（便捷）

将节点添加到 `workflow_engine/nodes/__init__.py` 的 `BUILTIN_NODES` 字典：

```python
# workflow_engine/nodes/__init__.py
from .my_custom_node import MyCustomNode

BUILTIN_NODES = {
    # ... 其他节点
    'my_custom': MyCustomNode,
}
```

然后使用自动注册函数：

```python
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

engine = WorkflowEngine()
auto_register_nodes(engine)  # 自动注册所有内置节点
```

**优点**：一次注册所有节点，代码简洁  
**缺点**：需要修改内置模块文件

### 方式 3：装饰器注册（优雅）

使用 `@register_node` 装饰器：

```python
from workflow_engine.core import Node, register_node

@register_node('my_custom')
class MyCustomNode(Node):
    """我的自定义节点"""
    pass
```

然后自动加载所有装饰器标记的节点：

```python
from workflow_engine import WorkflowEngine
from workflow_engine.core.node import get_registered_nodes

engine = WorkflowEngine()

# 导入包含装饰器节点的模块
import my_nodes  # 确保装饰器代码被执行

# 自动注册所有装饰器标记的节点
for node_type, node_class in get_registered_nodes().items():
    engine.register_node_type(node_type, node_class)
```

**优点**：声明式，代码清晰，不需要修改其他文件  
**缺点**：需要确保模块被导入

### 节点类型命名规范

- 使用小写字母和下划线：`my_custom_node`
- 描述节点功能：`audio_processor`, `text_classifier`
- 避免与内置节点冲突

---

## 参数定义规范

### 参数结构定义

节点的输入输出参数通过类属性 `INPUT_PARAMS` 和 `OUTPUT_PARAMS` 定义：

```python
class MyNode(Node):
    INPUT_PARAMS = {
        "param_name": ParameterSchema(
            is_streaming=False,  # 是否流式参数
            schema="string"      # 参数结构定义
        )
    }
    
    OUTPUT_PARAMS = {
        "result": ParameterSchema(
            is_streaming=False,
            schema="string"
        )
    }
```

### 支持的数据类型

#### 简单类型

```python
schema="string"    # 字符串
schema="integer"   # 整数
schema="float"     # 浮点数
schema="boolean"   # 布尔值
schema="bytes"     # 字节数据
schema="dict"      # 字典
schema="list"      # 列表
schema="any"       # 任意类型
```

#### 结构体（字典类型）

```python
schema={
    "field1": "string",
    "field2": "integer",
    "field3": "float"
}
```

### 流式参数 vs 非流式参数

#### 非流式参数

```python
ParameterSchema(
    is_streaming=False,
    schema="string"
)
```

- 一次性传递完整数据
- 适用于：配置、批量数据、最终结果

#### 流式参数

```python
ParameterSchema(
    is_streaming=True,
    schema={
        "data": "bytes",
        "timestamp": "float"
    }
)
```

- 数据以 chunk 形式增量传递
- 适用于：音频流、视频流、实时文本

---

## 流式节点开发

### 基本结构

```python
from workflow_engine.core import Node, ParameterSchema, StreamChunk, WorkflowContext
import asyncio

class StreamingNode(Node):
    """流式节点示例"""
    
    INPUT_PARAMS = {
        "stream_in": ParameterSchema(
            is_streaming=True,
            schema={"data": "bytes"}
        )
    }
    
    OUTPUT_PARAMS = {
        "stream_out": ParameterSchema(
            is_streaming=True,
            schema={"data": "bytes", "processed": "boolean"}
        )
    }
    
    async def execute_async(self, context: WorkflowContext):
        """初始化（持续运行）"""
        context.log(f"流式节点启动: {self.node_id}")
        try:
            await asyncio.sleep(float('inf'))  # 保持运行
        except asyncio.CancelledError:
            context.log(f"流式节点关闭: {self.node_id}")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """处理接收到的 chunk"""
        if param_name == "stream_in":
            # 处理输入数据
            input_data = chunk.data["data"]
            processed_data = self._process(input_data)
            
            # 发送输出 chunk
            await self.emit_chunk("stream_out", {
                "data": processed_data,
                "processed": True
            })
    
    def _process(self, data):
        """数据处理逻辑"""
        return data  # 示例
```

### 关键方法

#### `async def execute_async(self, context)`

- 节点初始化逻辑
- 通常持续运行（`await asyncio.sleep(float('inf'))`）
- 可以在这里初始化模型、建立连接等

#### `async def on_chunk_received(self, param_name, chunk)`

- 处理接收到的流式数据
- `param_name`: 输入参数名称
- `chunk.data`: 数据字典（根据 schema 验证）

#### `async def emit_chunk(self, param_name, chunk_data)`

- 发送流式输出数据
- `param_name`: 输出参数名称
- `chunk_data`: 数据字典（会自动验证）

### 流式节点生命周期

```
1. 引擎启动 -> 调用 __init__
2. 启动 consume_stream 后台任务（监听输入）
3. 调用 execute_async（初始化）
4. 持续运行，处理输入 chunk
5. 接收结束信号 -> 退出 consume_stream
6. asyncio.CancelledError -> execute_async 退出
```

---

## 非流式节点开发

### 基本结构

```python
from workflow_engine.core import Node, ParameterSchema, WorkflowContext

class BatchNode(Node):
    """批量处理节点示例"""
    
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=False,
            schema="dict"
        )
    }
    
    OUTPUT_PARAMS = {
        "output_data": ParameterSchema(
            is_streaming=False,
            schema="dict"
        )
    }
    
    async def execute_async(self, context: WorkflowContext):
        """执行批量处理"""
        # 获取输入数据
        input_data = self.get_input_value("input_data")
        
        # 处理数据
        result = self._process(input_data)
        
        # 设置输出
        self.set_output_value("output_data", result)
        
        context.log(f"批量处理完成: {self.node_id}")
    
    def _process(self, data):
        """数据处理逻辑"""
        return {"processed": True, "data": data}
```

### 关键方法

#### `self.get_input_value(param_name)`

- 获取非流式输入参数的值
- 返回值已通过 schema 验证

#### `self.set_output_value(param_name, value)`

- 设置非流式输出参数的值
- 值会自动验证并保存

---

## 最佳实践

### 1. 错误处理

```python
async def execute_async(self, context: WorkflowContext):
    try:
        # 执行逻辑
        result = await self._do_something()
    except ValueError as e:
        context.log(f"参数错误: {e}", level="ERROR")
        raise
    except Exception as e:
        context.log(f"未知错误: {e}", level="ERROR")
        raise
```

### 2. 日志记录

```python
context.log("开始处理", level="INFO")
context.log("处理成功", level="SUCCESS")
context.log("警告信息", level="WARNING")
context.log("错误信息", level="ERROR")
```

### 3. 配置参数

```python
class MyNode(Node):
    async def execute_async(self, context: WorkflowContext):
        # 从配置中获取参数，提供默认值
        threshold = self.config.get('threshold', 0.5)
        max_retries = self.config.get('max_retries', 3)
        
        context.log(f"配置: threshold={threshold}, max_retries={max_retries}")
```

### 4. 参数验证

```python
async def execute_async(self, context: WorkflowContext):
    # 验证必需配置
    if 'api_key' not in self.config:
        raise ValueError("缺少必需配置: api_key")
    
    # 验证参数范围
    temperature = self.config.get('temperature', 0.7)
    if not 0 <= temperature <= 2:
        raise ValueError(f"temperature 必须在 0-2 之间，当前: {temperature}")
```

### 5. 资源管理

```python
class MyNode(Node):
    def __init__(self, node_id, config, connection_manager=None):
        super().__init__(node_id, config, connection_manager)
        self.resource = None
    
    async def execute_async(self, context: WorkflowContext):
        try:
            # 初始化资源
            self.resource = await self._init_resource()
            
            # 执行逻辑
            await asyncio.sleep(float('inf'))
        finally:
            # 清理资源
            if self.resource:
                await self.resource.close()
```

### 6. 性能优化

```python
async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
    # 避免在每个 chunk 中重复初始化
    if not hasattr(self, '_processor'):
        self._processor = self._create_processor()
    
    # 批量处理（减少 I/O）
    self._buffer.append(chunk.data)
    if len(self._buffer) >= self.batch_size:
        await self._process_batch(self._buffer)
        self._buffer.clear()
```

---

## 完整示例

### 示例 1：流式音频处理节点

```python
from workflow_engine.core import Node, ParameterSchema, StreamChunk, WorkflowContext, register_node
import asyncio

@register_node('audio_processor')
class AudioProcessorNode(Node):
    """音频处理节点"""
    
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
    
    async def execute_async(self, context: WorkflowContext):
        """初始化音频处理器"""
        self.effect = self.config.get('effect', 'none')
        context.log(f"音频处理器启动，效果: {self.effect}")
        
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            context.log("音频处理器关闭")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """处理音频 chunk"""
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

### 示例 2：批量数据处理节点

```python
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, register_node

@register_node('batch_processor')
class BatchProcessorNode(Node):
    """批量数据处理节点"""
    
    INPUT_PARAMS = {
        "data_list": ParameterSchema(
            is_streaming=False,
            schema="list"
        )
    }
    
    OUTPUT_PARAMS = {
        "processed_list": ParameterSchema(
            is_streaming=False,
            schema="list"
        ),
        "statistics": ParameterSchema(
            is_streaming=False,
            schema={
                "total": "integer",
                "processed": "integer",
                "failed": "integer"
            }
        )
    }
    
    async def execute_async(self, context: WorkflowContext):
        """批量处理数据"""
        # 获取输入
        data_list = self.get_input_value("data_list")
        
        context.log(f"开始处理 {len(data_list)} 条数据")
        
        # 处理数据
        processed_list = []
        failed_count = 0
        
        for item in data_list:
            try:
                processed_item = self._process_item(item)
                processed_list.append(processed_item)
            except Exception as e:
                context.log(f"处理失败: {e}", level="WARNING")
                failed_count += 1
        
        # 设置输出
        self.set_output_value("processed_list", processed_list)
        self.set_output_value("statistics", {
            "total": len(data_list),
            "processed": len(processed_list),
            "failed": failed_count
        })
        
        context.log(f"处理完成: 成功 {len(processed_list)}, 失败 {failed_count}")
    
    def _process_item(self, item):
        """处理单个数据项"""
        # 实际处理逻辑
        return item
```

### 示例 3：混合流式/非流式节点

```python
from workflow_engine.core import Node, ParameterSchema, StreamChunk, WorkflowContext, register_node
import asyncio

@register_node('hybrid_node')
class HybridNode(Node):
    """混合节点：流式输入 + 非流式配置"""
    
    INPUT_PARAMS = {
        "stream_data": ParameterSchema(
            is_streaming=True,
            schema={"value": "float"}
        ),
        "config_data": ParameterSchema(
            is_streaming=False,
            schema={"threshold": "float", "mode": "string"}
        )
    }
    
    OUTPUT_PARAMS = {
        "filtered_stream": ParameterSchema(
            is_streaming=True,
            schema={"value": "float", "passed": "boolean"}
        )
    }
    
    async def execute_async(self, context: WorkflowContext):
        """初始化"""
        # 获取非流式配置
        config = self.get_input_value("config_data")
        self.threshold = config["threshold"]
        self.mode = config["mode"]
        
        context.log(f"混合节点启动: threshold={self.threshold}, mode={self.mode}")
        
        try:
            await asyncio.sleep(float('inf'))
        except asyncio.CancelledError:
            context.log("混合节点关闭")
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """处理流式输入"""
        if param_name == "stream_data":
            value = chunk.data["value"]
            
            # 根据配置过滤数据
            passed = value >= self.threshold
            
            if passed or self.mode == "all":
                await self.emit_chunk("filtered_stream", {
                    "value": value,
                    "passed": passed
                })
```

---

## 总结

- **参数在代码中定义**：使用 `INPUT_PARAMS` 和 `OUTPUT_PARAMS` 类属性
- **支持三种注册方式**：手动、自动、装饰器
- **流式和非流式混合**：根据业务需求选择合适的参数类型
- **完善的类型验证**：引擎自动验证参数结构匹配
- **清晰的生命周期**：理解节点执行流程和资源管理

开始开发您的自定义节点吧！🚀

