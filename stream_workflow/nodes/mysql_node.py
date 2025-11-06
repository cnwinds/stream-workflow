"""MySQL数据库节点（MySQL Node）"""

import aiomysql
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from stream_workflow.core import Node, ParameterSchema, WorkflowContext, register_node, NodeExecutionError

if TYPE_CHECKING:
    from stream_workflow.core.connection import ConnectionManager

# 尝试导入 SQLAlchemy 相关类型（可选依赖）
try:
    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession
    from sqlalchemy import text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    AsyncEngine = None
    AsyncSession = None


@register_node('mysql_node')
class MysqlNode(Node):
    """MySQL数据库节点
    
    功能：提供MySQL数据库连接池和操作接口，供其他节点调用
    
    配置格式：
        config:
          # 方式1：复用已存在的 DatabaseManager（推荐，如果系统中已有 DatabaseManager）
          db_ref: "db_manager_key"  # 从全局变量中获取 DatabaseManager 实例，调用 get_engine() 获取 AsyncEngine
          
          # 方式2：复用已存在的 aiomysql.Pool（向后兼容）
          # db_ref: "pool_key"  # 从全局变量中获取 aiomysql.Pool 实例
          
          # 方式3：创建新连接池（如果未提供 db_ref 或 db_ref 不存在）
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
        self._db_manager = None  # DatabaseManager 实例
        self._engine = None  # AsyncEngine 实例
        self._pool = None  # aiomysql.Pool 实例（向后兼容）
        
        # 尝试从全局变量中获取已存在的连接池或 DatabaseManager
        db_ref = config_dict.get('db_ref')
        if db_ref:
            existing_obj = context.get_global_var(db_ref)
            if existing_obj:
                # 方式1：尝试作为 DatabaseManager 处理
                if hasattr(existing_obj, 'get_engine'):
                    # 是 DatabaseManager 实例
                    self._db_manager = existing_obj
                    self._engine = existing_obj.get_engine()
                    self._pool_owner = False  # 不拥有连接池，不负责关闭
                    
                    # 测试连接是否可用
                    try:
                        if SQLALCHEMY_AVAILABLE and isinstance(self._engine, AsyncEngine):
                            async with async_sessionmaker(self._engine)() as session:
                                result = await session.execute(text("SELECT 1"))
                                result.fetchone()
                        else:
                            # 如果没有 SQLAlchemy，尝试使用 DatabaseManager 的方法
                            health = await self._db_manager.health_check()
                            if health.get("status") != "healthy":
                                raise Exception("数据库健康检查失败")
                        
                        context.log_info(
                            f"MySQL节点 {self.node_id} 成功复用 DatabaseManager "
                            f"(db_ref={db_ref})"
                        )
                        
                        # 将节点实例注册到全局对象
                        context.set_global_var(self.node_id, self)
                        context.log_info(f"MySQL节点 {self.node_id} 已注册到全局对象")
                        return
                    except Exception as e:
                        context.log_warning(
                            f"MySQL节点 {self.node_id} 从 DatabaseManager 获取的连接无效: {e}，"
                            f"将创建新连接池"
                        )
                
                # 方式2：尝试作为 aiomysql.Pool 处理（向后兼容）
                elif isinstance(existing_obj, aiomysql.Pool):
                    self._pool = existing_obj
                    self._pool_owner = False  # 不拥有连接池，不负责关闭
                    
                    # 测试连接池是否可用
                    try:
                        async with self._pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                await cur.execute("SELECT 1")
                                await cur.fetchone()
                        
                        context.log_info(
                            f"MySQL节点 {self.node_id} 成功复用已存在的 aiomysql 连接池 "
                            f"(db_ref={db_ref})"
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
                        f"MySQL节点 {self.node_id} 全局变量 '{db_ref}' 不是有效的 DatabaseManager 或连接池对象，"
                        f"将创建新连接池"
                    )
            else:
                context.log_warning(
                    f"MySQL节点 {self.node_id} 全局变量 '{db_ref}' 不存在，"
                    f"将创建新连接池"
                )
        
        # 如果没有提供 db_ref 或获取失败，创建新连接池
        # 读取必需参数
        host = config_dict.get('host')
        user = config_dict.get('user')
        password = config_dict.get('password')
        database = config_dict.get('database')
        
        if not all([host, user, password, database]):
            raise NodeExecutionError(
                self.node_id,
                "MySQL节点缺少必需配置：host, user, password, database "
                "(或提供有效的 db_ref 来复用已存在的连接池)"
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
    
    async def query(self, sql: str, params: Optional[Union[tuple, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        执行SELECT查询语句
        
        Args:
            sql: SQL查询语句
            params: 查询参数（元组格式或字典格式，用于参数化查询）
                   - 元组格式：用于 aiomysql，如 (1, "test")
                   - 字典格式：用于 SQLAlchemy，如 {"id": 1, "name": "test"}
            
        Returns:
            查询结果列表，每个元素是一个字典，键为字段名
            
        Example:
            # 使用元组参数（aiomysql）
            results = await mysql_node.query("SELECT * FROM users WHERE id = %s", (1,))
            
            # 使用字典参数（SQLAlchemy/DatabaseManager）
            results = await mysql_node.query("SELECT * FROM users WHERE id = :id", {"id": 1})
        """
        # 优先使用 DatabaseManager
        if self._db_manager:
            try:
                # DatabaseManager 使用字典参数，如果传入元组则转换为字典（简单映射）
                # 注意：如果 SQL 使用 %s 占位符，此转换可能不工作，建议使用字典参数
                if isinstance(params, tuple):
                    params_dict = self._tuple_to_dict_params(sql, params)
                else:
                    params_dict = params or {}
                return await self._db_manager.execute_query(sql, params_dict)
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL查询执行失败: {str(e)}",
                    e
                )
        
        # 使用 AsyncEngine（如果可用）
        if self._engine and SQLALCHEMY_AVAILABLE:
            try:
                # 转换参数格式
                if isinstance(params, tuple):
                    params_dict = self._tuple_to_dict_params(sql, params)
                else:
                    params_dict = params or {}
                
                async with async_sessionmaker(self._engine)() as session:
                    result = await session.execute(text(sql), params_dict)
                    rows = result.fetchall()
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL查询执行失败: {str(e)}",
                    e
                )
        
        # 使用 aiomysql.Pool（向后兼容）
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
    
    def _tuple_to_dict_params(self, sql: str, params: tuple) -> Dict[str, Any]:
        """
        将元组参数转换为字典参数（简单实现）
        
        注意：此方法仅用于向后兼容。使用 DatabaseManager 时，建议直接使用字典参数。
        如果 SQL 使用 %s 占位符，此方法无法正确转换，因为需要知道 SQL 中的参数名称。
        """
        if not params:
            return {}
        
        # 如果 SQL 中已经有命名参数（:param_name），直接使用位置索引作为键
        # 但这种方式不适用于 %s 占位符
        # 为了简单，我们假设 SQL 使用命名参数，将元组参数映射为 param_0, param_1 等
        # 实际使用时，建议直接使用字典参数
        params_dict = {}
        for i, value in enumerate(params):
            params_dict[f"param_{i}"] = value
        
        # 注意：如果 SQL 使用 %s，这种方法不会工作
        # 建议在使用 DatabaseManager 时，SQL 使用命名参数格式（:param_name）
        return params_dict
    
    async def execute(self, sql: str, params: Optional[Union[tuple, Dict[str, Any]]] = None) -> int:
        """
        执行UPDATE或DELETE语句
        
        Args:
            sql: SQL语句
            params: 参数（元组格式或字典格式，用于参数化查询）
            
        Returns:
            受影响的行数
            
        Example:
            # 使用元组参数
            rows = await mysql_node.execute(
                "UPDATE users SET name = %s WHERE id = %s",
                ("新名称", 1)
            )
            
            # 使用字典参数
            rows = await mysql_node.execute(
                "UPDATE users SET name = :name WHERE id = :id",
                {"name": "新名称", "id": 1}
            )
        """
        # 优先使用 DatabaseManager
        if self._db_manager:
            try:
                if isinstance(params, tuple):
                    params_dict = self._tuple_to_dict_params(sql, params)
                else:
                    params_dict = params or {}
                return await self._db_manager.execute_update(sql, params_dict)
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL执行失败: {str(e)}",
                    e
                )
        
        # 使用 AsyncEngine
        if self._engine and SQLALCHEMY_AVAILABLE:
            try:
                if isinstance(params, tuple):
                    params_dict = self._tuple_to_dict_params(sql, params)
                else:
                    params_dict = params or {}
                
                async with async_sessionmaker(self._engine)() as session:
                    result = await session.execute(text(sql), params_dict)
                    await session.commit()
                    return result.rowcount
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL执行失败: {str(e)}",
                    e
                )
        
        # 使用 aiomysql.Pool（向后兼容）
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
    
    async def insert(self, sql: str, params: Optional[Union[tuple, Dict[str, Any]]] = None) -> int:
        """
        执行INSERT语句
        
        Args:
            sql: SQL插入语句
            params: 参数（元组格式或字典格式，用于参数化查询）
            
        Returns:
            插入记录的自增ID（lastrowid）
            
        Example:
            # 使用元组参数
            insert_id = await mysql_node.insert(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                ("新用户", "user@example.com")
            )
            
            # 使用字典参数
            insert_id = await mysql_node.insert(
                "INSERT INTO users (name, email) VALUES (:name, :email)",
                {"name": "新用户", "email": "user@example.com"}
            )
        """
        # 优先使用 DatabaseManager
        if self._db_manager:
            try:
                if isinstance(params, tuple):
                    params_dict = self._tuple_to_dict_params(sql, params)
                else:
                    params_dict = params or {}
                return await self._db_manager.execute_insert(sql, params_dict)
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL插入失败: {str(e)}",
                    e
                )
        
        # 使用 AsyncEngine
        if self._engine and SQLALCHEMY_AVAILABLE:
            try:
                if isinstance(params, tuple):
                    params_dict = self._tuple_to_dict_params(sql, params)
                else:
                    params_dict = params or {}
                
                async with async_sessionmaker(self._engine)() as session:
                    result = await session.execute(text(sql), params_dict)
                    await session.commit()
                    return result.lastrowid
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL插入失败: {str(e)}",
                    e
                )
        
        # 使用 aiomysql.Pool（向后兼容）
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
    
    async def execute_many(self, sql: str, params_list: List[Union[tuple, Dict[str, Any]]]) -> int:
        """
        批量执行语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表（每个元素是元组或字典）
            
        Returns:
            受影响的总行数
            
        Example:
            # 使用元组参数列表
            rows = await mysql_node.execute_many(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                [("用户1", "user1@example.com"), ("用户2", "user2@example.com")]
            )
            
            # 使用字典参数列表
            rows = await mysql_node.execute_many(
                "INSERT INTO users (name, email) VALUES (:name, :email)",
                [{"name": "用户1", "email": "user1@example.com"}, {"name": "用户2", "email": "user2@example.com"}]
            )
        """
        if not params_list:
            return 0
        
        # 优先使用 DatabaseManager
        if self._db_manager:
            try:
                # 转换参数格式
                if params_list and isinstance(params_list[0], tuple):
                    params_dict_list = [self._tuple_to_dict_params(sql, p) for p in params_list]
                else:
                    params_dict_list = params_list
                return await self._db_manager.execute_many(sql, params_dict_list)
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL批量执行失败: {str(e)}",
                    e
                )
        
        # 使用 AsyncEngine
        if self._engine and SQLALCHEMY_AVAILABLE:
            try:
                # 转换参数格式
                if params_list and isinstance(params_list[0], tuple):
                    params_dict_list = [self._tuple_to_dict_params(sql, p) for p in params_list]
                else:
                    params_dict_list = params_list
                
                total_affected = 0
                async with async_sessionmaker(self._engine)() as session:
                    for params in params_dict_list:
                        result = await session.execute(text(sql), params)
                        total_affected += result.rowcount
                    await session.commit()
                return total_affected
            except Exception as e:
                raise NodeExecutionError(
                    self.node_id,
                    f"MySQL批量执行失败: {str(e)}",
                    e
                )
        
        # 使用 aiomysql.Pool（向后兼容）
        if not self._pool:
            raise NodeExecutionError(self.node_id, "MySQL连接池未初始化")
        
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

