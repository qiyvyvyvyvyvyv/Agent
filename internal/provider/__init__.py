"""
interface主要规范我们应该在哪一个方法函数内调用大模型

openai interface实现类 是真正实现了如何调用大模型的接口
openai.py中有函数可以帮助我们初始化接口实现 既new_zhipu_openai_provider
在后续我们可以根据用户传入的模型名字获取不同的大模型实现类去调用不同的大模型
generate函数就是调用大模型的接口
他会把我们agent/harness中的消息列表转换成大模型需要的格式
发送给大模型
然后把大模型返回的结果转换成我们agent/harness需要的格式
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
