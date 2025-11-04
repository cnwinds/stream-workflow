"""
设置全局变量
"""
from stream_workflow.core import Node, ParameterSchema, register_node, WorkflowContext

@register_node('variable_node')
class VariableNode(Node):
    """将节点配置的内容设置到全局变量中"""
    
    EXECUTION_MODE = 'sequential'
    
    # 输入参数定义
    INPUT_PARAMS = {

    }
    
    # 输出参数定义
    OUTPUT_PARAMS = {

    }
    
    # 配置Schema
    CONFIG_SCHEMA = {}
    
    async def initialize(self, context: WorkflowContext):
        """初始化节点 - 将config中的所有配置设置到全局变量中"""
        # 收集所有需要设置到全局变量的配置项
        config_dict = {}
        
        # 首先尝试从config子字典获取配置（通常节点配置在config字段下）
        config_subdict = self.get_config('config')
        if isinstance(config_subdict, dict):
            config_dict.update(config_subdict)
        
        # 遍历配置中的所有键值对，设置到全局变量
        for key, value in config_dict.items():
            context.set_global_var(key, value)
            context.log_info(f"设置全局变量: {key} = {value}")

    async def run(self, context):
        """节点执行逻辑"""

        # 返回输出
        return {}