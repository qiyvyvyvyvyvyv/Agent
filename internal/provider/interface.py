"""
规范所有大模型服务商（OpenAI / 通义千问 / DeepSeek 等）的调用代码，
不管换哪个模型，上层业务调用方式不变
"""
from abc import ABC, abstractmethod
from internal.schema.message import Message, ToolDefinition
"""
    1. ABC：Python 抽象基类，用来做接口定义
    2. abstractmethod：抽象方法装饰器，标记这个方法**子类必须实现，不能直接实例化父类**
"""

class LLMProvider(ABC):
    """
        LLMProvider 定义了与⼤模型通信的统⼀接⼝
    """
    @abstractmethod
    def generate(self, messages: list[Message],
                 available_tools: list[ToolDefinition] | None) -> Message:
        """
            通信方法
            :param messages: 对话上下文消息列表，包含历史对话（用户消息、之前模型回复、工具返回结果）
            :param available_tools: 可用工具列表
            :return: 模型返回的消息对象，可能是普通文本回答，也可能是工具调用请求（tool_call）
        """