"""连接系统：参数连接和数据传输"""

import asyncio
from typing import List, Dict, Tuple, Optional, Callable, Any
from .parameter import ParameterSchema, StreamChunk
from .exceptions import ConfigurationError


class Connection:
    """参数连接定义"""
    
    def __init__(self, source_node: str, source_param: str,
                 target_node: str, target_param: str,
                 source_schema: ParameterSchema, target_schema: ParameterSchema):
        """
        初始化连接
        
        Args:
            source_node: 源节点 ID
            source_param: 源参数名称
            target_node: 目标节点 ID
            target_param: 目标参数名称
            source_schema: 源参数 Schema
            target_schema: 目标参数 Schema
            
        Raises:
            ConfigurationError: 参数结构不匹配
        """
        self.source = (source_node, source_param)
        self.target = (target_node, target_param)
        self.source_schema = source_schema
        self.target_schema = target_schema
        self.is_streaming = source_schema.is_streaming
        self.target_queue = None  # 目标参数的队列（流式连接时设置）
        self.is_external = False  # 是否为外部连接
        self.external_handler = None  # 外部处理函数
        
        # 验证类型匹配
        self._validate()
    
    def _validate(self):
        """
        验证连接的两端参数结构完全一致
        
        Raises:
            ConfigurationError: 参数结构不匹配
        """
        if not self.source_schema.matches(self.target_schema):
            raise ConfigurationError(
                f"连接参数不匹配:\n"
                f"  源: {self.source[0]}.{self.source[1]} -> {self.source_schema}\n"
                f"  目标: {self.target[0]}.{self.target[1]} -> {self.target_schema}\n"
                f"参数结构必须完全相同才能连接"
            )
    
    
    def __repr__(self):
        if self.is_external:
            return f"ExternalConnection({self.source[0]}.{self.source[1]} -> external.{self.external_handler.__name__})"
        else:
            return f"Connection({self.source[0]}.{self.source[1]} -> {self.target[0]}.{self.target[1]})"


class ConnectionManager:
    """连接管理器"""
    
    def __init__(self):
        """初始化连接管理器"""
        self._connections: List[Connection] = []
        # 流式连接和非流式连接分类
        self._streaming_connections: List[Connection] = []
        self._data_connections: List[Connection] = []
        # 外部连接
        self._external_connections: List[Connection] = []
        # 索引：(source_node, source_param) -> [Connection]
        self._source_index: Dict[Tuple[str, str], List[Connection]] = {}
    
    def _add_connection(self, conn: Connection):
        """
        添加连接并自动分类
        
        Args:
            conn: 连接对象
        """
        self._connections.append(conn)
        
        # 根据连接类型分类
        if conn.is_external:
            self._external_connections.append(conn)
        elif conn.source_schema.is_streaming:
            self._streaming_connections.append(conn)
        else:
            self._data_connections.append(conn)
        
        # 建立索引
        if conn.source not in self._source_index:
            self._source_index[conn.source] = []
        self._source_index[conn.source].append(conn)
    
    async def route_chunk(self, source_node: str, source_param: str, chunk: StreamChunk):
        """
        路由 chunk 到所有目标（支持一对多广播）
        
        Args:
            source_node: 源节点 ID
            source_param: 源参数名称
            chunk: 流式数据块
        """
        connections = self._source_index.get((source_node, source_param), [])
        for conn in connections:
            if conn.is_external:
                # 外部连接：调用外部函数
                await self._call_external_handler(conn, chunk.data)
            elif conn.is_streaming and conn.target_queue:
                # 内部连接：发送到目标队列
                await conn.target_queue.put(chunk)
    
    def transfer_value(self, source_node: str, source_param: str, value, nodes_dict: dict = None):
        """
        传输非流式数据
        
        Args:
            source_node: 源节点 ID
            source_param: 源参数名称
            value: 数据值
            nodes_dict: 节点字典（node_id -> Node实例）
        """
        connections = self._source_index.get((source_node, source_param), [])
        for conn in connections:
            if conn.is_external:
                # 外部连接：调用外部函数
                asyncio.create_task(self._call_external_handler(conn, value))
            elif not conn.is_streaming:
                # 内部连接：直接设置目标参数的值
                if hasattr(conn, 'target_param_ref') and conn.target_param_ref:
                    conn.target_param_ref.value = value
    
    async def _call_external_handler(self, conn: Connection, data: Any):
        """调用外部处理函数"""
        try:
            if asyncio.iscoroutinefunction(conn.external_handler):
                await conn.external_handler(data)
            else:
                conn.external_handler(data)
        except Exception as e:
            print(f"❌ 外部处理函数异常: {e}")
    
    def get_connections(self) -> List[Connection]:
        """获取所有连接"""
        return self._connections.copy()
    
    def get_streaming_connections(self) -> List[Connection]:
        """获取所有流式连接"""
        return self._streaming_connections.copy()
    
    def get_data_connections(self) -> List[Connection]:
        """获取所有非流式连接"""
        return self._data_connections.copy()
    
    def get_external_connections(self) -> List[Connection]:
        """获取所有外部连接"""
        return self._external_connections.copy()
    
    def add_connection(self, source_node: str, source_param: str, source_node_obj,
                      target_node: str, target_param: str, target_node_obj) -> Connection:
        """
        创建并加入连接
        
        Args:
            source_node: 源节点 ID
            source_param: 源参数名称
            target_node: 目标节点 ID
            target_param: 目标参数名称
            source_node_obj: 源节点对象
            target_node_obj: 目标节点对象
            
        Returns:
            内部连接实例
        """
        # 从节点对象获取 schema
        source_schema = source_node_obj.outputs[source_param].schema
        target_schema = target_node_obj.inputs[target_param].schema
        
        # 创建连接
        conn = Connection(
            source_node, source_param,
            target_node, target_param,
            source_schema, target_schema
        )
        
        # 设置连接属性
        if conn.is_streaming:
            # 如果是流式连接，关联队列
            conn.target_queue = target_node_obj.inputs[target_param].stream_queue
        else:
            # 如果是非流式连接，保存目标参数的引用
            conn.target_param_ref = target_node_obj.inputs[target_param]
        
        self._add_connection(conn)

        return conn
    
    def add_external_connection(self, source_node: str, source_param: str,
                                 source_schema: ParameterSchema, external_handler: Callable) -> Connection:
        """
        创建并加入外部连接
        
        Args:
            source_node: 源节点 ID
            source_param: 源参数名称
            source_schema: 源参数 Schema
            external_handler: 外部处理函数
            
        Returns:
            外部连接实例
        """
        # 创建外部连接
        conn = Connection(
            source_node, source_param,
            "external", "handler",  # 目标为外部系统
            source_schema, source_schema  # 使用相同的 schema
        )
        
        # 标记为外部连接
        conn.is_external = True
        conn.external_handler = external_handler
        
        self._add_connection(conn)
        
        return conn
    
    def __repr__(self):
        return f"ConnectionManager(connections={len(self._connections)}, streaming={len(self._streaming_connections)}, data={len(self._data_connections)}, external={len(self._external_connections)})"

