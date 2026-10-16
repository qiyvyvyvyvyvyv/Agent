import os
import openai
# from internal.provider.interface import LLMProvider
from internal.schema.message import (Message,ROLE_ASSISTANT,ROLE_SYSTEM,ROLE_USER,ToolCall,ToolDefinition,)
class OpenAIProvider:
    def __init__(self, client: openai.OpenAI, model: str):
        self.client = client
        self.model = model

    """
    OpenAI Chat Completions API 请求示例
        [
            {"role":"system", "content":"你是天气助手"},
            {"role":"user", "content":"北京天气"},
            {
                "role":"assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id":"call_001",
                        "type":"function",
                        "function": {"name":"get_weather","arguments":"{\"city\":\"北京\"}"}
                    }
                ]
            },
            {"role":"tool", "tool_call_id":"call_001", "content":"北京25度晴"}
        ],
        tools=[
            {
                "type":"function",
                "function":{
                    "name":"get_weather",
                    "description":"查询天气",
                    "parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}
                }
            }
        ]
    """


    def generate(self, msgs: list[Message], available_tools: list[ToolDefinition] | None) -> Message:
        # 1. 把内部统一格式的消息翻译为 OpenAI Chat Completions 的格式
        openai_msgs = []
        for msg in msgs:
            # 如果是系统提示词，则直接翻译
            if msg.role == ROLE_SYSTEM:
                openai_msgs.append({"role": "system", "content": msg.content})
            # 如果是用户提示词，则需要判断是否是工具调用结果
            elif msg.role == ROLE_USER:
                if msg.tool_call_id != "":
                    # 工具执行结果在 OpenAI 协议中是独立的 "tool" 角色消息
                    openai_msgs.append({"role": "tool","content": msg.content,"tool_call_id": msg.tool_call_id,})
                else:
                    # 普通用户消息
                    openai_msgs.append({"role": "user", "content": msg.content})
            # 如果是大模型消息，则需要判断是否是工具调用
            elif msg.role == ROLE_ASSISTANT:
                ast_param: dict = {"role": "assistant"}
                # 如果有内容，则添加 content 字段
                if msg.content != "":
                    ast_param["content"] = msg.content
                # 如果有工具调用，则添加 tool_calls 字段
                if len(msg.tool_calls) > 0:
                    tool_calls = []
                    for tc in msg.tool_calls:
                        tool_calls.append({"id": tc.id,"type": "function","function": {"name": tc.name,
                                # OpenAI 协议中 arguments 本身就是 JSON 字符串
                                "arguments": tc.arguments,},})
                    ast_param["tool_calls"] = tool_calls
                openai_msgs.append(ast_param)
        # 2. 翻译工具为 function tool 格式
        openai_tools = []
        for tool_def in available_tools or []:
            params_schema = tool_def.input_schema \
                if isinstance(tool_def.input_schema, dict) else {}
            openai_tools.append({
                    "type": "function",
                    "function": {
                        "name":tool_def.name,
                        "description": tool_def.description,
                        "parameters": params_schema,
                    }
                })
        # 封装请求参数
        params = {"model": self.model, "messages": openai_msgs, }
        if openai_tools:
            params["tools"] = openai_tools
        try:
            # DeepSeek 思考模式（thinking mode）默认开启；开启时多轮工具调用必须把 reasoning_content
            # 回传给 API，否则返回 400。这里对 DeepSeek 模型显式关闭思考模式，避免处理 reasoning_content。
            # extra_body 是 OpenAI SDK 的专用参数，会原样合并进请求体。
            extra_body = None
            if "deepseek" in self.model:
                extra_body = {"thinking": {"type": "disabled"}}
            resp = self.client.chat.completions.create(**params, extra_body=extra_body)
        except Exception as e:
            raise RuntimeError(f"OpenAI/Zhipu API 请求失败: {e}") from e
        if len(resp.choices) == 0:
            raise RuntimeError("API 返回了空的 Choices")
        # 3. 把模型响应翻译回内部统一格式(非流式)
        choice = resp.choices[0].message
        result_msg = Message(role=ROLE_ASSISTANT, content=choice.content or "", )
        for tc in choice.tool_calls or []:
            if tc.type == "function":
                result_msg.tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments, ))
        return result_msg

def new_zhipu_openai_provider(model: str) -> OpenAIProvider:
    """
    创建一个 OpenAIProvider 实例
    :param model:
    :return:
    """
    return OpenAIProvider(
        client=openai.OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'),base_url="https://api.deepseek.com"),
        model="deepseek-flash" )