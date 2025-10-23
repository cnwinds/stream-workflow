"""输出节点"""

import json
from typing import Any
from workflow_engine.core import Node, ParameterSchema, WorkflowContext, register_node

@register_node('output_node')
class OutputNode(Node):
    """
    输出节点
    
    功能：用于输出工作流的最终结果
    
    输入参数：
        input_data: 输入数据（可选，可以从配置文件或输入获取）
            - data: any - 要输出的数据
            - format: string - 输出格式
            - save_to_file: boolean - 是否保存到文件
            - file_path: string - 文件路径
    
    输出参数：
        output: 输出结果
            - result: any - 输出结果
            - format: string - 使用的输出格式
            - saved: boolean - 是否已保存到文件
            - file_path: string - 保存的文件路径（如果保存）
    
    配置参数：
        format: string - 输出格式（json, text, raw）
        save_to_file: boolean - 是否保存到文件
        file_path: string - 文件路径
    """
    
    # 节点执行模式：顺序执行，任务驱动
    EXECUTION_MODE = 'sequential'
    
    # 定义输入输出参数结构
    INPUT_PARAMS = {
        "input_data": ParameterSchema(
            is_streaming=False,
            schema={
                "data": "any",
                "format": "string",
                "save_to_file": "boolean",
                "file_path": "string"
            }
        )
    }
    
    OUTPUT_PARAMS = {
        "output": ParameterSchema(
            is_streaming=False,
            schema={
                "result": "any",
                "format": "string",
                "saved": "boolean",
                "file_path": "string"
            }
        )
    }
    
    async def run(self, context: WorkflowContext) -> Any:
        """
        执行输出操作
        
        配置参数:
            - format: 输出格式（json, text, raw）
            - save_to_file: 是否保存到文件
            - file_path: 文件路径
        """
        # 1. 从配置文件获取默认值（使用简化的 get_config 方法）
        output_format = self.get_config('config.format') or self.get_config('format', 'raw')
        save_to_file = self.get_config('config.save_to_file', self.get_config('save_to_file', False))
        file_path = self.get_config('config.file_path') or self.get_config('file_path')
        
        # 2. 尝试从输入参数获取（覆盖配置）
        try:
            input_data = self.get_input_value('input_data')
            if input_data:
                data = input_data.get('data')
                output_format = input_data.get('format', output_format)
                save_to_file = input_data.get('save_to_file', save_to_file)
                file_path = input_data.get('file_path', file_path)
        except (ValueError, KeyError):
            # 没有输入参数，使用配置文件的值
            pass
        
        # 3. 获取要输出的数据
        if 'data' in locals() and data is not None:
            # 使用输入参数中的数据
            output_data = data
        else:
            # 使用旧架构的输入数据（向后兼容）
            input_data = self.get_input_data(context)
            
            # 合并所有输入
            if len(input_data) == 1:
                output_data = list(input_data.values())[0]
            else:
                output_data = {}
                for node_id, data in input_data.items():
                    output_data[node_id] = data
        
        # 4. 格式化输出
        if output_format == 'json':
            formatted_output = json.dumps(output_data, indent=2, ensure_ascii=False)
        elif output_format == 'text':
            formatted_output = str(output_data)
        else:  # raw
            formatted_output = output_data
        
        # 5. 打印输出
        context.log_info("=" * 50)
        context.log_info("工作流输出:")
        context.log_info(str(formatted_output))
        context.log_info("=" * 50)
        
        # 6. 保存到文件
        saved = False
        if save_to_file and file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if isinstance(formatted_output, str):
                        f.write(formatted_output)
                    else:
                        json.dump(formatted_output, f, indent=2, ensure_ascii=False)
                context.log_info(f"输出已保存到文件: {file_path}")
                saved = True
            except Exception as e:
                context.log_error(f"保存文件失败: {str(e)}")
                saved = False
        
        # 7. 设置输出值
        self.set_output_value('output', {
            'result': output_data,
            'format': output_format,
            'saved': saved,
            'file_path': file_path if saved else None
        })
        
        return {
            'result': output_data,
            'format': output_format,
            'saved': saved,
            'file_path': file_path if saved else None
        }
