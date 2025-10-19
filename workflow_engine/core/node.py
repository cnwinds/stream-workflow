"""节点基类定义"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from .context import WorkflowContext
from .exceptions import NodeExecutionError


class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    SUCCESS = "success"      # 执行成功
    FAILED = "failed"        # 执行失败
    SKIPPED = "skipped"      # 已跳过


class Node(ABC):
    """
    节点基类
    所有自定义节点都需要继承此类并实现execute方法
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        """
        初始化节点
        
        Args:
            node_id: 节点唯一标识符
            config: 节点配置字典
        """
        self.node_id = node_id
        self.config = config
        self.status = NodeStatus.PENDING
        self.inputs: List[str] = config.get('inputs', [])
        self.name = config.get('name', node_id)
        self.description = config.get('description', '')
    
    @abstractmethod
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行节点逻辑（抽象方法，子类必须实现）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        pass
    
    def get_input_data(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        从上下文中获取输入数据
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            输入数据字典，key为输入节点ID，value为该节点的输出
        """
        input_data = {}
        for input_node_id in self.inputs:
            output = context.get_node_output(input_node_id)
            input_data[input_node_id] = output
        return input_data
    
    def run(self, context: WorkflowContext) -> Any:
        """
        运行节点（包含状态管理和错误处理）
        
        Args:
            context: 工作流执行上下文
            
        Returns:
            节点执行结果
        """
        try:
            self.status = NodeStatus.RUNNING
            context.log(f"开始执行节点: {self.name} (ID: {self.node_id})")
            
            # 执行前验证
            self.validate(context)
            
            # 执行节点逻辑
            result = self.execute(context)
            
            # 保存输出到上下文
            context.set_node_output(self.node_id, result)
            
            self.status = NodeStatus.SUCCESS
            context.log(f"节点执行成功: {self.name} (ID: {self.node_id})")
            
            return result
            
        except Exception as e:
            self.status = NodeStatus.FAILED
            context.log(f"节点执行失败: {self.name} (ID: {self.node_id}) - {str(e)}", level="ERROR")
            raise NodeExecutionError(self.node_id, str(e), e)
    
    def validate(self, context: WorkflowContext):
        """
        执行前验证（可选，子类可以重写）
        
        Args:
            context: 工作流执行上下文
        """
        # 验证所有输入节点都已执行
        for input_node_id in self.inputs:
            if context.get_node_output(input_node_id) is None:
                raise NodeExecutionError(
                    self.node_id,
                    f"输入节点 '{input_node_id}' 尚未执行或无输出"
                )
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.node_id} status={self.status.value}>"
