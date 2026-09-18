"""
与大模型通信的协议，定义了请求和响应的格式
"""
from dataclasses import dataclass, field

"""角色定义"""
ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

"""
    部分代码解释
        - @dataclass：
        Python 装饰器，用来快速定义数据载体类（DTO / 实体类），
        自动生成 `__init__`、`__repr__`，专门用来存数据，不写复杂业务逻辑。
        - field(default_factory=list)：
        设置默认空列表。不能直接写 `tool_calls: list[ToolCall] = []`（会有可变对象共享坑）。
    执行流程:
        1. 构造 Message (role=system) + Message (role=user)，送入模型
        2. 模型返回 assistant Message，携带 `tool_calls=[ToolCall]`
        3. 引擎遍历 tool_calls，找到对应 ToolDefinition，执行工具函数
        4. 工具执行完成，产出 ToolResult（成功 / 失败）
        5. 将 ToolResult 转换为一条 user 类型 Message，填充 `tool_call_id`，追加进对话上下文
        6. 把更新后的消息列表再次发给模型，模型读取工具结果，生成最终自然语言回答
"""

@dataclass
class ToolCall:
    """
        一次工具调用请求的数据结构
        id: 工具调用的唯一标识符 工具返回结果的时候必须带上这个 ID 用来配对 告诉模型: 这个结果对应哪一次工具调用
        name: 工具名称
        arguments: 工具调用参数 JSON 格式字符串
        需要注意
        arguments: 是原始JSON字符串，不是dict。引擎不解析，交给对应的工具自己解析，减少序列化损耗。
        arguments 存原始 JSON 字符串，引擎层就不用做「JSON 字符串 → Python 字典」这一步反序列化；
        工具拿到之后自己按需解析，省去引擎全局做一次解析的开销，同时避免多余的类型转换，这就是减少序列化损耗。
    """
    id: str = ""
    name: str = ""
    arguments: str = ""

@dataclass
class Message:
    """
        一条上下文消息的数据结构
        role: 角色
        content: 内容
        tool_calls: 工具调用列表
        tool_call_id: 工具调用 ID
        举例:
            - assistant 消息：
            role=assistant,
            tool_calls=[ToolCall(id="call_001", name="weather", arguments='{"city":"北京"}')]
            - 工具执行完，构造 user 消息回传给模型：
            role=user, tool_call_id="call_001", content="北京今天25度"
    """
    role: str = ""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""

@dataclass
class ToolResult:
    """
        一次工具执行的结果
        tool_call_id: 工具调用的唯一标识符
        output: 工具执行结果
        is_error: 根据output判断是否执行出错
    """
    tool_call_id: str = ""
    output: str = ""
    is_error: bool = False

@dataclass
class ToolDefinition:
    """
        工具定义
        name: 工具名称
        description: 工具描述
        input_schema: 工具输入参数的 JSON Schema 约束
        描述工具需要哪些参数、参数类型、是否必填。模型会根据这个 schema 生成 ToolCall中的 arguments 里的 JSON 字符串
    """
    name: str = ""
    description: str = ""
    input_schema: dict | None = None
