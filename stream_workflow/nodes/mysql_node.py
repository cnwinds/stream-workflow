"""MySQL数据库节点（MySQL Node）"""

import aiomysql
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from stream_workflow.core import Node, ParameterSchema, WorkflowContext, register_node, NodeExecutionError

if TYPE_CHECKING:
    from stream_workflow.core.connection import ConnectionManager


@register_node('mysql_node')
class MysqlNode(Node):
    """
    MySQL数据库节点
    
    功能：提供MySQL数据库连接池和操作接口，供其他节点调用
    
    配置格式：
        config:
          # 方式1：复用已存在的连接池（推荐，如果系统中已有连接池）
          pool_ref: "existing_pool_key"  # 从全局变量中获取已存在的连接池（可选）
                                           使用aiomysql.create_pool创建的连接池
          
          # 方式2：创建新连接池（如果未提供 pool_ref 或 pool_ref 不存在）
          host: "localhost"          # 数据库主机地址（创建新池时必需）
          port: 3306                 # 端口号（默认 3306）
          user: "root"                # 用户名（创建新池时必需）
          password: "password"        # 密码（创建新池时必需）
          database: "test_db"         # 数据库名（创建新池时必需）
          charset: "utf8mb4"          # 字符集（默认 utf8mb4）
          pool_min_size: 1            # 连接池最小连接数（默认 1）
          pool_max_size: 10           # 连接池最大连接数（默认 10）
          pool_timeout: 30            # 获取连接超时时间（秒，默认 30）
    
    使用方式：
        其他节点可以通过 context.get_global_var('mysql_node_id') 获取节点实例，
        然后调用以下方法：
        - query(sql, params): 执行查询，返回结果列表
        - execute(sql, params): 执行更新/删除，返回受影响行数
        - insert(sql, params): 执行插入，返回插入的自增ID
        - execute_many(sql, params_list): 批量执行，返回受影响总行数
    """
    
    # 节点执行模式：顺序执行，服务型节点
    EXECUTION_MODE = 'sequential'
    
    # 定义输入参数结构（服务型节点，通常不需要输入）
    INPUT_PARAMS = {}
    
    # 定义输出参数结构（服务型节点，通常不需要输出）
    OUTPUT_PARAMS = {}
    
    async def initialize(self, context: WorkflowContext):
        """初始化节点，建立数据库连接池"""
        # 从配置读取连接参数
        config_dict = self.get_config('config', {})
        if not isinstance(config_dict, dict):
            raise NodeExecutionError(
                self.node_id,
                "MySQL节点配置格式错误：config 必须是字典"
            )
        
        # 标记是否拥有连接池（是否需要关闭）
        self._pool_owner = False
        
        # 尝试从全局变量中获取已存在的连接池
        pool_ref = config_dict.get('pool_ref')
        if pool_ref:
            existing_pool = context.get_global_var(pool_ref)
            if existing_pool:
                # 验证是否为有效的 aiomysql.Pool 对象
                if isinstance(existing_pool, aiomysql.Pool):
                    self._pool = existing_pool
                    self._pool_owner = False  # 不拥有连接池，不负责关闭
                    
                    # 测试连接池是否可用
                    try:
                        async with self._pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                await cur.execute("SELECT 1")
                                await cur.fetchone()
                        
                        context.log_info(
                            f"MySQL节点 {self.node_id} 成功复用已存在的连接池 "
                            f"(pool_ref={pool_ref})"
                        )
                        
                        # 将节点实例注册到全局对象
                        context.set_global_var(self.node_id, self)
                        context.log_info(f"MySQL节点 {self.node_id} 已注册到全局对象")
                        return
                    except Exception as e:
                        context.log_warning(
                            f"MySQL节点 {self.node_id} 从全局变量获取的连接池无效: {e}，"
                            f"将创建新连接池"
                        )
                else:
                    context.log_warning(
                        f"MySQL节点 {self.node_id} 全局变量 '{pool_ref}' 不是有效的连接池对象，"
                        f"将创建新连接池"
                    )
            else:
                context.log_warning(
                    f"MySQL节点 {self.node_id} 全局变量 '{pool_ref}' 不存在，"
                    f"将创建新连接池"
                )
        
        # 如果没有提供 pool_ref 或获取失败，创建新连接池
        # 读取必需参数
        host = config_dict.get('host')
        user = config_dict.get('user')
        password = config_dict.get('password')
        database = config_dict.get('database')
        
        if not all([host, user, password, database]):
            raise NodeExecutionError(
                self.node_id,
                "MySQL节点缺少必需配置：host, user, password, database "
                "(或提供有效的 pool_ref 来复用已存在的连接池)"
            )
        
        # 读取可选参数
        port = config_dict.get('port', 3306)
        charset = config_dict.get('charset', 'utf8mb4')
        pool_min_size = config_dict.get('pool_min_size', 1)
        pool_max_size = config_dict.get('pool_max_size', 10)
        pool_timeout = config_dict.get('pool_timeout', 30)
        
        # 创建连接池
        try:
            self._pool = await aiomysql.create_pool(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database,
                charset=charset,
                minsize=pool_min_size,
                maxsize=pool_max_size,
                autocommit=True
            )
            self._pool_owner = True  # 拥有连接池，需要负责关闭
            
            # 测试连接
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
            
            context.log_info(
                f"MySQL节点 {self.node_id} 连接池创建成功 "
                f"(host={host}, port={port}, database={database})"
            )
            
            # 将节点实例注册到全局对象
            context.set_global_var(self.node_id, self)
            context.log_info(f"MySQL节点 {self.node_id} 已注册到全局对象")
            
        except Exception as e:
            context.log_error(f"MySQL节点 {self.node_id} 连接池创建失败: {e}")
            raise NodeExecutionError(
                self.node_id,
                f"MySQL连接池创建失败: {str(e)}",
                e
            )
    
    async def run(self, context: WorkflowContext):
        """运行节点（服务型节点，通常不需要执行逻辑）"""
        # 服务型节点，初始化后即可提供服务，不需要执行逻辑
        return {}
    
    async def query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行SELECT查询语句
        
        Args:
            sql: SQL查询语句
            params: 查询参数（元组格式，用于参数化查询）
            
        Returns:
            查询结果列表，每个元素是一个字典，键为字段名
            
        Example:
            results = await mysql_node.query("SELECT * FROM users WHERE id = %s", (1,))
        """
        if not self._pool:
            raise NodeExecutionError(self.node_id, "MySQL连接池未初始化")
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(sql, params)
                    results = await cur.fetchall()
                    return list(results) if results else []
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"MySQL查询执行失败: {str(e)}",
                e
            )
    
    async def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行UPDATE或DELETE语句
        
        Args:
            sql: SQL语句
            params: 参数（元组格式，用于参数化查询）
            
        Returns:
            受影响的行数
            
        Example:
            rows = await mysql_node.execute(
                "UPDATE users SET name = %s WHERE id = %s",
                ("新名称", 1)
            )
        """
        if not self._pool:
            raise NodeExecutionError(self.node_id, "MySQL连接池未初始化")
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    return cur.rowcount
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"MySQL执行失败: {str(e)}",
                e
            )
    
    async def insert(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行INSERT语句
        
        Args:
            sql: SQL插入语句
            params: 参数（元组格式，用于参数化查询）
            
        Returns:
            插入记录的自增ID（lastrowid）
            
        Example:
            insert_id = await mysql_node.insert(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                ("新用户", "user@example.com")
            )
        """
        if not self._pool:
            raise NodeExecutionError(self.node_id, "MySQL连接池未初始化")
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, params)
                    return cur.lastrowid
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"MySQL插入失败: {str(e)}",
                e
            )
    
    async def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表（每个元素是一个元组）
            
        Returns:
            受影响的总行数
            
        Example:
            rows = await mysql_node.execute_many(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                [("用户1", "user1@example.com"), ("用户2", "user2@example.com")]
            )
        """
        if not self._pool:
            raise NodeExecutionError(self.node_id, "MySQL连接池未初始化")
        
        if not params_list:
            return 0
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(sql, params_list)
                    return cur.rowcount
        except Exception as e:
            raise NodeExecutionError(
                self.node_id,
                f"MySQL批量执行失败: {str(e)}",
                e
            )
    
    async def shutdown(self):
        """关闭节点，清理连接池"""
        # 只有拥有连接池的节点才负责关闭（避免关闭复用的连接池）
        if hasattr(self, '_pool_owner') and self._pool_owner and hasattr(self, '_pool') and self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._pool_owner = False

