# Python工作流引擎框架

一个类似 n8n 的 Python 工作流引擎框架，可以通过配置文件定义和执行复杂的数据处理流程。

## 🌟 特性

- 📝 **配置驱动**: 通过 YAML 或 JSON 配置文件定义工作流
- 🔌 **插件化节点**: 轻松扩展自定义节点类型
- 🔄 **自动依赖解析**: 智能的拓扑排序，自动确定节点执行顺序
- 📊 **数据流转**: 节点间自动传递数据，支持多输入多输出
- 🎯 **条件分支**: 支持基于条件的流程分支
- 🔍 **执行日志**: 详细的执行日志和错误追踪
- 🛠️ **内置节点**: 提供常用的节点类型（HTTP请求、数据转换、条件判断等）
- 🌊 **流式处理**: 支持实时音频/视频流、WebSocket 实时通信
- 🔗 **多端口连接**: 参数级精确连接，自动类型验证
- ⚡ **异步并发**: 基于 asyncio 的高性能异步执行
- 🔀 **混合执行模式**: 优雅融合流式和非流式节点，支持反馈回路
- 🔍 **上下文参数引用**: 使用 `${node_id.field}` 语法灵活引用节点输出，无需配置连接（新增）

## 📦 安装

```bash
# 克隆仓库
git clone <repository-url>
cd workflow_engine

# 安装依赖
pip install -r requirements.txt
```

## 🚀 快速开始

### 1. 创建工作流配置文件

创建一个 YAML 配置文件 `my_workflow.yaml`：

```yaml
workflow:
  name: "我的第一个工作流"
  description: "简单的数据处理示例"
  version: "1.0.0"
  
  nodes:
    - id: "start"
      type: "start"
      name: "开始"
      data:
        message: "Hello, Workflow!"
        value: 42
    
    - id: "process"
      type: "transform"
      name: "处理数据"
      inputs:
        - "start"
      operation: "custom"
      config:
        expression: "{'result': data['message'] + ' Value: ' + str(data['value'])}"
    
    - id: "output"
      type: "output"
      name: "输出结果"
      inputs:
        - "process"
      format: "json"
```

### 2. 编写执行代码

```python
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import StartNode, TransformNode, OutputNode

# 创建引擎实例
engine = WorkflowEngine()

# 注册节点类型
engine.register_node_type('start', StartNode)
engine.register_node_type('transform', TransformNode)
engine.register_node_type('output', OutputNode)

# 加载并执行工作流
engine.load_config('my_workflow.yaml')
context = engine.execute()

# 查看执行日志
for log in context.get_logs():
    print(f"[{log['level']}] {log['message']}")
```

### 3. 运行示例

```bash
# 运行自定义节点示例
python examples/custom_node_example.py

# 运行混合流程示例
python examples/run_mixed_example.py
```

## 📚 核心概念

### 节点 (Node)

节点是工作流的基本执行单元。每个节点：
- 有唯一的 ID
- 有特定的类型（type）
- 可以有多个输入节点
- 产生一个输出结果
- 输出会自动保存到执行上下文中

### 工作流配置

工作流配置定义了：
- **workflow**: 工作流元信息
  - `name`: 工作流名称
  - `description`: 描述
  - `version`: 版本号
  - `nodes`: 节点列表

- **nodes**: 节点配置列表
  - `id`: 节点唯一标识符
  - `type`: 节点类型
  - `name`: 节点名称
  - `inputs`: 输入节点ID列表
  - 其他节点特定的配置参数

### 执行上下文 (WorkflowContext)

执行上下文在整个工作流执行期间存储：
- 每个节点的输出结果
- 全局变量
- 执行日志
- 执行开始时间

## 🔧 内置节点类型

### StartNode (起始节点)

工作流的起点，提供初始数据。

```yaml
- id: "start"
  type: "start"
  name: "开始"
  data:
    key1: "value1"
    key2: 123
```

### HttpNode (HTTP请求节点)

发送HTTP请求。

```yaml
- id: "api_call"
  type: "http"
  name: "调用API"
  url: "https://api.example.com/data"
  method: "GET"  # GET, POST, PUT, DELETE等
  headers:
    Authorization: "Bearer token"
  params:
    page: 1
  timeout: 30
```

### TransformNode (数据转换节点)

对数据进行各种转换操作。

支持的操作：

**extract** - 提取字段：
```yaml
- id: "extract"
  type: "transform"
  name: "提取字段"
  inputs: ["previous_node"]
  operation: "extract"
  config:
    fields:
      - "name"
      - "email"
```

**map** - 映射/重命名字段：
```yaml
- id: "rename"
  type: "transform"
  name: "重命名字段"
  inputs: ["previous_node"]
  operation: "map"
  config:
    mapping:
      old_name: "new_name"
      age: "年龄"
```

**custom** - 自定义转换（Python表达式）：
```yaml
- id: "calculate"
  type: "transform"
  name: "自定义计算"
  inputs: ["previous_node"]
  operation: "custom"
  config:
    expression: "{'total': sum(data['values']), 'count': len(data['values'])}"
```

### ConditionNode (条件判断节点)

根据条件决定数据流向。

```yaml
- id: "check"
  type: "condition"
  name: "检查条件"
  inputs: ["previous_node"]
  conditions:
    - branch: "high"
      expression: "score >= 90"
    - branch: "medium"
      expression: "score >= 60"
  default_branch: "low"
```

### MergeNode (合并节点)

合并多个输入节点的数据。

```yaml
- id: "merge"
  type: "merge"
  name: "合并数据"
  inputs: ["node1", "node2", "node3"]
  strategy: "merge"  # merge, concat, first, last
```

### OutputNode (输出节点)

输出工作流的最终结果。

```yaml
- id: "output"
  type: "output"
  name: "输出结果"
  inputs: ["final_node"]
  format: "json"  # json, text, raw
  save_to_file: true
  file_path: "output.json"
```

## 🔍 上下文参数引用（新功能）

对于顺序执行的节点，你可以使用 `${node_id.field}` 语法直接从上下文中引用其他节点的输出，无需配置复杂的连接。

### 使用方法

在节点配置中，使用 `${}` 语法引用其他节点的输出：

```yaml
workflow:
  name: "参数引用示例"
  nodes:
    # 提供数据的节点
    - id: "data_source"
      type: "start_node"
      config:
        data:
          name: "张三"
          score: 85
    
    # 使用参数引用获取数据
    - id: "process"
      type: "http_node"
      inputs:
        - "data_source"
      config:
        url: "https://api.example.com/submit"
        method: "POST"
        body:
          # 引用 data_source 节点的输出字段
          student_name: "${data_source.name}"
          score: "${data_source.score}"
```

### 支持的引用语法

- `${node_id}` - 引用整个节点输出
- `${node_id.field}` - 引用节点输出的特定字段
- `${node_id.user.name}` - 引用嵌套字段
- `${global.var_name}` - 引用全局变量

### 优势

✅ **配置简单** - 无需定义connections  
✅ **灵活引用** - 可以引用任意节点的任意字段  
✅ **支持嵌套** - 支持深层嵌套字段访问  
✅ **字符串模板** - 支持在字符串中嵌入引用

### 完整文档

参见：[工作流引擎完整指南](docs/COMPLETE_GUIDE.md)

### 精简演示

我们提供了两个核心演示示例：

1. **自定义节点示例** - `examples/custom_node_example.py`
   - 展示如何创建自定义节点
   - 演示简化的 `get_config()` API
   - 计算流程：100 + 50 = 150, 150 * 2 = 300

2. **混合流程示例** - `examples/run_mixed_example.py`
   - 展示参数引用功能
   - 演示混合执行模式
   - 学生成绩评估流程

## 🎨 自定义节点

创建自定义节点非常简单，只需继承 `Node` 基类并实现 `execute_async` 方法：

```python
from workflow_engine.core import Node, WorkflowContext, register_node

@register_node('my_custom')  # 使用装饰器自动注册
class MyCustomNode(Node):
    """自定义节点示例"""
    
    EXECUTION_MODE = 'sequential'  # 或 'streaming' / 'hybrid'
    
    async def execute_async(self, context: WorkflowContext):
        """
        执行节点逻辑
        
        可以使用:
        - self.get_config(): 获取配置参数（简化API）✨
        - self.get_input_data(context): 获取输入数据
        - context.log(): 记录日志
        - context.get_node_output(): 从上下文获取其他节点输出
        """
        # ✨ 使用简化的配置获取 API
        param1 = self.get_config('config.param1')
        param2 = self.get_config('config.param2', 'default_value')
        timeout = self.get_config('timeout', 30)
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        # 执行自定义逻辑
        result = await self._do_something(input_data, param1, param2)
        
        # 记录日志
        context.log(f"处理完成: {result}")
        
        # 返回结果
        return result
    
    async def _do_something(self, data, param1, param2):
        # 实现你的逻辑
        return {"processed": True}
```

然后在配置文件中使用：

```yaml
- id: "custom_step"
  type: "my_custom"
  name: "自定义步骤"
  inputs: ["previous_node"]
  param1: "value1"
  param2: "value2"
```

## 🌊 流式处理（新增）

### 什么是流式处理？

流式处理允许数据以小块（chunk）的形式增量传输和处理，适用于：
- 实时音频/视频处理
- WebSocket 实时通信
- 大文件分块处理
- 低延迟场景

### 流式工作流示例

```yaml
workflow:
  name: "语音对话流程"
  nodes:
    - id: "vad"
      type: "vad_node"
      config:
        threshold: 0.5
    
    - id: "asr"
      type: "asr_node"
      config:
        model: "whisper"
    
    - id: "agent"
      type: "agent_node"
      config:
        model: "gpt-4"
    
    - id: "tts"
      type: "tts_node"
      config:
        voice: "zh-CN-XiaoxiaoNeural"
  
  # 参数级连接 - 引擎自动验证类型匹配
  connections:
    - from: "vad.audio_stream"
      to: "asr.audio_in"
    - from: "asr.text_stream"
      to: "agent.text_input"
    - from: "agent.response_text"
      to: "tts.text_input"
```

### 运行流式示例

```python
import asyncio
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import auto_register_nodes

async def main():
    engine = WorkflowEngine()
    auto_register_nodes(engine)
    
    engine.load_config('workflow_streaming.yaml')
    context = await engine.execute_async()

asyncio.run(main())
```

### 开发流式节点

```python
from workflow_engine.core import Node, ParameterSchema, StreamChunk, register_node
import asyncio

@register_node('my_stream_node')
class MyStreamNode(Node):
    # 定义参数结构
    INPUT_PARAMS = {
        "stream_in": ParameterSchema(
            is_streaming=True,
            schema={"data": "bytes", "timestamp": "float"}
        )
    }
    
    OUTPUT_PARAMS = {
        "stream_out": ParameterSchema(
            is_streaming=True,
            schema={"data": "bytes", "processed": "boolean"}
        )
    }
    
    async def execute_async(self, context):
        """初始化（持续运行）"""
        context.log("流式节点启动")
        await asyncio.sleep(float('inf'))
    
    async def on_chunk_received(self, param_name, chunk: StreamChunk):
        """处理输入 chunk"""
        if param_name == "stream_in":
            # 处理数据
            data = chunk.data["data"]
            processed_data = self._process(data)
            
            # 发送输出 chunk
            await self.emit_chunk("stream_out", {
                "data": processed_data,
                "processed": True
            })
```

详细开发指南请参考：[节点开发指南](docs/NODE_DEVELOPMENT_GUIDE.md)

## 📖 完整示例

查看 `examples/` 目录下的完整示例：

- `workflow_simple.yaml` - 简单的数据处理流程
- `workflow_http.yaml` - HTTP API调用和数据处理
- `workflow_condition.yaml` - 条件判断和分支
- `workflow_complex.yaml` - 复杂的多节点协作流程
- `workflow_streaming.yaml` - 流式音视频处理流程（新增）
- `run_example.py` - 运行所有示例的脚本
- `run_streaming_example.py` - 运行流式示例（新增）

## 🏗️ 架构设计

```
workflow_engine/
├── core/
│   ├── node.py           # 节点基类
│   ├── context.py        # 执行上下文
│   ├── workflow.py       # 工作流引擎
│   └── exceptions.py     # 自定义异常
├── nodes/
│   ├── start_node.py     # 起始节点
│   ├── http_node.py      # HTTP请求节点
│   ├── transform_node.py # 数据转换节点
│   ├── condition_node.py # 条件判断节点
│   ├── merge_node.py     # 合并节点
│   └── output_node.py    # 输出节点
└── examples/
    ├── workflow_*.yaml   # 示例配置文件
    └── run_example.py    # 示例运行脚本
```

## 🔍 执行流程

1. **加载配置**: 解析 YAML/JSON 配置文件
2. **验证配置**: 检查配置完整性和正确性
3. **构建节点**: 根据配置创建节点实例
4. **拓扑排序**: 分析依赖关系，确定执行顺序
5. **执行节点**: 按顺序执行每个节点
6. **传递数据**: 自动在节点间传递数据
7. **记录日志**: 记录执行过程和结果

## 🔀 混合执行模式

工作流引擎支持三种节点执行模式，可以在同一个工作流中优雅地混合使用：

### 节点执行模式

| 模式 | 描述 | 执行方式 | 典型应用 |
|------|------|----------|----------|
| **sequential** | 顺序执行节点 | 按拓扑顺序执行，执行完返回 | HTTP请求、数据库查询、数据转换 |
| **streaming** | 流式处理节点 | 数据驱动，实时响应 | 音频/视频处理、实时通信 |
| **hybrid** | 混合模式节点 | 既有初始化逻辑，又能处理流式数据 | AI Agent（需要初始化+流式对话） |

### 混合工作流示例

```yaml
workflow:
  name: "混合工作流"
  config:
    stream_timeout: 300
  
  nodes:
    # 非流式节点 - 按顺序执行
    - id: "api_call"
      type: "http"  # EXECUTION_MODE = 'sequential'
      config:
        url: "https://api.example.com/data"
    
    # 流式节点 - 数据驱动
    - id: "vad"
      type: "vad_node"  # EXECUTION_MODE = 'streaming'
    
    - id: "asr"
      type: "asr_node"  # EXECUTION_MODE = 'streaming'
    
    - id: "agent"
      type: "agent_node"  # EXECUTION_MODE = 'streaming'
  
  connections:
    # 流式连接 - 实时传递，不影响执行顺序
    - from: "vad.audio_stream"
      to: "asr.audio_in"
    
    - from: "asr.text_stream"
      to: "agent.text_input"
    
    # 支持反馈回路（流式连接允许循环）
    - from: "agent.status"
      to: "vad.control"
```

### 运行混合工作流

```bash
# 运行混合工作流示例
python examples/run_hybrid_simple_example.py
```

### 关键优势

- ✅ **自动分类**: 引擎根据 `EXECUTION_MODE` 自动处理节点
- ✅ **智能排序**: 只对非流式节点进行拓扑排序
- ✅ **反馈回路**: 流式连接支持循环依赖（反馈控制）
- ✅ **实时性**: 流式数据不等待非流式节点完成
- ✅ **资源优化**: 并发执行，充分利用系统资源

详细文档请参阅：[混合执行模式设计文档](docs/HYBRID_EXECUTION_MODE.md)

## ⚙️ 高级特性

### 全局变量

在执行工作流时传入全局变量：

```python
initial_data = {
    'api_key': 'your-api-key',
    'env': 'production'
}
context = engine.execute(initial_data=initial_data)
```

### 代码配置

除了配置文件，也可以通过代码定义工作流：

```python
config = {
    'workflow': {
        'name': '代码定义的工作流',
        'nodes': [
            {'id': 'start', 'type': 'start', 'data': {'value': 100}},
            {'id': 'output', 'type': 'output', 'inputs': ['start']}
        ]
    }
}
engine.load_config_dict(config)
```

### 错误处理

框架提供了完善的错误处理机制：

```python
try:
    context = engine.execute()
except NodeExecutionError as e:
    print(f"节点 {e.node_id} 执行失败: {e}")
except ConfigurationError as e:
    print(f"配置错误: {e}")
except WorkflowException as e:
    print(f"工作流异常: {e}")
```

### 日志系统

查看详细的执行日志：

```python
context = engine.execute()

# 获取所有日志
for log in context.get_logs():
    timestamp = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{log['level']}] {log['message']}")

# 获取所有节点输出
all_outputs = context.get_all_outputs()
for node_id, output in all_outputs.items():
    print(f"节点 {node_id} 的输出: {output}")
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🎯 使用场景

- **数据处理管道**: ETL流程、数据清洗和转换
- **API集成**: 多个API的调用和数据聚合
- **自动化任务**: 定时任务、批量处理
- **业务流程**: 审批流程、状态机
- **数据分析**: 数据采集、分析和报告生成

## 📞 联系方式

如有问题或建议，请提交 Issue 或联系维护者。

---

**Happy Workflow Building! 🎉**
