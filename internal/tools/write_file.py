import json
import os
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
class WriteFileTool(BaseTool):
    def __init__(self, work_dir: str):
        """
        工具初始化
        :param work_dir: 工作区
        """
        self.work_dir = work_dir

    def name(self) -> str:
        """
        工具名称
        """
        return "write_file"

    def definition(self) -> ToolDefinition:
        """
        工具描述
        """
        return ToolDefinition(
            name=self.name(),
            description="创建或覆盖写入一个文件。如果目录不存在会自动创建。请提供相对于工作区的相对路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件路径，如 src/main.py",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的完整文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        )

    def execute(self, args: str) -> str:
        """
        工具执行
        :param args: 参数
        :return: 返回结果
        """
        try:
            input_args = json.loads(args)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"参数解析失败: {e}") from e
        path = input_args.get("path", "")
        content = input_args.get("content", "")
        # 拼接工作区路径和文件路径
        full_path = os.path.join(self.work_dir, path)
        # 自动创建父目录（对应 Go 的 os.MkdirAll）
        try:
            # 作用：创建 `full_path` 文件所在的目录（多级目录），目录已存在也不会报错。**
            # 1. `os.path.dirname(full_path)`
            # 拿到**文件路径里的目录部分**。
            # > 例子：`full_path = "/data/log/run.txt"`
            # > `os.path.dirname(full_path)` → `"/data/log"`
            # > ⚠️ 注意：它**不会创建 run.txt 这个文件**，只处理文件夹。
            # 2. `os.makedirs(path, exist_ok=True)`
            # `os.makedirs` = **递归创建多层目录**（可以一次性创建多级嵌套文件夹）
            # - `exist_ok=True`：如果这个目录**已经存在，不抛异常，直接跳过**
            # - 如果不加 `exist_ok=True`，目录已存在时会抛出 `FileExistsError`
            # > 对比：`os.mkdir()` 只能创建**单级目录**，上级目录不存在就报错；`makedirs` 可以一口气建好所有上级文件夹。
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"创建父目录失败: {e}") from e
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            raise RuntimeError(f"写入文件失败: {e}") from e
        return f"成功将内容写入到文件: {path}"