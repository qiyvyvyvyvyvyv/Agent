"""
    Mock 模型
"""
import os
import sys
from internal.engine.loop import AgentEngine
from internal.provider.openai import new_zhipu_openai_provider
from internal.tools.read_file import ReadFileTool
from internal.tools.registry import new_registry
from internal.tools.write_file import WriteFileTool
from internal.tools.bash import BashTool
from internal.tools.edit_file import EditFileTool

# 日志配置
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
datefmt="%Y/%m/%d %H:%M:%S")

def main():
    work_dir = os.getcwd()
    llm_provider = new_zhipu_openai_provider("deepseek-flash")
    registry = new_registry()
    registry.register(WriteFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(ReadFileTool(work_dir))
    registry.register(EditFileTool(work_dir))
    eng = AgentEngine(llm_provider, registry, work_dir, False)
    prompt = """
    我当前目录下有一个 server.py 文件。
    请帮我把里面 "TODO: 增加鉴权逻辑" 下面的那个 if 语句，整个替换为：
    if user is None:
        print("Forbidden!")
        return
    """
    try:
        eng.run(prompt)
    except Exception as e:
        sys.exit(f"引擎运行崩溃: {e}")

if __name__ == "__main__":
    main()