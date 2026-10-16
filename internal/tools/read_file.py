import json
import os
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
class ReadFileTool(BaseTool):
    def __init__(self, work_dir: str):
        """
        指定工作目录
        """
        self.work_dir = work_dir


    def name(self) -> str:
        """
        返回工具名称
        """
        return "read_file"


    def definition(self) -> ToolDefinition:
        """
        返回工具描述
        """
        return ToolDefinition(
            name=self.name(),
            description="读取指定路径的文件内容。请提供相对工作区的路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径，如 cmd/claw/main.py",
                    },
                },
                "required": ["path"],
            },
        )


    def execute(self, args: str) -> str:
        """
        执行工具
        :param args: 读取文件的参数，格式为 {"path": "文件路径"}
        :return: 文件内容
        """
        try:
            input_args = json.loads(args)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"参数解析失败: {e}") from e
        full_path = os.path.join(self.work_dir, input_args.get("path", ""))
        try:
            with open(full_path, "rb") as f:
                content = f.read()
        except OSError as e:
            raise RuntimeError(f"打开文件失败: {e}") from e
            # 防御上下文爆炸：超长文件只保留前 8000 字节
        MAX_LEN = 8000
        if len(content) > MAX_LEN:
            truncated_msg = (
                # decode函数解析 由于读出的文件内容是二进制的，需要先解码成utf-8 格式的字符串 然后使用errors='replace'是替换原本内容
                f"{content[:MAX_LEN].decode('utf-8', errors='replace')}"
                f"\n\n...[由于内容过长，已被系统截断至前 {MAX_LEN} 字节]..."
            )
            return truncated_msg
        return content.decode("utf-8", errors="replace")