import json
import os
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
class EditFileTool(BaseTool):
    def __init__(self, work_dir: str):
        """
        指定工作目录
        :param work_dir: 工作目录
        """
        self.work_dir = work_dir

    def name(self) -> str:
        """
        返回工具名称
        :return: 工具名称
        """
        return "edit_file"

    def definition(self) -> ToolDefinition:
        """
        返回工具描述
        :return: 工具描述
        """
        return ToolDefinition(
            name=self.name(),
            description="对现有文件进行局部的字符串替换。这比重写整个文件更安全、更快速。请提供足够的 old_text 上下文以确保匹配的唯一性。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要修改的文件路径",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "文件中原有的文本。必须包含足够的上下文，以确保在文件中的唯一性。",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "要替换成的新文本",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        )

    def execute(self, args: str) -> str:
        """
        执行工具
        :param args: 参数格式 {"path": "文件路径", "old_text": "原有文本", "new_text": "新文本"}
        :return: 返回结果
        """
        try:
            input_args = json.loads(args)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"参数解析失败: {e}") from e
        # 拼接路径
        path = input_args.get("path", "")
        old_text = input_args.get("old_text", "")
        new_text = input_args.get("new_text", "")
        full_path = os.path.join(self.work_dir, path)
        # 先把文件内容读取出来
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except OSError as e:
            raise RuntimeError(f"读取文件失败，请确认路径是否正确: {e}") from e
        # 进行模糊匹配替换
        new_content = fuzzy_replace(original_content, old_text, new_text)
        # 将修改后的内容写回文件
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except OSError as e:
            raise RuntimeError(f"写回文件失败: {e}") from e
        return f"✅ 成功修改文件: {path}"

def fuzzy_replace(original_content: str, old_text: str, new_text: str) -> str:
    """
    精确匹配(L1) → 失败则 → 换行符归一化匹配(L2) → 失败则 → 去首尾空白匹配(L3) → 失败则 → 逐行去缩进匹配(L4)
    每一级只要匹配到「多处」，直接报错要求补充上下文；匹配到「1处」则执行替换；0处才进入下一级。
    :param original_content: 原文内容
    :param old_text: 要匹配的旧文本
    :param new_text: 要替换的新文本
    :return: 替换后的内容
    """
    # TODO L1: 精确匹配
    # 逻辑：大模型给出的old_text完全按原始字符发来 可以逐字匹配，是最理想的匹配状态。
    # 设计：匹配到 1 处则直接替换（只替换 1 次）；匹配到多处直接报错，不继续降级。
    # 目的：优先保证替换的绝对准确性，避免模糊匹配带来的误替换风险
    # 匹配要替换的旧文本，返回匹配到的次数
    count = original_content.count(old_text)
    if count == 1:
        # 如果只匹配到一处 那么就是正常的 直接替换即可
        return original_content.replace(old_text, new_text, 1)
    if count > 1:
        # 如果匹配到多处 则要求补充上下文
        # raise：Python 关键字，用于主动抛出一个异常，让程序停止当前逻辑，把错误原因抛给调用者。
        # RuntimeError：Python 内置的标准异常类型，代表「运行时逻辑错误」，属于通用的业务逻辑异常。
        # f"old_text 匹配到了 {count} 处，请提供更多的上下文代码以确保唯一性"：具体的错误提示信息，{count} 会被替换成实际匹配到的数量。
        raise RuntimeError(f"old_text 匹配到了 {count} 处，请提供更多的上下文代码以确保唯一性")
    # TODO L2: 换行符归一化
    # 优先考虑换行符问题
    # 逻辑：把 Windows 风格的换行符 \r\n 统一替换成 Unix/Linux 风格的 \n，再进行匹配。这样可以避免换行符差异导致的匹配失败。
    # 为什么需要这一级？
    # 不同操作系统、编辑器的换行符标准不一致：
    # Windows 用 \r\n，Linux/macOS/ 多数代码编辑器用 \n。肉眼看起来完全一样的代码，实际字符串不相等，精确匹配会失败。
    # 归一化后可以解决跨平台复制代码、不同编辑器保存导致的换行符差异问题
    # 到这里说明count=0 第一步精准匹配没有匹配到
    normalized_content = original_content.replace("\r\n", "\n")
    # 保险起见，把 old_text 也进行换行符归一化
    normalized_old = old_text.replace("\r\n", "\n")
    # 再次匹配
    count = normalized_content.count(normalized_old)
    if count == 1:
        # 成功匹配到一处
        return normalized_content.replace(normalized_old, new_text, 1)
    # TODO L3: Trim Space 匹配
    # 逻辑：对 old_text 去除首尾所有空白（空格、换行、制表符），再在归一化后的原文中匹配 由于前面已经去除了换行符，这里直接复用归一化后的结果
    # 细节：加了 trimmed_old != "" 的判断，避免 old_text 全是空白时，空字符串匹配到无数位置的异常。
    # 为什么需要这一级？
    # 从网页、聊天框、PDF 中复制代码时，经常会带上首尾多余的空格、空行；
    # AI 生成的代码片段也常带有首尾空白。肉眼无法察觉，但精确匹配会失败。去除首尾空白后可以容忍这类格式误差
    # 到这里有两种情况 count=0或者count>1
    trimmed_old = normalized_old.strip()
    if trimmed_old != "":
        count = normalized_content.count(trimmed_old)
        # 如果只匹配到一处 那么就是正常的 直接替换即可
        if count == 1:
            return normalized_content.replace(trimmed_old, new_text, 1)
    # TODO L4: 逐行去缩进匹配
    # 当前三级都匹配失败时，进入最宽松的逐行匹配，专门解决缩进不一致问题，由辅助函数实现
    return line_by_line_replace(normalized_content, normalized_old, new_text)

def line_by_line_replace(content: str, old_text: str, new_text: str) -> str:
    """
    逐行去缩进匹配
    :param content: 原文内容
    :param old_text: 要匹配的旧文本
    :param new_text: 要替换的新文本
    :return: 替换后的内容
    """
    # 第一步：把原文和待匹配文本都按换行符拆成「行列表」
    content_lines = content.split("\n")
    old_lines = old_text.strip().split("\n")
    # 如果出现 old_text 比 content 还长，直接失败 或者 old_text 为空，也直接失败
    if len(old_lines) == 0 or len(content_lines) < len(old_lines):
        raise RuntimeError("找不到该代码片段")
    # 每一行都去掉首尾空白后再比较，容忍模型给出的缩进偏差 只保留代码内容本身
    old_lines = [line.strip() for line in old_lines]
    match_count = 0
    match_start_index = -1
    match_end_index = -1
    # 朴素字符串比较算法
    for i in range(len(content_lines) - len(old_lines) + 1):
        # 标记是否匹配成功
        is_match = True
        for j in range(len(old_lines)):
            if content_lines[i + j].strip() != old_lines[j]:
                is_match = False
                break
        if is_match:
            match_count += 1
            match_start_index = i
            match_end_index = i + len(old_lines)
    if match_count == 0:
        raise RuntimeError("在文件中未找到 old_text，请检查内容和缩进")
    if match_count > 1:
        raise RuntimeError(f"模糊匹配到了 {match_count} 处代码，请提供更多上下文以定位")
    # 执行替换前，先提取匹配块第一行的基础缩进（Base Indentation）
    # 例：匹配块第一行是 '            def foo():'，则 base_indent = 12 空格
    base_indent = _leading_whitespace(content_lines[match_start_index])
    # 把 base_indent 补齐到 new_text 的每一行（同时抹掉模型自带的错误缩进）
    reindented_new_text = _reindent(new_text, base_indent)
    # 执行替换：把匹配到的连续多行，整体替换成 reindented_new_text（注意是整块替换，不是逐行替换），注意这里的new_content_lines是列表
    new_content_lines = (
            content_lines[:match_start_index]
            + [reindented_new_text]
            + content_lines[match_end_index:]
    )
    # "\n".join(new_content_lines)这一步的意思是 把每相邻的两个元素用换行符连接起来，生成一个新的字符串
    return "\n".join(new_content_lines)


def _leading_whitespace(line: str) -> str:
    """
    提取一行的前导空白（空格 / 制表符）。
    原理：len(line) - len(line.lstrip()) = 前导空白的长度。
    例：'            def foo():' -> '            '（12 空格）
    """
    return line[: len(line) - len(line.lstrip())]


def _common_indent(lines: list[str]) -> str:
    """
    计算一组非空行「公共的最小前导缩进」，即 new_text 自带的缩进基准。
    例：['    def foo():', '        x = 1'] -> '    '（4 空格）
    细节：只统计非空行，空行不参与，否则会把公共缩进误算成 ''。
    """
    indents = [_leading_whitespace(l) for l in lines if l.strip() != ""]
    if not indents:
        return ""
    common = indents[0]
    for ind in indents[1:]:
        # 逐字符收敛到共同前缀（比 min(len) 更严谨，能处理空格/制表符混用）
        while not ind.startswith(common):
            common = common[:-1]
        if common == "":
            break
    return common


def _reindent(new_text: str, base_indent: str) -> str:
    """
    把 new_text 的缩进统一对齐到 base_indent：
    1. 算出 new_text 自带的最小公共缩进 own_indent；
    2. 每行去掉 own_indent（抹掉模型给的错误缩进基准）；
    3. 再统一补上文件里的 base_indent。
    结果：既修正了「绝对缩进层级」，又保留 new_text 内部「相对缩进」结构。
    空行原样保留，避免产生多余的行尾空格。
    """
    lines = new_text.split("\n")
    own_indent = _common_indent(lines)
    fixed_lines = []
    for line in lines:
        if line.strip() == "":
            fixed_lines.append(line)             # 空行不动
            continue
        if own_indent and line.startswith(own_indent):
            line = line[len(own_indent):]        # 先去掉自带的缩进基准
        fixed_lines.append(base_indent + line)   # 再补上文件的基础缩进
    return "\n".join(fixed_lines)