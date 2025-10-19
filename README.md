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
- 🌊 **流式处理**: 支持实时音频/视频流、WebSocket 实时通信（新增）
- 🔗 **多端口连接**: 参数级精确连接，自动类型验证（新增）
- ⚡ **异步并发**: 基于 asyncio 的高性能异步执行（新增）

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
# 运行提供的示例
python examples/run_example.py
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

## 🎨 自定义节点

创建自定义节点非常简单，只需继承 `Node` 基类并实现 `execute` 方法：

```python
from workflow_engine.core import Node, WorkflowContext, NodeExecutionError

class MyCustomNode(Node):
    """自定义节点示例"""
    
    def execute(self, context: WorkflowContext):
        """
        执行节点逻辑
        
        可以使用:
        - self.config: 节点配置
        - self.get_input_data(context): 获取输入数据
        - context.log(): 记录日志
        - context.set_global_var(): 设置全局变量
        """
        # 获取配置参数
        param1 = self.config.get('param1')
        param2 = self.config.get('param2', 'default_value')
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        # 执行自定义逻辑
        result = self._do_something(input_data, param1, param2)
        
        # 记录日志
        context.log(f"处理完成: {result}")
        
        # 返回结果
        return result
    
    def _do_something(self, data, param1, param2):
        # 实现你的逻辑
        return {"processed": True}

# 注册自定义节点
engine.register_node_type('my_custom', MyCustomNode)
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
