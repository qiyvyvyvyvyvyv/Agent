"""
工具注册中心接口
"""
from abc import ABC, abstractmethod
from internal.schema.message import ToolCall, ToolDefinition, ToolResult


class Registry(ABC):
    """
        工具注册中心接口类
    """
    @abstractmethod
    def get_available_tools(self) -> list[ToolDefinition]:
        """
            :return: 可用工具列表(获取当前所有注册好、可以交给大模型使用的工具清单)
        """
    @abstractmethod
    def execute(self, call: ToolCall) -> ToolResult:
        """
            :param call: 工具调用请求
            :return: 工具执行结果
        """
