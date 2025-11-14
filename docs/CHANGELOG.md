# 变更历史

本文档记录工作流引擎的重要变更和实现历史。

---

## 版本 1.0.9 (2025-01-XX)

### 🆕 新增功能

**Jinja2 模板递归解析**：
- `render_template()` 方法现在支持递归解析变量
- 如果渲染后的结果仍然包含 Jinja2 语法，会自动继续解析
- 最多递归 10 次，防止无限循环
- 智能检测渲染结果是否变化，无变化时自动停止

### 🐛 问题修复

**流式队列安全检查**：
- 在 `feed_input_chunk()` 和 `close_input_stream()` 方法中添加了 `stream_queue` 的 None 检查
- 如果队列未初始化，会抛出清晰的错误信息，而不是 `AttributeError`
- 提高了错误信息的可读性和问题定位能力

### 📝 使用示例

```python
# 递归解析示例
context.set_global_var('base_url', '{{ api.host }}/v1')
context.set_global_var('api.host', 'https://api.example.com')
result = engine.render_template("{{ base_url }}")
# 会自动递归解析，直到所有变量都被替换

# 流式队列安全检查
# 如果队列未初始化，会抛出清晰的错误：
# ValueError: 流式参数 {param_name} 的队列未初始化。请确保节点已调用 initialize() 方法
```

### 🔧 技术改进

- `render_template()` 方法增加了递归解析逻辑
- 添加了最大迭代次数限制（10次）防止无限循环
- 改进了错误处理，提供更清晰的错误信息

---

## 版本 1.0.8 (2025-01-XX)

### 🆕 新增功能

**全局变量点号分隔支持**：
- `set_global_var()` 和 `get_global_var()` 方法现在支持点号分隔的键名
- 支持嵌套字典的自动创建和访问（如 `user.config`、`user.memory`）
- 自动处理嵌套字典结构，无需手动创建中间字典

### 📝 使用示例

```python
# 设置嵌套全局变量
context.set_global_var('user.config', {'theme': 'dark'})
context.set_global_var('user.memory', 1024)

# 获取嵌套全局变量
config = context.get_global_var('user.config')  # 返回 {'theme': 'dark'}
memory = context.get_global_var('user.memory', 0)  # 返回 1024

# 在 Jinja2 模板中使用
# {{ user.config.theme }}  # 输出: dark
# {{ user.memory }}  # 输出: 1024
```

### 🔧 技术改进

- `set_global_var()` 方法自动创建嵌套字典结构
- `get_global_var()` 方法安全地遍历嵌套字典，支持默认值
- 如果中间路径已存在但不是字典，会自动覆盖为字典

---

## 版本 1.0.7 (2025-01-XX)

### 🆕 新增功能

**Jinja2 模板引擎集成**：
- 完全集成 Jinja2 模板引擎，替换原有的 `${}` 语法
- 在 `WorkflowEngine` 中提供 `render_template()` 公共接口，支持模板渲染
- 在 `start()` 方法中自动初始化 Jinja2 环境并注入全局变量
- 支持嵌套字典的点号访问（如 `{{ user.profile.user_name }}`）
- 在节点配置解析中自动支持 Jinja2 语法

**节点输出访问**：
- 通过 `nodes['node_id']` 访问节点输出
- 支持 `{{ nodes['node_id'].field }}` 语法访问嵌套字段
- 提供 `get_node_output()` 辅助函数作为备选访问方式

**全局变量增强**：
- 全局变量直接注入到 Jinja2 环境，可直接使用变量名访问
- 支持嵌套字典的全局变量，自动创建访问器支持点号访问
- 在 `start()` 时通过 `initial_data` 参数注入初始全局变量

### 🔧 架构改进

**节点初始化优化**：
- `Node.__init__()` 现在接收 `engine` 参数而不是 `connection_manager`
- 节点通过 `self.engine` 访问引擎实例
- 节点通过 `self.engine.get_connection_manager()` 获取连接管理器
- 所有节点方法统一使用 `self.engine`，不再从 context 获取

**代码清理**：
- 完全移除 `${}` 语法解析逻辑
- 移除 `_get_reference_value()` 方法
- 简化节点配置解析流程

### 📝 使用示例

```python
# 启动工作流时注入全局变量
context = await engine.start(initial_data={
    'user': {
        'profile': {
            'user_name': 'kity',
            'age': 25
        }
    },
    'base_url': 'https://api.example.com'
})

# 使用模板渲染接口
result = engine.render_template("用户: {{ user.profile.user_name }}")
# 结果: "用户: kity"

# 在节点配置中使用 Jinja2
config = {
    "url": "{{ base_url }}/api/users",
    "name": "{{ nodes['start'].data.name }}"
}
```

### 📦 依赖更新

- 新增 `Jinja2>=3.1.0` 依赖

---

## 版本 1.0.3 (2025-01-XX)

### 🆕 新增功能

**连接查询工具**：
- 新增 `ConnectionManager.get_connected_nodes()` 方法
  - 支持通过节点ID和参数名查询连接的节点和参数
  - 支持查询输出参数连接到的目标节点（`is_output=True`）
  - 支持查询输入参数连接的源节点（`is_output=False`）
  - 支持外部连接的识别和查询
  - 返回连接的详细信息，包括流式连接标识

**技术改进**：
- 添加目标索引 `_target_index` 到 `ConnectionManager`，优化反向查询性能
- 改进 `_add_connection()` 方法，自动建立目标索引

**使用示例**：
```python
# 查询输出参数的连接
connections = manager.get_connected_nodes("node_a", "output", is_output=True)
# 返回: [{"target_node": "node_b", "target_param": "input", "is_streaming": False, ...}, ...]

# 查询输入参数的连接
connections = manager.get_connected_nodes("node_b", "input", is_output=False)
# 返回: [{"source_node": "node_a", "source_param": "output", "is_streaming": False, ...}, ...]
```

---

## 版本 1.0.2 (2025-01-XX)

### 🔧 代码清理和优化

**变更内容**：
- 删除不再使用的内置节点：`output_node`, `transform_node`, `merge_node`, `start_node`, `condition_node`
- 精简内置节点列表，现在仅包含：`http`, `variable`
- 修复包安装配置，确保从 Git 安装时正确包含所有文件
- 优化 `pyproject.toml` 配置，使用自动包发现机制
- 实现内置节点默认自动加载功能
- 新增 `VariableNode`，用于在工作流启动时设置全局变量

**技术改进**：
- 改进 `WorkflowEngine` 初始化，支持自动加载内置节点
- 修复 `condition_node` 对 transform 节点输出的处理逻辑
- 修复 `output_node` 的 `file_path` 字段类型验证问题

**API变更**：
- `WorkflowEngine.__init__()` 新增 `auto_load_builtin_nodes` 参数（默认为 `True`）

**破坏性变更**：
- 移除了以下内置节点：`output`, `transform`, `merge`, `start`, `condition`
- 用户需要自定义这些节点或使用其他替代方案

---

## 版本 2.0.0 (2025-10-20)

### 📚 文档整合

**目标**：简化文档结构，提升可读性

**变更**：
- 将10个文档整合为4个核心文档
- 新增 `USER_GUIDE.md` - 完整用户指南
- 新增 `DEVELOPER_GUIDE.md` - 开发者指南
- 新增 `CHANGELOG.md` - 本文档
- 保留 `ARCHITECTURE.md` - 架构设计文档

**删除的文档**：
- `NODE_REFACTORING_SUMMARY.md` → 内容合并到 CHANGELOG
- `IMPLEMENTATION_SUMMARY.md` → 内容合并到 CHANGELOG
- `CONDITION_NODE_REFACTORING.md` → 内容合并到 CHANGELOG
- `STREAMING_WORKFLOW_GUIDE.md` → 内容合并到 USER_GUIDE
- `DATA_INPUT_GUIDE.md` → 内容合并到 USER_GUIDE
- `HYBRID_EXECUTION_MODE.md` → 内容合并到 DEVELOPER_GUIDE
- `COMPLETE_GUIDE.md` → 内容合并到 USER_GUIDE
- `NODE_DEVELOPMENT_GUIDE.md` → 内容合并到 DEVELOPER_GUIDE
- `ASYNC_NON_STREAMING_NODES.md` → 内容合并到 DEVELOPER_GUIDE

---

## 版本 1.3.0 (2025-10-19)

### 🔀 混合执行模式实现

**实现日期**: 2025年10月19日

#### ✅ 核心架构修改

**1. Node 基类扩展** (`stream_workflow/core/node.py`)
- 添加 `EXECUTION_MODE` 类属性
- 支持三种执行模式：`sequential`、`streaming`、`hybrid`

**2. Connection 系统增强** (`stream_workflow/core/connection.py`)
- 添加连接分类功能
- 新增 `_streaming_connections` 和 `_data_connections` 属性
- 实现自动连接分类：根据 `is_streaming` 属性
- 新增 `get_streaming_connections()` 和 `get_data_connections()` 方法

**3. WorkflowEngine 重构** (`stream_workflow/core/workflow.py`)
- 重写工作流执行方法，实现混合执行模式
  - 分类节点：sequential/hybrid vs streaming
  - 启动所有流式消费任务（后台运行）
  - 对 sequential/hybrid 节点按拓扑顺序执行
  - 等待流式任务完成（或超时）
- 优化 `_get_execution_order()` 方法
  - 只使用非流式连接构建依赖图
  - 支持指定节点列表进行排序
- 支持工作流配置参数：
  - `stream_timeout`: 流式任务超时时间
  - `continue_on_error`: 错误时是否继续执行

#### ✅ 节点执行模式定义

| 节点 | 执行模式 | 说明 |
|------|----------|------|
| `VADNode` | `streaming` | 纯流式节点，音频活动检测 |
| `ASRNode` | `streaming` | 纯流式节点，语音识别 |
| `AgentNode` | `streaming` | 流式节点，智能对话 |
| `TTSNode` | `streaming` | 流式节点，文本转语音 |
| `HttpNode` | `sequential` | 顺序节点，HTTP请求 |
| `StartNode` | `sequential` | 顺序节点，工作流起点 |
| `TransformNode` | `sequential` | 顺序节点，数据转换 |
| `OutputNode` | `sequential` | 顺序节点，结果输出 |

#### ✅ 核心设计理念

**1. 执行模式分类**

| 特性 | sequential | streaming | hybrid |
|------|-----------|-----------|--------|
| **执行方式** | 任务驱动，按顺序执行 | 数据驱动，被动响应 | 初始化+流式处理 |
| **参与拓扑排序** | ✅ 是 | ❌ 否 | ✅ 是 |
| **支持流式输入** | ❌ 否 | ✅ 是 | ✅ 是 |
| **执行完毕后** | 立即返回 | 保持运行 | 保持运行 |

**2. 连接分类**

```python
# 流式连接：不影响执行顺序，实时传递数据
_streaming_connections = []  # is_streaming == True

# 非流式连接：决定执行顺序，通过拓扑排序
_data_connections = []       # is_streaming == False
```

**3. 执行流程**

```
启动工作流
    ↓
分类节点
    ├── Sequential/Hybrid 节点 → 拓扑排序
    └── Streaming 节点 → 不参与排序
    ↓
启动所有流式消费任务（后台异步运行）
    ↓
按拓扑顺序执行 Sequential/Hybrid 节点
    ├── Sequential: 执行完返回
    └── Hybrid: 初始化后保持运行
    ↓
等待流式任务完成（或超时）
    ↓
返回结果
```

#### ✅ 技术亮点

**1. Kahn 拓扑排序算法**

只使用非流式连接构建依赖图，避免流式连接的循环依赖问题。

**2. 异步并发执行**

使用 `asyncio.create_task()` 和 `asyncio.gather()` 实现高效并发。

**3. 自动连接分类**

根据参数 schema 自动判断连接类型。

#### ✅ 示例文件

- `examples/workflow_hybrid.yaml` - 完整的混合工作流配置示例
- `examples/workflow_hybrid_simple.yaml` - 简化的混合工作流示例
- `examples/run_hybrid_example.py` - 混合工作流运行脚本（完整版）
- `examples/run_hybrid_simple_example.py` - 混合工作流运行脚本（简化版）

---

## 版本 1.2.0 (2025-10-19)

### 🔧 节点重构

**重构日期**: 2025年10月19日

#### ✅ 已完成的节点重构

按照 `http_node.py` 的新格式，成功重构了以下节点：

**1. TransformNode** (`transform_node.py`)

重构内容：
- 添加 `@register_node('transform_node')` 装饰器
- 定义 `INPUT_PARAMS` 和 `OUTPUT_PARAMS`
- 实现 `run()` 方法
- 支持新格式的参数连接

**2. MergeNode** (`merge_node.py`)

重构内容：
- 添加 `@register_node('merge_node')` 装饰器
- 定义完整的参数结构
- 支持多种合并策略
- 返回详细的合并信息

**3. OutputNode** (`output_node.py`)

重构内容：
- 添加 `@register_node('output_node')` 装饰器
- 支持多种输出格式
- 返回详细的输出信息
- 增强错误处理

**4. StartNode** (`start_node.py`)

重构内容：
- 添加 `@register_node('start_node')` 装饰器
- 支持全局变量
- 返回数据来源信息

**5. ConditionNode** (`condition_node.py`)

重构内容：
- 添加 `@register_node('condition_node')` 装饰器
- 改进条件评估逻辑
- 增强输出信息
- 修复参数验证问题

#### ✅ 标准重构模式

```python
@register_node('node_type')
class NodeClass(Node):
    """节点描述"""
    
    EXECUTION_MODE = 'sequential'  # 或 'streaming' 或 'hybrid'
    
    INPUT_PARAMS = {
        "param_name": ParameterSchema(
            is_streaming=False,
            schema={
                "field1": "type",
                "field2": "type"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "output_name": ParameterSchema(
            is_streaming=False,
            schema={
                "field1": "type",
                "field2": "type"
            }
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
        # 1. 从配置获取参数
        # 2. 从输入获取数据
        # 3. 执行核心逻辑
        # 4. 设置输出值
        pass
```

#### ✅ 关键改进

**1. 参数结构标准化**

所有节点都定义了明确的输入输出参数结构。

**2. 配置优先级**

实现了配置优先级机制：**输入参数** > **配置文件** > **默认值**

**3. 输出信息丰富化**

所有节点都返回更详细的输出信息。

**4. 错误处理增强**

改进了错误处理机制，提供更清晰的错误信息。

---

## 版本 1.1.0 (2025-10-18)

### 🌊 流式多端口架构

#### ✅ 核心功能

**1. 参数系统** (`stream_workflow/core/parameter.py`)

- `ParameterSchema`: 参数结构定义和验证
- `StreamChunk`: 流式数据块封装
- `Parameter`: 参数实例管理

**2. 连接系统** (`stream_workflow/core/connection.py`)

- `Connection`: 参数级连接定义
- `ConnectionManager`: 连接管理和数据路由

**3. 节点基类扩展** (`stream_workflow/core/node.py`)

- 多端口输入输出支持
- 流式数据处理方法
- 异步执行支持

**4. 流式节点实现**

- `VADNode`: 语音活动检测
- `ASRNode`: 语音识别
- `AgentNode`: 对话代理
- `TTSNode`: 文本转语音

#### ✅ 配置格式扩展

新增参数级连接定义：

```yaml
connections:
  - from: "node1.output_param"
    to: "node2.input_param"
```

#### ✅ 数据输入API

- `feed_input_chunk()`: 发送流式数据
- `close_input_stream()`: 关闭流式输入
- `set_input_value()`: 设置非流式输入
- `get_input_value()`: 获取非流式输入

---

## 版本 1.0.0 (2025-10-15)

### 🎉 初始版本

#### ✅ 核心功能

**1. 工作流引擎** (`stream_workflow/core/workflow.py`)
- 配置文件解析（YAML/JSON）
- 节点类型注册
- 拓扑排序
- 工作流执行

**2. 节点基类** (`stream_workflow/core/node.py`)
- 节点接口定义
- 状态管理
- 输入输出处理

**3. 执行上下文** (`stream_workflow/core/context.py`)
- 节点输出存储
- 全局变量管理
- 日志记录

**4. 内置节点**
- `StartNode`: 起始节点
- `HttpNode`: HTTP请求
- `TransformNode`: 数据转换
- `ConditionNode`: 条件判断
- `MergeNode`: 数据合并
- `OutputNode`: 结果输出

#### ✅ 核心特性

- 📝 配置驱动
- 🔌 插件化节点
- 🔄 自动依赖解析
- 📊 数据流转
- 🎯 条件分支
- 🔍 执行日志

---

## 技术债务

### 已知问题

1. **数据传递问题**（v1.2.0）
   - 在旧架构下，数据传递存在问题
   - 需要进一步调试数据传递机制

2. **参数结构匹配**（v1.2.0）
   - 新格式的参数连接需要完全匹配的 schema
   - 需要设计更灵活的匹配机制

### 未来优化方向

#### 1. 监控和可视化
- [ ] 节点执行状态监控
- [ ] 实时数据流动可视化
- [ ] 性能指标收集和展示

#### 2. 错误处理增强
- [ ] 流式节点的错误重试机制
- [ ] 部分节点失败时的降级策略
- [ ] 更详细的错误诊断信息

#### 3. 性能优化
- [ ] 流式数据的批处理优化
- [ ] 节点间的背压控制
- [ ] 内存使用优化

#### 4. 开发工具
- [ ] 节点执行模式的可视化工具
- [ ] 配置文件的验证和提示
- [ ] 单元测试框架

#### 5. 长期目标
- [ ] 可视化编辑器（支持参数级连接）
- [ ] 节点市场/插件系统
- [ ] 分布式执行（跨机器流式传输）
- [ ] 实时监控和调试（流式数据可视化）
- [ ] 版本控制和回滚
- [ ] 背压控制和流量管理

---

## 贡献者

- AI Assistant - 主要开发者

---

**文档版本**: 2.0.0  
**最后更新**: 2025-10-20

