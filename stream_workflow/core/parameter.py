"""参数系统：参数定义、Schema 和验证"""

import time
from typing import Any, Dict, Union


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
            # 简单类型验证
            if value is not None:  # 允许 None 值
                return self._validate_simple_type(value, self.schema)
            return True
        
        if isinstance(self.schema, dict):
            # 字典结构验证
            if not isinstance(value, dict):
                raise ValueError(f"期望字典类型，实际: {type(value).__name__}")
            
            for field_name, field_def in self.schema.items():
                # 解析字段定义（支持简单格式和详细格式）
                field_info = self._parse_field_definition(field_def)
                field_type = field_info['type']
                field_required = field_info['required']
                field_description = field_info['description']
                field_default = field_info['default']
                
                # 如果字段不存在，应用默认值（如果有）
                if field_name not in value:
                    if field_default is not None:
                        value[field_name] = field_default
                    elif field_required:
                        # 检查必传字段
                        error_msg = f"缺少必传字段: {field_name}"
                        if field_description:
                            error_msg += f" ({field_description})"
                        raise ValueError(error_msg)
                
                # 如果字段存在，验证类型
                if field_name in value:
                    self._validate_simple_type(value[field_name], field_type)
        
        return True
    
    def _parse_field_definition(self, field_def: Union[str, dict]) -> Dict[str, Any]:
        """
        解析字段定义，支持两种格式：
        1. 简单格式: "string" -> {"type": "string", "required": False, "description": "", "default": None}
        2. 详细格式: {"type": "string", "required": True, "description": "说明", "default": "默认值"}
        
        Args:
            field_def: 字段定义（字符串或字典）
            
        Returns:
            包含 type、required、description、default 的字典
        """
        if isinstance(field_def, str):
            # 简单格式：直接是类型字符串
            return {
                "type": field_def,
                "required": False,
                "description": "",
                "default": None
            }
        elif isinstance(field_def, dict):
            # 详细格式：包含 type、required、description、default
            return {
                "type": field_def.get("type", "any"),
                "required": field_def.get("required", False),
                "description": field_def.get("description", ""),
                "default": field_def.get("default", None)
            }
        else:
            raise ValueError(f"无效的字段定义格式: {field_def}")
    
    def _validate_simple_type(self, value: Any, type_str: str) -> bool:
        """
        验证简单类型
        
        Args:
            value: 要验证的值
            type_str: 类型字符串
            
        Returns:
            验证通过返回 True
            
        Raises:
            TypeError: 类型不匹配
        """
        type_map = {
            'bytes': bytes,
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'dict': dict,
            'list': list,
            'any': object
        }
        
        expected_type = type_map.get(type_str)
        if expected_type and expected_type != object:
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"类型不匹配: 期望 {type_str}, 实际 {type(value).__name__}"
                )
        
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

