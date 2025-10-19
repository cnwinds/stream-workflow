"""参数系统：参数定义、Schema 和验证"""

import time
from typing import Any, Dict, Union


class ParameterSchema:
    """参数结构定义"""
    
    def __init__(self, is_streaming: bool = False, schema: Union[str, dict] = None):
        """
        初始化参数 Schema
        
        Args:
            is_streaming: 是否为流式参数
            schema: 参数结构定义
                    - 简单类型: "string", "integer", "float", "bytes", "boolean", "dict", "list", "any"
                    - 结构体: {"field_name": "type", ...}
        """
        self.is_streaming = is_streaming
        self.schema = schema or {}
    
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
            return self._validate_simple_type(value, self.schema)
        
        if isinstance(self.schema, dict):
            # 字典结构验证
            if not isinstance(value, dict):
                raise ValueError(f"期望字典类型，实际: {type(value).__name__}")
            
            for field_name, field_type in self.schema.items():
                if field_name not in value:
                    raise ValueError(f"缺少必需字段: {field_name}")
                self._validate_simple_type(value[field_name], field_type)
        
        return True
    
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
        return f"ParameterSchema(streaming={self.is_streaming}, schema={self.schema})"
    
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

