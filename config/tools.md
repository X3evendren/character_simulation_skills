# 工具定义

## read_file

描述: 读取指定路径的文件内容
参数:
  - path: 文件路径 (必填, string)
  - offset: 起始行号 (选填, int, 默认 0)
  - limit: 读取行数 (选填, int, 默认 2000)
风险等级: low
并发安全: true
只读: true

## write_file

描述: 写入内容到指定文件
参数:
  - path: 文件路径 (必填, string)
  - content: 要写入的内容 (必填, string)
风险等级: medium
并发安全: false
只读: false

## edit_file

描述: 精确替换文件中的字符串
参数:
  - path: 文件路径 (必填, string)
  - old_string: 要替换的文本 (必填, string)
  - new_string: 替换后的文本 (必填, string)
风险等级: medium
并发安全: false
只读: false

## exec_command

描述: 执行 Shell 命令并返回输出
参数:
  - command: 要执行的命令 (必填, string)
  - timeout: 超时毫秒数 (选填, int, 默认 120000)
风险等级: high
并发安全: false
只读: false
需要审批: true

## search_files

描述: 按 glob 模式搜索文件
参数:
  - pattern: glob 模式 (必填, string, 如 "**/*.py")
  - path: 搜索根目录 (选填, string, 默认为当前工作目录)
风险等级: low
并发安全: true
只读: true

## search_content

描述: 在文件内容中搜索正则表达式
参数:
  - pattern: 正则表达式 (必填, string)
  - path: 搜索目录或文件 (选填, string)
  - glob: 文件名过滤 (选填, string, 如 "*.py")
风险等级: low
并发安全: true
只读: true

## web_search

描述: 搜索网页
参数:
  - query: 搜索查询 (必填, string)
风险等级: low
并发安全: true
只读: true

## web_fetch

描述: 获取网页内容
参数:
  - url: 网页 URL (必填, string)
  - prompt: 提取信息的提示 (必填, string)
风险等级: medium
并发安全: true
只读: true
