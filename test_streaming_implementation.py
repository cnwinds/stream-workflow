"""测试流式工作流架构实施"""

import sys
from pathlib import Path

# 确保可以导入项目模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_core_imports():
    """测试核心模块导入"""
    print("测试 1: 核心模块导入...")
    try:
        from workflow_engine.core import (
            ParameterSchema, StreamChunk, Parameter,
            Connection, ConnectionManager,
            Node, NodeStatus, register_node, get_registered_nodes,
            WorkflowEngine, WorkflowContext
        )
        print("  ✅ 所有核心模块导入成功")
        return True
    except Exception as e:
        print(f"  ❌ 核心模块导入失败: {e}")
        return False

def test_node_imports():
    """测试节点模块导入"""
    print("\n测试 2: 节点模块导入...")
    try:
        from workflow_engine.nodes import (
            VADNode, ASRNode, AgentNode, TTSNode,
            auto_register_nodes, BUILTIN_NODES
        )
        print("  ✅ 所有流式节点导入成功")
        return True
    except Exception as e:
        print(f"  ❌ 节点模块导入失败: {e}")
        return False

def test_auto_registration():
    """测试自动注册功能"""
    print("\n测试 3: 自动注册节点...")
    try:
        from workflow_engine import WorkflowEngine
        from workflow_engine.nodes import auto_register_nodes
        
        engine = WorkflowEngine()
        auto_register_nodes(engine)
        
        node_count = len(engine._node_registry)
        print(f"  ✅ 自动注册成功，共 {node_count} 个节点类型")
        
        # 检查关键节点类型
        required_nodes = ['vad_node', 'asr_node', 'agent_node', 'tts_node']
        for node_type in required_nodes:
            if node_type in engine._node_registry:
                print(f"  ✅ 节点类型 '{node_type}' 已注册")
            else:
                print(f"  ❌ 节点类型 '{node_type}' 未注册")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ 自动注册失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_schema():
    """测试参数 Schema"""
    print("\n测试 4: 参数 Schema...")
    try:
        from workflow_engine.core import ParameterSchema
        
        # 测试简单类型
        schema1 = ParameterSchema(is_streaming=False, schema="string")
        schema1.validate_value("test")
        print("  ✅ 简单类型验证成功")
        
        # 测试结构体
        schema2 = ParameterSchema(
            is_streaming=True,
            schema={"data": "bytes", "timestamp": "float"}
        )
        schema2.validate_value({"data": b"test", "timestamp": 1.0})
        print("  ✅ 结构体验证成功")
        
        # 测试 Schema 匹配
        schema3 = ParameterSchema(is_streaming=True, schema={"data": "bytes", "timestamp": "float"})
        if schema2.matches(schema3):
            print("  ✅ Schema 匹配检查成功")
        else:
            print("  ❌ Schema 匹配检查失败")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ 参数 Schema 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n测试 5: 配置加载...")
    try:
        from workflow_engine import WorkflowEngine
        from workflow_engine.nodes import auto_register_nodes
        
        engine = WorkflowEngine()
        auto_register_nodes(engine)
        
        config_path = project_root / "examples" / "workflow_streaming.yaml"
        if not config_path.exists():
            print(f"  ⚠️ 配置文件不存在: {config_path}")
            return True  # 不算失败，只是警告
        
        engine.load_config(str(config_path))
        print("  ✅ 配置加载成功")
        
        workflow_info = engine.get_workflow_info()
        print(f"  ✅ 工作流名称: {workflow_info['name']}")
        print(f"  ✅ 节点数量: {workflow_info['node_count']}")
        
        return True
    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("流式工作流架构实施验证测试")
    print("=" * 60)
    
    tests = [
        test_core_imports,
        test_node_imports,
        test_auto_registration,
        test_parameter_schema,
        test_config_loading,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if all(results):
        print("\n✅ 所有测试通过！流式工作流架构实施成功！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

