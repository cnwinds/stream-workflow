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

**位置**: `workflow_engine/core/node.py`

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

**位置**: `workflow_engine/core/context.py`

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

**位置**: `workflow_engine/core/workflow.py`

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
from workflow_engine.core import Node, WorkflowContext

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

## 未来规划

### 短期目标

1. ✅ 完成核心框架
2. ✅ 实现基础节点类型
3. ✅ 提供示例和文档
4. ⏳ 添加单元测试
5. ⏳ 性能优化

### 长期目标

1. ⏳ 可视化编辑器
2. ⏳ 节点市场/插件系统
3. ⏳ 分布式执行
4. ⏳ 实时监控和调试
5. ⏳ 版本控制和回滚

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
