# 变更历史

本文档记录工作流引擎的重要变更和实现历史。

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

**1. Node 基类扩展** (`workflow_engine/core/node.py`)
- 添加 `EXECUTION_MODE` 类属性
- 支持三种执行模式：`sequential`、`streaming`、`hybrid`

**2. Connection 系统增强** (`workflow_engine/core/connection.py`)
- 添加连接分类功能
- 新增 `_streaming_connections` 和 `_data_connections` 属性
- 实现自动连接分类：根据 `is_streaming` 属性
- 新增 `get_streaming_connections()` 和 `get_data_connections()` 方法

**3. WorkflowEngine 重构** (`workflow_engine/core/workflow.py`)
- 重写 `execute_async()` 方法，实现混合执行模式
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
- 实现 `execute_async()` 方法
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

**1. 参数系统** (`workflow_engine/core/parameter.py`)

- `ParameterSchema`: 参数结构定义和验证
- `StreamChunk`: 流式数据块封装
- `Parameter`: 参数实例管理

**2. 连接系统** (`workflow_engine/core/connection.py`)

- `Connection`: 参数级连接定义
- `ConnectionManager`: 连接管理和数据路由

**3. 节点基类扩展** (`workflow_engine/core/node.py`)

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

**1. 工作流引擎** (`workflow_engine/core/workflow.py`)
- 配置文件解析（YAML/JSON）
- 节点类型注册
- 拓扑排序
- 工作流执行

**2. 节点基类** (`workflow_engine/core/node.py`)
- 节点接口定义
- 状态管理
- 输入输出处理

**3. 执行上下文** (`workflow_engine/core/context.py`)
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

