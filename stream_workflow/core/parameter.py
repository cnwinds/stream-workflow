"""参数系统：参数定义、Schema 和验证"""

import time
from typing import Any, Dict, Union

# 字段定义类型（用于 CONFIG_PARAMS 的类型注解）
# - 简单类型: "string", "integer", "float", "bytes", "boolean", "dict", "list", "any"
# 支持两种格式：
# - 结构体（简单格式）: {"field_name": "type", ...}
# - 结构体（详细格式）: {
#     "field_name": {
#         "type": "string",
#         "required": True,
#         "description": "字段说明",
#         "default": "默认值"
#     },
#     ...
#   }
FieldSchemaDef = Union[str, Dict[str, Any]]

# 类型映射表（共享）
TYPE_MAP = {
    'bytes': bytes,
    'string': str,
    'integer': int,
    'float': float,
    'boolean': bool,
    'dict': dict,
    'list': list,
    'any': object
}


class FieldSchema:
    """
    字段定义 Schema（用于 CONFIG_PARAMS）
    
    封装字段定义的解析、验证和默认值处理逻辑
    """
    
    TYPE_MAP = TYPE_MAP  # 引用共享的类型映射表
    
    def __init__(self, field_def: FieldSchemaDef):
        """
        初始化字段 Schema
        
        Args:
            field_def: 字段定义
                    - 简单格式: "string" - 直接是类型字符串
                    - 详细格式: {"type": "string", "required": True, "description": "...", "default": "..."}
        """
        self._parse(field_def)
    
    def _parse(self, field_def: FieldSchemaDef):
        """解析字段定义"""
        if isinstance(field_def, str):
            # 简单格式：直接是类型字符串
            self.type = field_def
            self.required = False
            self.description = ""
            self.default = None
        elif isinstance(field_def, dict):
            # 详细格式：包含 type、required、description、default
            self.type = field_def.get("type", "any")
            self.required = field_def.get("required", False)
            self.description = field_def.get("description", "")
            self.default = field_def.get("default", None)
        else:
            raise ValueError(f"无效的字段定义格式: {field_def}")
    
    def validate_value(self, value: Any, param_name: str = "") -> None:
        """
        验证值是否符合字段定义
        
        Args:
            value: 要验证的值
            param_name: 参数名称（用于错误信息）
            
        Raises:
            TypeError: 类型不匹配
        """
        if value is None:
            return  # None 值由调用方处理（应用默认值或检查必传）
        
        expected_type = self.TYPE_MAP.get(self.type)
        if expected_type and expected_type != object:
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"类型不匹配: 期望 {self.type}, 实际 {type(value).__name__}"
                )
    
    def get_default(self) -> Any:
        """
        获取默认值
        
        Returns:
            默认值，如果没有则返回 None
        """
        return self.default
    
    def is_required(self) -> bool:
        """
        检查字段是否必传
        
        Returns:
            如果必传返回 True，否则返回 False
        """
        return self.required
    
    def get_description(self) -> str:
        """
        获取字段描述
        
        Returns:
            字段描述字符串
        """
        return self.description
    
    def apply_default(self, config: Dict[str, Any], param_name: str) -> Any:
        """
        应用默认值到配置字典（如果值不存在且有默认值）
        
        Args:
            config: 配置字典
            param_name: 参数名称
            
        Returns:
            参数值（可能是原始值或默认值）
        """
        value = config.get(param_name)
        if value is None and self.default is not None:
            config[param_name] = self.default
            return self.default
        return value
    
    def validate_and_apply(self, config: Dict[str, Any], param_name: str, node_id: str = "") -> None:
        """
        验证并应用默认值（完整流程）
        
        Args:
            config: 配置字典
            param_name: 参数名称
            node_id: 节点ID（用于错误信息）
            
        Raises:
            ValueError: 缺少必传配置参数或参数类型不匹配
        """
        value = self.apply_default(config, param_name)
        
        # 检查必传字段
        if value is None and self.required:
            error_msg = f"节点 {node_id} 缺少必传配置参数: {param_name}" if node_id else f"缺少必传配置参数: {param_name}"
            if self.description:
                error_msg += f" ({self.description})"
            raise ValueError(error_msg)
        
        # 验证类型
        if value is not None:
            try:
                self.validate_value(value, param_name)
            except TypeError as e:
                error_msg = f"节点 {node_id} 配置参数 {param_name} 验证失败: {str(e)}" if node_id else f"配置参数 {param_name} 验证失败: {str(e)}"
                if self.description:
                    error_msg += f" ({self.description})"
                raise ValueError(error_msg)
    
    @classmethod
    def from_def(cls, field_def: FieldSchemaDef) -> 'FieldSchema':
        """
        从字段定义创建 FieldSchema 实例（工厂方法）
        
        Args:
            field_def: 字段定义
            
        Returns:
            FieldSchema 实例
        """
        return cls(field_def)
    
    def __repr__(self):
        return f"FieldSchema(type={self.type!r}, required={self.required}, description={self.description!r}, default={self.default!r})"


class ParameterSchema:
    """参数结构定义"""
    
    def __init__(self, is_streaming: bool = False, schema: Union[str, dict] = None, 
                 description: str = ""):
        """
        初始化参数 Schema
        
        Args:
            is_streaming: 是否为流式参数
            schema: 参数结构定义
                    - 简单类型: "string", "integer", "float", "bytes", "boolean", "dict", "list", "any"
                    - 结构体（简单格式）: {"field_name": "type", ...}
                    - 结构体（详细格式）: {
                        "field_name": {
                            "type": "string",
                            "required": True,
                            "description": "字段说明",
                            "default": "默认值"
                        },
                        ...
                      }
            description: 参数备注说明（默认空字符串）
        """
        self.is_streaming = is_streaming
        self.schema = schema or {}
        self.description = description
    
    def validate_value(self, value: Any) -> bool:
        """
        验证值是否符合 schema
        
        Args:
            value: 要验证的值
            
        Returns:
            验证通过返回 True
            
        Raises:
            ValueError: schema 为字典时值不是字典，或缺少必需字段
            TypeError: 类型不匹配
        """
        if isinstance(self.schema, str):
            # 简单类型验证：使用 FieldSchema 来验证
            if value is not None:  # 允许 None 值
                field_schema = FieldSchema(self.schema)
                field_schema.validate_value(value)
            return True
        
        if isinstance(self.schema, dict):
            # 字典结构验证：使用 FieldSchema 来管理每个字段
            if not isinstance(value, dict):
                raise ValueError(f"期望字典类型，实际: {type(value).__name__}")
            
            for field_name, field_def in self.schema.items():
                # 使用 FieldSchema 来处理字段定义
                field_schema = FieldSchema.from_def(field_def)
                
                # 如果字段不存在，应用默认值（如果有）
                if field_name not in value:
                    default = field_schema.get_default()
                    if default is not None:
                        value[field_name] = default
                    elif field_schema.is_required():
                        # 检查必传字段
                        error_msg = f"缺少必传字段: {field_name}"
                        description = field_schema.get_description()
                        if description:
                            error_msg += f" ({description})"
                        raise ValueError(error_msg)
                
                # 如果字段存在，验证类型
                if field_name in value:
                    field_schema.validate_value(value[field_name], field_name)
        
        return True
    
    def matches(self, other: 'ParameterSchema') -> bool:
        """
        判断两个 schema 是否完全一致
        
        Args:
            other: 另一个 ParameterSchema
            
        Returns:
            完全一致返回 True，否则返回 False
        """
        return (self.is_streaming == other.is_streaming and
                self.schema == other.schema)
    
    def __repr__(self):
        return f"ParameterSchema(streaming={self.is_streaming}, schema={self.schema}, description={self.description!r})"
    
    def __eq__(self, other):
        if not isinstance(other, ParameterSchema):
            return False
        return self.matches(other)


class StreamChunk:
    """流式数据块"""
    
    def __init__(self, data: Any, schema: ParameterSchema):
        """
        初始化流式数据块
        
        Args:
            data: 数据内容（通常是字典）
            schema: 参数 Schema
            
        Raises:
            ValueError/TypeError: 数据不符合 schema
        """
        self.data = data
        self.schema = schema
        self.timestamp = time.time()
        
        # 验证数据符合 schema
        schema.validate_value(data)
    
    def __repr__(self):
        return f"StreamChunk(data={self.data}, timestamp={self.timestamp})"


class Parameter:
    """参数实例"""
    
    def __init__(self, name: str, schema: ParameterSchema):
        """
        初始化参数实例
        
        Args:
            name: 参数名称
            schema: 参数 Schema
        """
        self.name = name
        self.schema = schema
        self.is_streaming = schema.is_streaming
        self.value = None  # 非流式数据存储
        self.stream_queue = None  # 流式队列（运行时创建）
    
    def __repr__(self):
        return f"Parameter(name={self.name}, streaming={self.is_streaming})"

