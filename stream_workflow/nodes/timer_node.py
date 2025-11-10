"""定时器节点（Timer Node）"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, Optional, Set, TYPE_CHECKING
from stream_workflow.core import Node, ParameterSchema, WorkflowContext, register_node

if TYPE_CHECKING:
    from stream_workflow.core.connection import ConnectionManager

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


@register_node('timer_node')
class TimerNode(Node):
    """定时器节点
    
    功能：按配置的周期定时触发目标节点
    
    配置格式：
        config:
          target_node_id1: { interval: "5s", data: {} }
          target_node_id2: { interval: "0 * * * *", data: { custom_field: "value" } }
        
        示例：
        config:
          target_node1: { interval: "5s", data: {} }
          target_node2: { interval: "0 * * * *", data: {} }
    
    配置参数说明：
        - 每个目标节点ID作为key，值为包含以下字段的字典：
          - interval: 触发周期配置（必需）
            * 时间单位格式：如 "5s"（每5秒）、"1m"（每1分钟）、"1h"（每1小时）
            * Cron表达式：标准5字段格式（分钟 小时 日 月 星期），如 "0 * * * *"（每小时整点）
          - data: 触发消息的数据部分，字典类型（可选，默认 {}）
    
    输出参数：
        trigger: 流式输出参数（用于向后兼容，实际触发通过 feed_input_chunk 直接发送）
    
    触发消息格式：
        {
            "timestamp": "2024-01-01T12:00:00",  # ISO格式时间戳
            "timer_id": "timer_node_id",  # timer节点的ID
            "data": {...}  # 从配置的 data 字段获取
        }
    
    注意：
        - 标准Cron表达式不支持秒级精度，如需秒级精度请使用时间单位格式（如 "5s"）
        - 每个目标节点有独立的定时任务，互不影响
    """
    
    # 节点执行模式：流式模式，持续运行
    EXECUTION_MODE = 'streaming'
    
    # 定义输出参数结构
    OUTPUT_PARAMS = {
        "trigger": ParameterSchema(
            is_streaming=True,
            schema={
                "timestamp": "string",
                "timer_id": "string",
                "data": "dict"
            }
        )
    }
    
    async def initialize(self, context: WorkflowContext):
        """初始化节点"""
        self._tasks: Set[asyncio.Task] = set()  # 存储所有定时任务
        self._input_param_cache: Dict[str, str] = {}  # 目标节点输入参数名称缓存
        context.log_info(f"定时器节点 {self.node_id} 初始化完成")
    
    async def run(self, context: WorkflowContext):
        """
        运行定时器节点
        
        为每个配置的目标节点创建独立的定时任务
        """
        # 获取配置
        config_dict = self.get_config('config', {})
        if not isinstance(config_dict, dict):
            context.log_error(f"定时器节点 {self.node_id} 配置格式错误：config 必须是字典")
            return
        
        # 过滤出目标节点配置（排除系统字段）
        target_configs = {}
        for key, value in config_dict.items():
            if isinstance(value, dict) and 'interval' in value:
                target_configs[key] = value
        
        if not target_configs:
            context.log_warning(f"定时器节点 {self.node_id} 没有配置任何目标节点")
            return
        
        context.log_info(f"定时器节点 {self.node_id} 发现 {len(target_configs)} 个目标节点")
        
        # 构建目标节点输入参数名称缓存
        self._build_input_param_cache(list(target_configs.keys()), context)
        
        # 为每个目标节点创建独立的定时任务
        for target_node_id, target_config in target_configs.items():
            interval = target_config.get('interval')
            data = target_config.get('data', {})
            
            if not interval:
                context.log_error(f"目标节点 {target_node_id} 缺少 interval 配置")
                continue
            
            # 创建定时任务
            task = asyncio.create_task(
                self._trigger_loop(context, target_node_id, interval, data)
            )
            self._tasks.add(task)
            context.log_info(f"已为目标节点 {target_node_id} 创建定时任务，周期: {interval}")
        
        # 等待所有任务完成（实际上会一直运行直到被取消）
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            context.log_info(f"定时器节点 {self.node_id} 所有任务已取消")
    
    async def _trigger_loop(self, context: WorkflowContext, 
                            target_node_id: str, interval: str, data: Dict[str, Any]):
        """
        定时触发循环
        
        Args:
            context: 工作流上下文
            target_node_id: 目标节点ID
            interval: 触发周期配置
            data: 触发消息数据
        """
        try:
            # 检查是否是cron表达式
            is_cron = self._is_cron_expression(interval)
            cron_iter = None
            
            if is_cron:
                # Cron表达式：需要特殊处理
                if not CRONITER_AVAILABLE:
                    context.log_error(f"目标节点 {target_node_id} 使用cron表达式但未安装 croniter 库")
                    return
                try:
                    cron_iter = croniter(interval)
                except Exception as e:
                    context.log_error(f"目标节点 {target_node_id} 的cron表达式无效: {interval}, 错误: {e}")
                    return
                next_trigger_delay = None  # Cron表达式不需要delay
            else:
                # 时间单位格式：解析周期配置
                next_trigger_delay = self._parse_interval(interval)
                if next_trigger_delay is None:
                    context.log_error(f"目标节点 {target_node_id} 的周期配置格式错误: {interval}")
                    return
            
            context.log_info(f"目标节点 {target_node_id} 定时任务启动，周期: {interval}")
            
            while True:
                if is_cron and cron_iter:
                    # Cron表达式：基于当前时间计算下次触发时间
                    now = datetime.now()
                    next_time = cron_iter.get_next(datetime, now)
                    delay = (next_time - now).total_seconds()
                    # 如果已经过了触发时间，立即触发（delay可能为0或负数）
                    if delay <= 0:
                        delay = 0
                    await asyncio.sleep(delay)
                else:
                    # 时间单位格式：直接使用计算出的延迟
                    await asyncio.sleep(next_trigger_delay)
                
                # 构建触发消息
                trigger_message = {
                    "timestamp": datetime.now().isoformat(),
                    "timer_id": self.node_id,
                    "data": data.copy() if isinstance(data, dict) else {}
                }
                
                # 获取目标节点
                target_node = self.engine.get_node(target_node_id)
                if not target_node:
                    context.log_error(f"目标节点 {target_node_id} 不存在")
                    continue
                
                # 从缓存获取目标节点的输入参数名称
                input_param_name = self._input_param_cache.get(target_node_id)
                if not input_param_name:
                    context.log_error(f"无法确定目标节点 {target_node_id} 的输入参数名称")
                    continue
                
                # 发送触发消息
                try:
                    await target_node.feed_input_chunk(input_param_name, trigger_message)
                    context.log_info(f"定时器 {self.node_id} 触发目标节点 {target_node_id}.{input_param_name}")
                except Exception as e:
                    context.log_error(f"触发目标节点 {target_node_id} 失败: {e}")
                
        except asyncio.CancelledError:
            context.log_info(f"目标节点 {target_node_id} 的定时任务已取消")
        except Exception as e:
            context.log_error(f"目标节点 {target_node_id} 的定时任务异常: {e}")
    
    def _parse_interval(self, interval: Any) -> Optional[float]:
        """
        解析周期配置
        
        Args:
            interval: 周期配置（数字、字符串格式或cron表达式）
        
        Returns:
            返回秒数（对于时间单位格式），cron表达式返回None（需要特殊处理）
        """
        if isinstance(interval, (int, float)):
            # 数字格式：直接作为秒数
            return float(interval)
        
        if not isinstance(interval, str):
            return None
        
        # 检查是否是cron表达式
        if self._is_cron_expression(interval):
            return None  # cron表达式需要特殊处理
        
        # 时间单位格式：如 "5s", "1m", "1h"
        match = re.match(r'^(\d+(?:\.\d+)?)([smh])$', interval.strip())
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            
            if unit == 's':
                return value
            elif unit == 'm':
                return value * 60
            elif unit == 'h':
                return value * 3600
        
        return None
    
    def _is_cron_expression(self, interval: str) -> bool:
        """
        判断是否是cron表达式
        
        Args:
            interval: 周期配置字符串
        
        Returns:
            如果是cron表达式返回True
        """
        if not isinstance(interval, str):
            return False
        
        # Cron表达式特征：包含多个空格分隔的字段，通常有5个字段
        parts = interval.strip().split()
        if len(parts) == 5:
            # 标准5字段cron表达式
            return True
        
        return False
    
    def _build_input_param_cache(self, target_node_ids: list, context: WorkflowContext):
        """
        构建目标节点输入参数名称缓存
        
        策略：
        1. 优先从连接配置中获取
        2. 否则从目标节点的INPUT_PARAMS中获取第一个输入参数
        3. 否则使用默认值 "input"
        
        Args:
            target_node_ids: 目标节点ID列表
            context: 工作流上下文（用于日志）
        """
        connection_manager = self.engine.get_connection_manager()
        connections = connection_manager.get_connected_nodes(self.node_id, "trigger", is_output=True)
        
        # 构建连接映射：target_node_id -> target_param
        connection_map = {}
        for conn in connections:
            target_node = conn.get("target_node")
            if target_node:
                connection_map[target_node] = conn.get("target_param")
        
        # 为每个目标节点确定输入参数名称
        for target_node_id in target_node_ids:
            # 策略1: 从连接配置中获取
            if target_node_id in connection_map:
                self._input_param_cache[target_node_id] = connection_map[target_node_id]
                context.log_debug(f"目标节点 {target_node_id} 输入参数从连接配置获取: {connection_map[target_node_id]}")
                continue
            
            # 策略2: 从目标节点的INPUT_PARAMS中获取第一个输入参数
            target_node = self.engine.get_node(target_node_id)
            if target_node and target_node.inputs:
                first_input = next(iter(target_node.inputs.keys()), None)
                if first_input:
                    self._input_param_cache[target_node_id] = first_input
                    context.log_debug(f"目标节点 {target_node_id} 输入参数从节点定义获取: {first_input}")
                    continue
            
            # 策略3: 使用默认值
            self._input_param_cache[target_node_id] = "input"
            context.log_debug(f"目标节点 {target_node_id} 输入参数使用默认值: input")
    
    def _get_target_input_param_name(self, target_node_id: str) -> Optional[str]:
        """
        从缓存获取目标节点的输入参数名称
        
        Args:
            target_node_id: 目标节点ID
        
        Returns:
            输入参数名称，如果缓存中没有则返回None
        """
        return self._input_param_cache.get(target_node_id)
    
    async def shutdown(self):
        """关闭节点，取消所有定时任务"""
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()

