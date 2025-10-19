"""输出节点"""

import json
from typing import Any
from workflow_engine.core import Node, WorkflowContext


class OutputNode(Node):
    """
    输出节点
    用于输出工作流的最终结果
    """
    
    def execute(self, context: WorkflowContext) -> Any:
        """
        执行输出操作
        
        配置参数:
            - format: 输出格式（json, text, raw）
            - save_to_file: 是否保存到文件
            - file_path: 文件路径
        """
        output_format = self.config.get('format', 'raw')
        save_to_file = self.config.get('save_to_file', False)
        file_path = self.config.get('file_path')
        
        # 获取输入数据
        input_data = self.get_input_data(context)
        
        # 合并所有输入
        if len(input_data) == 1:
            output_data = list(input_data.values())[0]
        else:
            output_data = {}
            for node_id, data in input_data.items():
                output_data[node_id] = data
        
        # 格式化输出
        if output_format == 'json':
            formatted_output = json.dumps(output_data, indent=2, ensure_ascii=False)
        elif output_format == 'text':
            formatted_output = str(output_data)
        else:  # raw
            formatted_output = output_data
        
        # 打印输出
        context.log("=" * 50)
        context.log("工作流输出:")
        context.log(str(formatted_output))
        context.log("=" * 50)
        
        # 保存到文件
        if save_to_file and file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if isinstance(formatted_output, str):
                        f.write(formatted_output)
                    else:
                        json.dump(formatted_output, f, indent=2, ensure_ascii=False)
                context.log(f"输出已保存到文件: {file_path}")
            except Exception as e:
                context.log(f"保存文件失败: {str(e)}", level="ERROR")
        
        return output_data
