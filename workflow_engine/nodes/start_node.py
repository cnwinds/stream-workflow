"""起始节点"""

from typing import Any
from workflow_engine.core import Node, WorkflowContext


class StartNode(Node):
    """
    起始节点
    用于工作流的起点，可以提供初始数据
    """
    
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行起始节点
        
        返回配置中的初始数据或从全局变量获取数据
        """
        # 从配置中获取初始数据
        initial_data = self.config.get('data', {})
        
        # 如果配置中指定了全局变量，则从上下文获取
        global_var_key = self.config.get('global_var')
        if global_var_key:
            global_data = context.get_global_var(global_var_key, {})
            initial_data.update(global_data)
        
        context.log(f"起始节点返回数据: {initial_data}")
        return initial_data
