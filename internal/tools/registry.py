"""
工具注册中心接口
"""
import logging
from abc import ABC, abstractmethod
from internal.schema.message import ToolCall, ToolDefinition, ToolResult
log = logging.getLogger(__name__)
class BaseTool(ABC):
    """
    所有工具必须实现的基础接口（对应 Go 的 BaseTool interface）
    """
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def definition(self) -> ToolDefinition:
        ...

    @abstractmethod
    def execute(self, args: str) -> str:
        """
        args 为原始 JSON 字符串，由工具自行解析；执行失败时抛出异常（对应 Go 的返回 error）
        """

class Registry(ABC):
    """工具注册中心接口"""
    @abstractmethod
    def register(self, tool: BaseTool):
        ...

    @abstractmethod
    def get_available_tools(self) -> list[ToolDefinition]:
        ...

    @abstractmethod
    def execute(self, call: ToolCall) -> ToolResult:
        ...

class RegistryImpl(Registry):
    """
    Registry 的默认实现：内部用一个 dict 存储 名称 -> 工具实例 的映射
    """
    def __init__(self):
        self.tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """
        注册工具
        :param tool: 工具类
        :return:
        """
        name = tool.name()
        if name in self.tools:
            log.info("[Warning] 工具 '%s' 已经被注册，将被覆盖。", name)
        self.tools[name] = tool
        log.info("[Registry] 成功挂载工具: %s", name)


    def get_available_tools(self) -> list[ToolDefinition]:
        """
        获取所有已注册工具的定义
        :return: 已注册工具的定义列表
        """
        return [tool.definition() for tool in self.tools.values()]

    def execute(self, call: ToolCall) -> ToolResult:
        """
        执行工具
        :param call: 工具调用请求
        :return: 工具执行结果
        """
        tool = self.tools.get(call.name)
        if tool is None:
            err_msg = f"Error: 系统中不存在名为 '{call.name}' 的工具。"
            return ToolResult(
                tool_call_id=call.id,
                output=err_msg,
                is_error=True,
            )
            # 统一的异常兜底：工具内部抛出的任何异常都转换为 is_error 的观察结果，
            # 反馈给模型让它自行纠错，而不是让整个引擎崩溃。
        try:
            output = tool.execute(call.arguments)
        except Exception as e:
            return ToolResult(
                tool_call_id=call.id,
                output=f"Error executing {call.name}: {e}",
                is_error=True,
            )
        return ToolResult(
            tool_call_id=call.id,
            output=output,
            is_error=False,
        )

def new_registry() -> Registry:
    """
    对应 Go 版的 NewRegistry 构造函数
    """
    return RegistryImpl()

# class Registry(ABC):
#     """
#         工具注册中心接口类
#     """
#     @abstractmethod
#     def get_available_tools(self) -> list[ToolDefinition]:
#         """
#             :return: 可用工具列表(获取当前所有注册好、可以交给大模型使用的工具清单)
#         """
#     @abstractmethod
#     def execute(self, call: ToolCall) -> ToolResult:
#         """
#             :param call: 工具调用请求
#             :return: 工具执行结果
#         """
