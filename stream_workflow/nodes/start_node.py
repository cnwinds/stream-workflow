"""起始节点"""

from typing import Any
from stream_workflow.core import Node, ParameterSchema, WorkflowContext, register_node

@register_node('start_node')
class StartNode(Node):
    """
    起始节点
    
    功能：用于工作流的起点，可以提供初始数据
    
    输入参数：
        initial_data: 初始数据（可选，可以从配置文件或输入获取）
            - data: any - 初始数据
            - global_var: string - 全局变量键名
    
    输出参数：
        output: 初始数据
            - data: any - 初始数据
            - source: string - 数据来源（config/global_var/input）
            - global_var: string - 使用的全局变量键名（如果有）
    
    配置参数：
        data: any - 初始数据
        global_var: string - 全局变量键名
    """
    
    # 节点执行模式：顺序执行，任务驱动
    EXECUTION_MODE = 'sequential'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "initial_data": ParameterSchema(
            is_streaming=False,
            schema={
                "data": "any",
                "global_var": "string"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "output": ParameterSchema(
            is_streaming=False,
            schema={
                "data": "any",
                "source": "string",
                "global_var": "any"  # 允许 None
            }
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
        """
        运行起始节点（通用接口）
        
        返回配置中的初始数据或从全局变量获取数据
        """
        return await self.execute(context)
    
    async def execute(self, context: WorkflowContext) -> Any:
        """
        顺序执行起始节点（专门用于顺序执行调用）
        
        返回配置中的初始数据或从全局变量获取数据
        """
        # 1. 从配置文件获取默认值（使用简化的 get_config 方法）
        initial_data = self.get_config('config.data') or self.get_config('data', {})
        global_var_key = self.get_config('config.global_var') or self.get_config('global_var')
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            input_data = self.get_input_value('initial_data')
            if input_data:
                data = input_data.get('data')
                global_var_key = input_data.get('global_var', global_var_key)
                if data is not None:
                    initial_data = data
        except (ValueError, KeyError):
            # 没有输入参数，使用配置文件的值
            pass
        
        # 3. 如果指定了全局变量，则从上下文获取
        source = "config"
        if global_var_key:
            global_data = context.get_global_var(global_var_key, {})
            if global_data:
                initial_data.update(global_data)
                source = "global_var"
        
        # 4. 设置输出值
        self.set_output_value('output', {
            'data': initial_data,
            'source': source,
            'global_var': global_var_key or ""
        })
        
        context.log_info(f"起始节点返回数据: {initial_data}")
        return {
            'data': initial_data,
            'source': source,
            'global_var': global_var_key
        }
