"""
JSON 解析工具 — 从 LLM 原始输出中提取结构化 JSON。
移植自 character_mind v2 core/base.py 的 extract_json() 函数。
"""
from __future__ import annotations

import json
import re


def extract_json(raw_output: str) -> dict:
    """从 LLM 原始输出中提取 JSON 字典。

    处理常见情况:
    1. ```json ... ``` 围栏代码块
    2. ``` ... ``` 无标记围栏
    3. 裸 JSON 字符串
    4. 尾随逗号 (LLM 常见错误)
    5. BOM / 不可见前缀
    6. 单引号 JSON
    7. 截断的 JSON (尝试补全)

    返回解析后的 dict，失败返回空 dict。
    """
    text = raw_output.strip()
    text = text.lstrip("﻿​‌‍⁠")

    # 优先匹配围栏代码块
    match = re.search(r'`{3,}\s*(?:json)?\s*\n(.*?)\n\s*`{3,}', text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # 回退: 取首尾花括号之间的内容
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end + 1]

    # 移除尾随逗号
    text = re.sub(r',\s*([]}])', r'\1', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试修复单引号 JSON
    try:
        return json.loads(text.replace("'", '"'))
    except json.JSONDecodeError:
        pass

    # 尝试修复截断的 JSON: 补全缺失的闭合括号
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    if open_braces > 0 or open_brackets > 0:
        fixed = text.rstrip()
        fixed = re.sub(r',\s*$', '', fixed)

        quote_count = fixed.count('"')
        if quote_count % 2 != 0:
            try:
                return json.loads(fixed + '": null' + ']' * max(0, open_brackets) + '}' * max(0, open_braces))
            except json.JSONDecodeError:
                pass
            try:
                return json.loads(fixed + '"' + ']' * max(0, open_brackets) + '}' * max(0, open_braces))
            except json.JSONDecodeError:
                pass

        last_colon = fixed.rfind(':')
        if last_colon > 0:
            before_colon = fixed[:last_colon].rstrip()
            if before_colon.endswith('"'):
                try:
                    return json.loads(before_colon + ': null' + ']' * max(0, open_brackets) + '}' * max(0, open_braces))
                except json.JSONDecodeError:
                    pass

        try:
            return json.loads(fixed + ']' * max(0, open_brackets) + '}' * max(0, open_braces))
        except json.JSONDecodeError:
            pass

    return {}


def extract_xml(raw_output: str, tag: str) -> str | None:
    """从 LLM 输出中提取 XML 标签内容。"""
    pattern = rf'<{tag}>(.*?)</{tag}>'
    match = re.search(pattern, raw_output, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_xml_attr(raw_output: str, tag: str, attr: str) -> str | None:
    """从 LLM 输出中提取 XML 标签的属性值。"""
    pattern = rf'<{tag}\s[^>]*{attr}="([^"]*)"'
    match = re.search(pattern, raw_output)
    return match.group(1) if match else None
