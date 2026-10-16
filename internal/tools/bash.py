import json
import subprocess
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
class BashTool(BaseTool):
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
        return "bash"

    def definition(self) -> ToolDefinition:
        """
        工具描述
        """
        return ToolDefinition(
            name=self.name(),
            description="在当前工作区执行任意的 bash 命令。支持链式命令(如 &&)。返回标准输出(stdout)和标准错误(stderr)。",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令",
                    },
                },
                "required": ["command"],
            },
        )

    def execute(self, args: str) -> str:
        """
        工具执行
        :param args: 参数格式 {"command": "bash 命令"}
        """
        try:
            input_args = json.loads(args)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"参数解析失败: {e}") from e
        # 30 秒超时保护，防止模型执行的命令把引擎挂死（对应 Go 的 context.WithTimeout）
        # subprocess.run () 【重点】
        # > 作用：**创建子进程，运行外部程序，等待进程结束，返回执行结果对象**（Python3.5+）
        # > 对比老 API：替代 `subprocess.call/check_output`，现在推荐首选。
        # 参数逐个解释
        # 1. `["bash", "-c", input_args.get("command", "")]`
        #    - 列表形式：子进程执行的命令 + 参数
        #    - `bash -c "xxx"`：启动 bash，把后面字符串当做 shell 脚本执行。
        #    >
        #    > 好处：支持管道`|`、重定向`>`、通配符`*`、&& 等 shell 语法；
        #    > 风险：如果 command 来自外部用户输入，**会有命令注入漏洞！**
        #    - `input_args.get("command", "")`：从字典`input_args`拿 key=`command`的值，取不到就默认为空字符串。
        # 2. `cwd=self.work_dir`
        #    - cwd = current working directory
        #    - **子进程的工作目录**：命令执行的时候，相当于`cd`到这个目录再跑命令。
        #    - 比如 work_dir = `/tmp/task`，命令里写 `ls` 就会列出 `/tmp/task` 的文件。
        # 3. `capture_output=True`
        #    - 捕获 stdout（标准输出） 和 stderr（标准错误输出）
        #    - 等价于同时设置 `stdout=subprocess.PIPE, stderr=subprocess.PIPE`
        #    - 如果不开启，程序输出会直接打印到主程序终端，代码拿不到输出文本。
        # 4. `text=True`
        # > 别名 `universal_newlines=True`
        #    - 让 stdout /stderr **直接返回字符串 str，而不是原始 bytes 字节**
        #    - 自动处理换行符转换；省去手动 `.decode()`。
        # 5. `timeout=30`
        #    - **最多等待 30 秒**。如果子进程 30 秒内没跑完，Python 直接杀掉这个子进程，抛出 `subprocess.TimeoutExpired` 异常
        try:
            #  subprocess.run(
            #     ["bash", "-c", input_args.get("command", "")] 注意这么写是有bug的
            #     # 这个工具在调用 subprocess.run(["bash", "-c", ...])，意思是「用 bash 来执行命令」
            #     # 但是windows上默认没有bash这个可执行文件
            #     # Python 找不到 bash，于是抛出了 FileNotFoundError: [WinError 2] 系统找不到指定的文件
            #     # 因此我们采用跨平台写法，使用 shell=True 让他自适应 交给系统默认的shell执行
            #     cwd=self.work_dir,
            #     capture_output=True,
            #     text=True,
            #     timeout=30,)
            proc = subprocess.run(
                input_args.get("command", ""),
                shell=True,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as e:
            # stdout/stderr 合并输出（对应 Go 的 CombinedOutput）
            # `subprocess.TimeoutExpired`：**超时触发的异常**
            # 触发条件：子进程运行超过 timeout 设置的 30 秒。
            # > 重要特性：超时被杀死时，**已经产生的 stdout/stderr 会保留在异常对象 e 里面**，不会全部丢失。
            # - `e.stdout`：超时前已经打印的标准输出
            # - `e.stderr`：超时前已经打印的标准错误
            # - `(e.stdout or "")`：如果是 None，就替换为空字符串，防止拼接报错
            partial = (e.stdout or "") + (e.stderr or "")
            # - `isinstance(partial, bytes)`：兼容判断。
            # > 虽然上面 `text=True` 一般是字符串，但写这个判断是防御性代码，万一某些场景返回 bytes。
            # - `.decode("utf-8", errors="replace")`：字节转字符串，遇到无法解码的字符直接替换成 �，不会抛出解码崩溃。
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", errors="replace")
            # - return：返回**已经收集到的部分输出 + 超时警告**。
            return partial + "\n[警告: 命令执行超时(30s)，已被系统强制终止。]"
        # `proc` 是 subprocess.CompletedProcess 对象（命令正常结束后返回的实例）
        # - `proc.stdout`：命令正常打印的输出（stdout）
        # - `proc.stderr`：命令报错打印的信息（stderr）
        # - 把**正常输出 + 错误输出合并成一个字符串**，这就是终端上你看到的全部内容
        output_str = proc.stdout + proc.stderr
        # - `proc.returncode`：**进程退出码**
        # - Unix/Linux 习惯：`0 = 执行成功`；非 0 = 程序报错、异常退出
        # 例如：`ls 不存在的文件`，returncode 一般是 2
        # - 如果不等于 0，返回提示文本，带上退出码 + 全部输出
        if proc.returncode != 0:
            return f"执行报错: exit status {proc.returncode}\n输出:\n{output_str}"
        # 命令执行成功（returncode=0），但是 stdout 和 stderr 都没有任何内容，返回提示文字。
        if output_str == "":
            return "命令执行成功，无终端输出。"
        # 命令执行成功（returncode=0），并且有输出内容，返回输出内容。
        MAX_LEN = 8000
        if len(output_str) > MAX_LEN:
            return f"{output_str[:MAX_LEN]}\n\n...[终端输出过长，已截断至前 {MAX_LEN} 字节]..."
        return output_str