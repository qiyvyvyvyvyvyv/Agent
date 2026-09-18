"""
    Mock 模型
"""
import os
import sys
from internal.engine.loop import AgentEngine
from internal.provider.interface import LLMProvider
from internal.schema.message import (Message,ROLE_ASSISTANT,ToolCall,ToolResult,
)
from internal.tools.registry import Registry

# 日志配置
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
datefmt="%Y/%m/%d %H:%M:%S")

class MockProvider(LLMProvider):
    """假模型：第一轮固定要求调用 bash 工具，第二轮宣布任务完成。"""
    def __init__(self):
        self.turn = 0
    def generate(self, msgs, tools):
        # 没有工具可用 => 处于 Thinking 阶段，只输出规划文本
        if tools is None :
            return Message(role=ROLE_ASSISTANT,
                           content="【推理中】目标是检查文件。我不能直接盲猜，我需要先调用 bash 工具执行 ls 命令，看看当前目录下有什么，然后再做定夺。",)
        self.turn += 1
        if self.turn == 1:
            return Message(role=ROLE_ASSISTANT,content="我要执行我刚才计划的步骤了。",tool_calls=[ToolCall(id="call_123", name="bash", arguments='{"command": "ls -la"}'),],)
        return Message(role=ROLE_ASSISTANT,content="根据工具返回的结果，我看到了 main.py，任务圆满完成！",)

class MockRegistry(Registry):
    """假工具箱：无论调用什么工具都返回一份固定的 ls 输出。"""
    def get_available_tools(self):
        return []
    def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(tool_call_id=call.id,output="-rw-r--r--  1 user group  234 Oct 24 10:00 main.py\n",is_error=False,)

def main():
    work_dir = os.getcwd()
    p = MockProvider()
    r = MockRegistry()
    eng = AgentEngine(p, r, work_dir, True)
    try:
        eng.run("帮我检查当前目录的文件")
    except Exception as e:
        sys.exit(f"引擎崩溃: {e}")
if __name__ == "__main__":
    main()