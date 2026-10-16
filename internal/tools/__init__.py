"""
工具层，包含所有工具的定义
BaseTool: 基础工具类，所有工具都继承自这个类
他规范了工具的定义 明确每一个函数应该干什么
我们规定
name函数 返回该工具的名字
definition函数 返回该工具的定义
execute函数 执行该工具

Registry: 工具注册表，用于注册和获取工具
我们规定
register函数 注册一个工具 如果该工具已存在则覆盖
get_available_tools函数 获取所有已注册的工具
execute函数 执行一个工具

最后new_registry返回一个注册表
"""