# 工作流引擎架构设计文档

## 概述

这是一个类似 n8n 的 Python 工作流引擎框架，采用配置驱动的方式定义和执行数据处理流程。

## 设计理念

### 核心思想

1. **配置驱动**: 通过 YAML/JSON 配置文件定义工作流，降低开发成本
2. **插件化**: 节点类型可扩展，开发者只需实现节点逻辑
3. **数据流**: 节点间自动传递数据，无需手动管理
4. **依赖解析**: 自动分析节点依赖关系，确定执行顺序

### 设计模式

- **策略模式**: 不同节点类型实现不同的执行策略
- **模板方法模式**: Node 基类定义执行流程，子类实现具体逻辑
- **责任链模式**: 数据在节点间流转传递
- **工厂模式**: WorkflowEngine 根据配置创建节点实例

## 架构层次

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
│         上下文层 (Context Layer)                  │
│  - WorkflowContext: 执行上下文                    │
│  - 数据存储、日志记录、状态管理                      │
└─────────────────────────────────────────────────┘
```

## 核心组件

### 1. Node (节点基类)

**位置**: `stream_workflow/core/node.py`

**职责**:
- 定义节点的基本接口和行为
- 管理节点状态（待执行、执行中、成功、失败）
- 提供输入数据获取和输出数据保存的标准流程
- 实现执行前验证逻辑

**关键方法**:
```python
class Node(ABC):
    def __init__(self, node_id, config)  # 初始化节点
    def execute(self, context) -> Any    # 抽象方法，子类必须实现
    def run(self, context) -> Any        # 执行包装（状态管理+错误处理）
    def get_input_data(self, context)    # 获取输入数据
    def validate(self, context)          # 执行前验证
```

**扩展点**:
- 子类必须实现 `execute()` 方法
- 可选重写 `validate()` 方法自定义验证逻辑

### 2. WorkflowContext (执行上下文)

**位置**: `stream_workflow/core/context.py`

**职责**:
- 存储节点输出结果
- 管理全局变量
- 记录执行日志
- 跟踪执行时间

**关键方法**:
```python
class WorkflowContext:
    def set_node_output(node_id, output)    # 保存节点输出
    def get_node_output(node_id)            # 获取节点输出
    def set_global_var(key, value)          # 设置全局变量
    def get_global_var(key)                 # 获取全局变量
    def log(message, level)                 # 记录日志
```

**生命周期**:
- 每次执行工作流时创建新的上下文实例
- 执行完成后保留，可查询日志和结果

### 3. WorkflowEngine (工作流引擎)

**位置**: `stream_workflow/core/workflow.py`

**职责**:
- 注册和管理节点类型
- 解析和验证配置文件
- 构建节点实例
- 计算执行顺序（拓扑排序）
- 控制工作流执行

**关键方法**:
```python
class WorkflowEngine:
    def register_node_type(type, class)     # 注册节点类型
    def load_config(config_path)            # 从文件加载配置
    def load_config_dict(config)            # 从字典加载配置
    def execute(initial_data)               # 执行工作流
    def _get_execution_order()              # 计算执行顺序（拓扑排序）
```

**执行流程**:
1. 加载配置 → 2. 验证配置 → 3. 构建节点 → 4. 拓扑排序 → 5. 顺序执行

### 4. 内置节点

#### StartNode (起始节点)
- 提供工作流初始数据
- 可从配置或全局变量获取数据

#### HttpNode (HTTP请求节点)
- 支持 GET、POST、PUT、DELETE 等方法
- 支持请求头、参数、请求体
- 自动解析 JSON 响应

#### TransformNode (数据转换节点)
- **extract**: 提取指定字段
- **map**: 映射/重命名字段
- **filter**: 过滤数据
- **aggregate**: 聚合操作（sum、avg、max、min）
- **custom**: 自定义 Python 表达式

#### ConditionNode (条件判断节点)
- 支持多条件判断
- 支持 Python 表达式
- 返回分支信息和数据

#### MergeNode (合并节点)
- **merge**: 合并字典
- **concat**: 连接列表
- **first**: 取第一个输入
- **last**: 取最后一个输入

#### OutputNode (输出节点)
- 支持多种格式（JSON、文本、原始）
- 可选保存到文件
- 打印执行结果

## 配置文件格式

### YAML 配置结构

```yaml
workflow:
  name: "工作流名称"           # 必需
  description: "工作流描述"    # 可选
  version: "1.0.0"            # 可选
  
  nodes:                      # 必需
    - id: "node_id"           # 必需，节点唯一ID
      type: "node_type"       # 必需，节点类型
      name: "节点名称"         # 可选
      description: "描述"      # 可选
      inputs:                 # 可选，输入节点ID列表
        - "input_node_id"
      # ... 节点特定配置 ...
```

### 配置验证规则

1. **必需字段验证**:
   - `workflow.name`
   - `workflow.nodes`
   - `nodes[].id`
   - `nodes[].type`

2. **唯一性验证**:
   - 节点 ID 必须唯一

3. **引用验证**:
   - 输入节点必须存在
   - 不能存在循环依赖

4. **类型验证**:
   - 节点类型必须已注册

## 执行机制

### 拓扑排序算法

使用 Kahn 算法计算节点执行顺序：

```python
1. 计算每个节点的入度（依赖节点数量）
2. 将入度为 0 的节点加入队列
3. 从队列中取出节点，加入执行顺序
4. 将该节点的所有后继节点入度减 1
5. 如果后继节点入度变为 0，加入队列
6. 重复步骤 3-5，直到队列为空
7. 如果还有节点未处理，说明存在循环依赖
```

### 数据流转

```
Node A (输出) → Context (存储) → Node B (读取)
                   ↓
              get_node_output(A)
```

节点输出自动保存到上下文，后续节点通过 `get_input_data()` 获取。

### 错误处理

```
执行节点
  ↓
try:
  validate() → execute() → save_output()
  ↓
  SUCCESS
catch Exception:
  ↓
  记录日志 → 设置状态为 FAILED → 抛出 NodeExecutionError
```

## 扩展指南

### 创建自定义节点

```python
from stream_workflow.core import Node, WorkflowContext

class MyNode(Node):
    def execute(self, context: WorkflowContext):
        # 1. 获取配置
        param = self.config.get('param')
        
        # 2. 获取输入
        input_data = self.get_input_data(context)
        
        # 3. 执行逻辑
        result = self._process(input_data, param)
        
        # 4. 返回结果（自动保存到上下文）
        return result
```

### 注册和使用

```python
# 注册
engine.register_node_type('my_node', MyNode)

# 配置文件中使用
nodes:
  - id: "step1"
    type: "my_node"
    param: "value"
```

## 性能优化

### 已实现的优化

1. **懒加载**: 节点实例按需创建
2. **一次性计算**: 拓扑排序只计算一次
3. **直接引用**: 使用字典存储节点，O(1) 查找

### 未来优化方向

1. **并行执行**: 无依赖关系的节点可并行执行
2. **缓存机制**: 缓存节点输出，支持重试
3. **流式处理**: 支持大数据流式处理
4. **断点续传**: 支持工作流中断后继续执行

## 安全性考虑

### 表达式执行安全

TransformNode 和 ConditionNode 使用 `eval()` 执行自定义表达式，已实现以下安全措施：

1. **限制内置函数**: 只允许安全的内置函数
2. **隔离环境**: 使用受限的全局命名空间
3. **禁止导入**: 不允许 `import` 语句

### 建议

- 生产环境应考虑使用更安全的表达式引擎
- 或完全禁用自定义表达式，只使用预定义操作

## 测试策略

### 单元测试

- 每个节点类型独立测试
- 上下文管理测试
- 配置解析测试

### 集成测试

- 完整工作流执行测试
- 多节点协作测试
- 错误处理测试

### 性能测试

- 大规模节点图执行
- 内存使用监控
- 执行时间分析

## 流式多端口架构（新增）

### 设计理念

为支持实时音频/视频处理和 WebSocket 实时通信等场景，引擎已扩展支持流式多端口架构：

1. **多端口输入输出**：每个节点可定义多个命名参数
2. **参数级连接**：连接基于参数而非节点，精确控制数据流向
3. **流式数据处理**：支持数据以 chunk 形式增量传输
4. **异步并行执行**：基于 asyncio 的并发执行模型
5. **参数结构验证**：引擎自动验证连接两端参数结构完全匹配

### 核心组件扩展

#### 1. 参数系统 (Parameter System)

**文件**: `stream_workflow/core/parameter.py`

提供参数定义、Schema 和验证功能：

```python
class ParameterSchema:
    - is_streaming: bool - 是否流式参数
    - schema: Union[str, dict] - 参数结构（简单类型或字典）
    - validate_value() - 验证数据是否符合 schema
    - matches() - 判断两个 schema 是否完全一致

class StreamChunk:
    - data: 数据内容（通常是字典）
    - schema: ParameterSchema
    - timestamp: 时间戳
    - 构造时自动验证数据

class Parameter:
    - name: 参数名称
    - schema: ParameterSchema
    - value: 非流式数据存储
    - stream_queue: asyncio.Queue（流式数据队列）
```

**支持的类型**：
- 简单类型：`string`, `integer`, `float`, `boolean`, `bytes`, `dict`, `list`, `any`
- 结构体：`{"field1": "string", "field2": "integer", ...}`

#### 2. 连接系统 (Connection System)

**文件**: `stream_workflow/core/connection.py`

管理参数间的连接和数据路由：

```python
class Connection:
    - source: (node_id, param_name) - 源参数
    - target: (node_id, param_name) - 目标参数
    - source_schema, target_schema - 参数 Schema
    - is_streaming: bool - 是否流式连接
    - _validate() - 验证两端参数结构完全匹配

class ConnectionManager:
    - add_connection() - 添加连接
    - route_chunk() - 路由 chunk 到所有目标（支持一对多广播）
    - transfer_value() - 传输非流式数据
```

**连接验证**：
- 引擎在构建连接时自动验证源和目标参数的 schema 是否完全匹配
- 不匹配时抛出详细的错误信息，包括双方的 schema 定义

#### 3. 节点基类扩展

**文件**: `stream_workflow/core/node.py`

节点基类增加多端口和异步支持：

```python
class Node:
    # 类属性：子类定义参数结构
    INPUT_PARAMS: Dict[str, ParameterSchema] = {}
    OUTPUT_PARAMS: Dict[str, ParameterSchema] = {}
    
    # 实例属性：运行时参数实例
    inputs: Dict[str, Parameter]
    outputs: Dict[str, Parameter]
    
    # 异步执行方法
    async def run(context) - 节点运行入口（必须实现）
    async def execute(context) - 顺序执行接口（可选实现）
    
    # 流式数据处理
    async def emit_chunk(param_name, chunk_data) - 发送流式 chunk
    async def consume_stream(param_name) - 消费流式输入
    async def on_chunk_received(param_name, chunk) - 处理接收到的 chunk
    
    # 非流式数据访问
    def set_output_value(param_name, value) - 设置非流式输出
    def get_input_value(param_name) - 获取非流式输入
```

**向后兼容**：
- 保留旧的 `execute()` 和 `run()` 方法
- 旧节点可以无缝运行在新引擎上

#### 4. 工作流引擎扩展

**文件**: `stream_workflow/core/workflow.py`

引擎增加连接管理和异步执行：

```python
class WorkflowEngine:
    _connection_manager: ConnectionManager
    
    # 构建连接并验证
    def _build_connections():
        - 解析配置中的 connections 列表
        - 创建 Connection 对象（自动验证参数匹配）
        - 关联流式连接的队列
    
    # 启动和执行工作流
    async def start(initial_data):
        - 准备执行环境
        - 启动流式任务到后台
        
    async def execute(**kwargs):
        - 执行所有顺序节点（按配置顺序）
        - 等待任务完成或超时
```

### 配置文件格式扩展

#### 节点定义

节点配置不再需要定义参数结构（参数在代码中定义）：

```yaml
nodes:
  - id: "vad"
    type: "vad_node"
    config:
      threshold: 0.5
```

#### 连接定义

使用 `node_id.param_name` 格式定义参数级连接：

```yaml
connections:
  - from: "vad.audio_stream"
    to: "asr.audio_in"
  - from: "asr.text_stream"
    to: "agent.text_input"
```

引擎会自动：
1. 检查节点和参数是否存在
2. 验证两端参数 schema 是否完全匹配
3. 建立连接并关联队列

### 流式节点开发模式

#### 参数定义

在节点类中使用类属性定义参数：

```python
class VADNode(Node):
    INPUT_PARAMS = {
        "raw_audio": ParameterSchema(
            is_streaming=True,
            schema={
                "audio_data": "bytes",
                "audio_type": "string",
                "sample_rate": "integer"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "audio_stream": ParameterSchema(
            is_streaming=True,
            schema={
                "audio_data": "bytes",
                "audio_type": "string",
                "sample_rate": "integer",
                "timestamp": "float"
            }
        )
    }
```

#### 执行逻辑

流式节点通常持续运行，通过回调处理数据：

```python
async def run(self, context):
    """初始化（持续运行）"""
    context.log(f"VAD 节点启动")
    try:
        await asyncio.sleep(float('inf'))
    except asyncio.CancelledError:
        context.log(f"VAD 节点关闭")

async def on_chunk_received(self, param_name, chunk):
    """处理输入 chunk"""
    if param_name == "raw_audio":
        audio_data = chunk.data["audio_data"]
        # 处理音频
        if self._is_speech(audio_data):
            # 发送输出 chunk
            await self.emit_chunk("audio_stream", {
                "audio_data": audio_data,
                "audio_type": chunk.data["audio_type"],
                "sample_rate": chunk.data["sample_rate"],
                "timestamp": time.time()
            })
```

### 节点注册机制

支持三种注册方式：

#### 1. 手动注册
```python
engine.register_node_type('my_node', MyNode)
```

#### 2. 自动注册
```python
from stream_workflow.nodes import auto_register_nodes
auto_register_nodes(engine)
```

#### 3. 装饰器注册
```python
@register_node('my_node')
class MyNode(Node):
    pass
```

### 示例：语音对话流程

完整的流式工作流示例（`examples/workflow_streaming.yaml`）：

```
语音输入 -> VAD -> ASR -> Agent -> TTS -> 语音输出
           (流)   (流)   (流)   (流)
```

每个箭头代表一个参数级连接，数据以 chunk 形式流式传输。

### 关键设计要点

1. **参数在代码中定义**：确保类型安全，便于IDE提示和重构
2. **配置专注编排**：YAML 只定义节点实例和连接关系
3. **自动类型验证**：连接构建时验证参数结构，早期发现错误
4. **向后兼容**：旧节点可以继续使用，渐进式迁移
5. **异步并发**：充分利用 asyncio，提高执行效率

### 性能优化

#### 已实现

1. **异步并发执行**：无依赖节点可并行运行
2. **流式传输**：减少内存占用，降低延迟
3. **队列路由**：高效的 chunk 分发机制

#### 未来优化

1. **背压控制**：防止生产者过快导致队列堆积
2. **动态批处理**：自动合并小 chunk 提高吞吐量
3. **连接池**：复用网络连接减少开销
4. **分布式执行**：跨机器分布节点执行

## 未来规划

### 短期目标

1. ✅ 完成核心框架
2. ✅ 实现基础节点类型
3. ✅ 提供示例和文档
4. ✅ 流式多端口架构
5. ✅ 异步并行执行
6. ⏳ 添加单元测试
7. ⏳ 性能优化和监控

### 长期目标

1. ⏳ 可视化编辑器（支持参数级连接）
2. ⏳ 节点市场/插件系统
3. ⏳ 分布式执行（跨机器流式传输）
4. ⏳ 实时监控和调试（流式数据可视化）
5. ⏳ 版本控制和回滚
6. ⏳ 背压控制和流量管理

## 相关资源

- **n8n**: https://n8n.io/
- **Apache Airflow**: https://airflow.apache.org/
- **Prefect**: https://www.prefect.io/

## 贡献者指南

1. Fork 项目
2. 创建特性分支
3. 实现功能并添加测试
4. 提交 Pull Request
5. 等待代码审查

---

**文档版本**: 1.0.0  
**最后更新**: 2025-10-19
