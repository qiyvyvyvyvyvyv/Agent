"""
    Agent 引擎
"""
from internal.provider.interface import LLMProvider
from internal.provider.openai import OpenAIProvider
from internal.schema.message import Message, ROLE_SYSTEM, ROLE_USER
from internal.tools.registry import Registry

"""
    logging模块解释
    - logging 是 Python 内置标准日志库，用来替代print打印程序运行信息（INFO、WARN、ERROR 等日志）。
    - getLogger(name)：获取一个日志器（logger）实例，name 是日志器的名称，通常使用 __name__。
    - setLevel(level)：设置日志级别，level 可以是 DEBUG、INFO、WARN、ERROR 等。
    为什么规范写法要用 getLogger(__name__)，而不是直接 logging.info()
    - 区分日志来源
    注意事项
    getLogger(__name__) 只是拿到 logger 对象，不等于自动开启日志
    如果你只写这一行，不做 logging 基础配置，默认只会输出 WARNING 及以上级别日志，INFO 日志默认不会打印出来
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )
"""
import logging
log = logging.getLogger(__name__)

class AgentEngine:
    """Agent 引擎：持有 Provider(大脑) 与 Registry(手脚)，并锁定一个工作区目录。"""
    def __init__(self, provider: OpenAIProvider, registry: Registry, work_dir: str, enable_thinking: bool):
        self.provider = provider                # 大脑
        self.registry = registry                # 工具注册表
        self.work_dir = work_dir                # 工作区目录
        self.enable_thinking = enable_thinking  # 是否启用思考模式

    def run(self, user_prompt: str) -> None:
        log.info("[Engine] 引擎启动，锁定工作区: %s", self.work_dir)
        log.info("[Engine] 慢思考模式 (Thinking Phase): %s", self.enable_thinking)
        context_history: list[Message] = [Message(
            role=ROLE_SYSTEM,content="You are py-tiny-claw, an expert coding assistant. You have fullaccess to tools in theworkspace.",),
            Message(role=ROLE_USER,content=user_prompt,),]
        # 轮数计数器
        turn_count = 0
        while True:
            turn_count += 1
            log.info("\n========== [Turn %d] 开始 ==========", turn_count)
            # 获取可用工具
            available_tools = self.registry.get_available_tools()
            # ================= Phase 1: 慢思考 =================
            if self.enable_thinking:
                log.info("[Engine][Phase 1] 剥夺工具访问权，强制进入慢思考与规划阶段...")
                try:
                    # 传入 None 剥夺工具
                    think_resp = self.provider.generate(context_history, None)
                except Exception as e:
                    raise RuntimeError(f"Thinking 阶段生成失败: {e}") from e
                if think_resp.content != "":
                    print(f"🧠 [内部思考 Trace]: {think_resp.content}")
                    # 将思考内容添加到上下文历史
                    context_history.append(think_resp)
            # ================= Phase 2: 行动 =================
            log.info("[Engine][Phase 2] 恢复工具挂载，等待模型采取行动...")
            try:
                action_resp = self.provider.generate(context_history, available_tools)
            except Exception as e:
                raise RuntimeError(f"Action 阶段生成失败: {e}") from e
            # 将行动内容添加到上下文历史
            context_history.append(action_resp)
            if action_resp.content != "":
                print(f"🤖 [对外回复]: {action_resp.content}")
            # ================= 执行判断 =================
            if len(action_resp.tool_calls) == 0:
                log.info("[Engine] 模型未请求调用工具，任务宣告完成。")
                break
            log.info("[Engine] 模型请求调用 %d 个工具...", len(action_resp.tool_calls))
            for tool_call in action_resp.tool_calls:
                log.info("  -> 🛠️ 执行工具: %s, 参数: %s", tool_call.name,
                         tool_call.arguments)
                result = self.registry.execute(tool_call)
                if result.is_error:
                    log.info("  -> ❌ 工具执行报错: %s", result.output)
                else:
                    log.info("  -> ✅ 工具执行成功 (返回 %d 字节)", len(result.output))
                observation_msg =Message(role=ROLE_USER, content=result.output, tool_call_id=tool_call.id, )
                # 将工具执行结果添加到上下文历史
                context_history.append(observation_msg)
