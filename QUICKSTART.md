# 快速入门指南

## 10分钟上手工作流引擎

### 第一步：安装依赖

```bash
pip install -r requirements.txt
```

### 第二步：运行示例

```bash
python3 examples/run_example.py
```

你将看到5个示例的执行结果：
- ✅ 简单数据处理
- ✅ HTTP API调用
- ✅ 条件判断分支
- ✅ 复杂多节点协作
- ✅ 代码定义工作流

### 第三步：创建你的第一个工作流

#### 1. 创建配置文件 `hello_workflow.yaml`

```yaml
workflow:
  name: "Hello World"
  
  nodes:
    - id: "start"
      type: "start"
      data:
        message: "Hello, World!"
    
    - id: "output"
      type: "output"
      inputs: ["start"]
      format: "json"
```

#### 2. 创建执行脚本 `run_hello.py`

```python
from workflow_engine import WorkflowEngine
from workflow_engine.nodes import StartNode, OutputNode

# 创建引擎
engine = WorkflowEngine()

# 注册节点类型
engine.register_node_type('start', StartNode)
engine.register_node_type('output', OutputNode)

# 执行工作流
engine.load_config('hello_workflow.yaml')
engine.execute()
```

#### 3. 运行

```bash
python3 run_hello.py
```

## 常见使用场景

### 场景1: 调用API并处理数据

```yaml
workflow:
  name: "API数据处理"
  nodes:
    - id: "fetch"
      type: "http"
      url: "https://api.example.com/data"
      method: "GET"
    
    - id: "transform"
      type: "transform"
      inputs: ["fetch"]
      operation: "extract"
      config:
        fields: ["name", "value"]
    
    - id: "output"
      type: "output"
      inputs: ["transform"]
```

### 场景2: 条件判断

```yaml
workflow:
  name: "根据分数判断等级"
  nodes:
    - id: "start"
      type: "start"
      data:
        score: 85
    
    - id: "check_grade"
      type: "condition"
      inputs: ["start"]
      conditions:
        - branch: "优秀"
          expression: "score >= 90"
        - branch: "良好"
          expression: "score >= 80"
      default_branch: "及格"
    
    - id: "output"
      type: "output"
      inputs: ["check_grade"]
```

### 场景3: 数据转换

```yaml
workflow:
  name: "数据转换"
  nodes:
    - id: "start"
      type: "start"
      data:
        numbers: [1, 2, 3, 4, 5]
    
    - id: "calculate"
      type: "transform"
      inputs: ["start"]
      operation: "custom"
      config:
        expression: |
          {
            'sum': sum(data['numbers']),
            'avg': sum(data['numbers']) / len(data['numbers'])
          }
    
    - id: "output"
      type: "output"
      inputs: ["calculate"]
```

## 创建自定义节点

### 简单的自定义节点

```python
from workflow_engine.core import Node, WorkflowContext

class GreetingNode(Node):
    """问候节点"""
    
    def execute(self, context: WorkflowContext):
        name = self.config.get('name', 'World')
        greeting = f"Hello, {name}!"
        context.log(f"生成问候语: {greeting}")
        return {'greeting': greeting}

# 使用
engine = WorkflowEngine()
engine.register_node_type('greeting', GreetingNode)
```

配置文件中使用：

```yaml
nodes:
  - id: "greet"
    type: "greeting"
    name: "张三"
```

## 调试技巧

### 1. 查看执行日志

```python
context = engine.execute()

for log in context.get_logs():
    print(f"[{log['level']}] {log['message']}")
```

### 2. 查看节点输出

```python
# 获取特定节点的输出
result = context.get_node_output('node_id')

# 获取所有节点的输出
all_results = context.get_all_outputs()
```

### 3. 查看工作流信息

```python
info = engine.get_workflow_info()
print(f"工作流: {info['name']}")
print(f"节点数量: {info['node_count']}")
```

## 下一步

- 📖 阅读 [README.md](README.md) 了解更多特性
- 🏗️ 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解架构设计
- 💡 查看 [examples/](examples/) 目录的完整示例
- 🔧 尝试创建自己的自定义节点

## 常见问题

### Q: 如何处理错误？

使用 try-except 捕获异常：

```python
try:
    engine.execute()
except NodeExecutionError as e:
    print(f"节点 {e.node_id} 执行失败")
```

### Q: 节点执行顺序如何确定？

引擎自动根据 `inputs` 字段分析依赖关系，使用拓扑排序确定执行顺序。

### Q: 如何在节点间传递复杂数据？

节点的输出会自动保存到上下文，后续节点通过 `inputs` 声明依赖，使用 `get_input_data()` 获取。

### Q: 支持并行执行吗？

当前版本按顺序执行，未来版本将支持无依赖节点的并行执行。

---

开始构建你的工作流吧！ 🚀
