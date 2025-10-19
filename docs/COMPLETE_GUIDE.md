# 工作流引擎完整指南

## 📖 概述

这是一个类似 n8n 的 Python 工作流引擎框架，支持通过配置文件定义和执行复杂的数据处理流程。

### 🌟 核心特性

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
- 🔍 **上下文参数引用**: 使用 `${node_id.field}` 语法灵活引用节点输出，无需配置连接

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
from workflow_engine.nodes import StartNode, TransformNode, OutputNode

# 创建工作流引擎
engine = WorkflowEngine()

# 注册节点类型
engine.register_node_type('start_node', StartNode)
engine.register_node_type('transform_node', TransformNode)
engine.register_node_type('output_node', OutputNode)

# 加载配置
engine.load_config('my_workflow.yaml')

# 执行工作流
context = await engine.execute_async()
```

## 🔍 上下文参数引用（核心功能）

### 问题解决

对于顺序执行的节点，上一个的输出不一定和下一个的输入的数据格式能对上。通过上下文参数引用，顺序节点无需配置连接，可以直接从上下文获取之前节点的输出内容。

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

### 使用示例

```yaml
workflow:
  name: "参数引用示例"
  nodes:
    # 数据源节点
    - id: "student_data"
      type: "start_node"
      config:
        data:
          name: "张三"
          score: 85
          course: "数学"
    
    # 条件判断节点
    - id: "grade_check"
      type: "condition_node"
      inputs: ["student_data"]
      config:
        conditions:
          - branch: "good"
            expression: "data.get('score', 0) >= 80"
        default_branch: "fail"
    
    # 使用参数引用的节点
    - id: "report"
      type: "transform_node"
      inputs: ["grade_check"]
      config:
        operation: "custom"
        config:
          expression: |
            {
              'student': data.get('data', {}).get('data', {}).get('name', 'Unknown'),
              'score': data.get('data', {}).get('data', {}).get('score', 0),
              'grade': data.get('branch', 'unknown')
            }
```

## 🛠️ 简化的配置获取 API

### 问题解决

之前获取配置参数的方式过于复杂：

```python
# ❌ 复杂且难以理解
actual_config = self.resolved_config.get('config', self.resolved_config) if self.resolved_config else self.config.get('config', self.config)
url = actual_config.get('url')
```

### 新的简化 API

```python
# ✅ 简单且清晰
url = self.get_config('config.url')
method = self.get_config('config.method', 'GET')
timeout = self.get_config('timeout', 30)
```

### API 特性

1. **自动处理配置优先级** - 自动使用 `resolved_config`（包含参数引用解析）
2. **支持嵌套访问** - 使用点号访问嵌套字段
3. **默认值支持** - 提供默认值，避免 None 检查
4. **简洁易用** - 一行代码完成配置获取

### 使用示例

```python
class HttpNode(Node):
    async def execute_async(self, context: WorkflowContext) -> Any:
        # 获取配置参数（简洁清晰）
        url = self.get_config('config.url') or self.get_config('url')
        method = self.get_config('config.method', 'GET')
        timeout = self.get_config('config.timeout', 30)
        headers = self.get_config('config.headers', {})
        
        # 发送 HTTP 请求
        # ...
```

## 🎨 自定义节点开发

### 基本结构

```python
from workflow_engine.core import Node, WorkflowContext, register_node
from typing import Any

@register_node('my_custom')  # 使用装饰器自动注册
class MyCustomNode(Node):
    """自定义节点示例"""
    
    EXECUTION_MODE = 'sequential'  # 或 'streaming' / 'hybrid'
    
    async def execute_async(self, context: WorkflowContext) -> Any:
        """执行节点逻辑"""
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

### 节点执行模式

- **sequential**: 顺序执行，适合数据处理
- **streaming**: 流式执行，适合实时数据流
- **hybrid**: 混合模式，支持两种执行方式

### 配置获取方法

```python
# 基本用法
url = self.get_config('config.url')
method = self.get_config('config.method', 'GET')

# 嵌套访问
db_host = self.get_config('config.database.host')
db_port = self.get_config('config.database.port', 5432)

# 兼容多种配置格式
url = self.get_config('config.url') or self.get_config('url')
```

## 📋 内置节点类型

### StartNode (起始节点)

提供初始数据或从全局变量获取数据。

```yaml
- id: "start"
  type: "start_node"
  config:
    data:
      message: "Hello, Workflow!"
      value: 42
```

### TransformNode (数据转换节点)

支持多种数据转换操作。

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

## 🎯 演示示例

### 1. 自定义节点示例

**文件**: `examples/custom_node_example.py`

**功能**:
- 展示如何创建自定义节点
- 演示简化的 `get_config()` API
- 计算流程：100 + 50 = 150, 150 * 2 = 300

**运行**:
```bash
python examples/custom_node_example.py
```

### 2. 混合流程参数引用示例

**文件**: 
- `examples/workflow_mixed_example.yaml` - 配置文件
- `examples/run_mixed_example.py` - 运行脚本

**功能**:
- 展示参数引用功能
- 演示混合执行模式
- 学生成绩评估流程

**运行**:
```bash
python examples/run_mixed_example.py
```

## 🔧 高级功能

### 混合执行模式

支持同时处理流式和非流式节点：

```yaml
workflow:
  config:
    stream_timeout: 300
    continue_on_error: false
  
  nodes:
    # 顺序节点
    - id: "data_processor"
      type: "transform_node"
      # ...
    
    # 流式节点
    - id: "stream_processor"
      type: "streaming_node"
      # ...
```

### 流式数据处理

```python
class StreamingNode(Node):
    EXECUTION_MODE = 'streaming'
    
    async def on_chunk_received(self, param_name: str, chunk: StreamChunk):
        """处理接收到的流式数据"""
        # 处理流式数据
        pass
    
    async def emit_chunk(self, param_name: str, chunk_data: Any):
        """发送流式数据"""
        # 发送数据到下游节点
        pass
```

### 参数连接系统

对于需要类型安全的场景，可以使用连接系统：

```yaml
workflow:
  connections:
    - from: "source.output"
      to: "target.input"
```

## 📊 性能优化

### 异步执行

所有节点都支持异步执行，可以充分利用 asyncio 的性能优势。

### 流式处理

对于大数据量或实时数据，使用流式处理避免内存问题。

### 混合模式

结合顺序执行和流式处理的优势，实现高效的工作流。

## 🐛 调试和日志

### 执行日志

```python
# 在节点中记录日志
context.log("处理开始")
context.log("处理完成", level="SUCCESS")
context.log("处理失败", level="ERROR")

# 获取所有日志
logs = context.get_logs()
```

### 错误处理

```python
try:
    result = await self.execute_async(context)
except Exception as e:
    context.log(f"节点执行失败: {e}", level="ERROR")
    raise
```

## 📈 最佳实践

### 1. 节点设计

- 保持节点功能单一
- 使用有意义的节点名称
- 提供清晰的配置参数

### 2. 配置管理

- 使用 `get_config()` 方法获取配置
- 提供合理的默认值
- 支持参数引用

### 3. 错误处理

- 记录详细的日志
- 提供有意义的错误信息
- 支持错误恢复

### 4. 性能考虑

- 选择合适的执行模式
- 避免阻塞操作
- 合理使用流式处理

## 🔮 扩展开发

### 创建自定义节点

1. 继承 `Node` 基类
2. 实现 `execute_async` 方法
3. 使用 `@register_node` 装饰器注册
4. 使用 `get_config()` 获取配置

### 添加新的执行模式

1. 在 `Node` 类中定义新的 `EXECUTION_MODE`
2. 在 `WorkflowEngine` 中处理新的执行模式
3. 更新文档和示例

## 📚 总结

工作流引擎提供了强大而灵活的工作流处理能力：

- ✅ **上下文参数引用** - 解决顺序节点数据格式不匹配问题
- ✅ **简化配置API** - 大幅降低开发复杂度
- ✅ **混合执行模式** - 支持多种执行方式
- ✅ **丰富的内置节点** - 满足常见业务需求
- ✅ **完整的文档支持** - 便于学习和使用

通过这个框架，你可以快速构建复杂的数据处理工作流，提高开发效率和代码质量！
