"""
Skill 基类

每个 Skill 代表一个外部模型。AI 不是"自己感受"——
而是按照 Skill 定义的分析框架，对当前状态进行分析后输出结构化结果。
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


def extract_json(raw_output: str) -> dict:
    """从 LLM 原始输出中提取 JSON 字典。

    处理常见情况:
    1. ```json ... ``` 围栏代码块
    2. ``` ... ``` 无标记围栏
    3. 裸 JSON 字符串
    4. 尾随逗号 (LLM 常见错误)
    5. BOM / 不可见前缀
    返回解析后的 dict，失败返回空 dict。
    """
    text = raw_output.strip()
    # 移除 BOM 和零宽字符
    text = text.lstrip("﻿​‌‍⁠")

    # 优先匹配围栏代码块
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # 回退: 取首尾花括号之间的内容
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end + 1]

    # 移除尾随逗号 (LLM 常见错误: {"a": 1,} 或 [1, 2,])
    text = re.sub(r',\s*([]}])', r'\1', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试修复单引号 JSON (LLM 常见错误: {'key': 'value'})
    try:
        return json.loads(text.replace("'", '"'))
    except json.JSONDecodeError:
        pass

    # 尝试修复截断的 JSON: 补全缺失的闭合括号
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    if open_braces > 0 or open_brackets > 0:
        # 在截断的字符串值处截断到最后一个完整的键或值
        fixed = text.rstrip()
        fixed = re.sub(r',\s*$', '', fixed)  # 移除尾部逗号
        # 检查是否因字符串未闭合而截断: 奇数个引号
        if fixed.count('"') % 2 != 0:
            fixed += '"'
        fixed += ']' * max(0, open_brackets)
        fixed += '}' * max(0, open_braces)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    return {}


@dataclass
class SkillResult:
    """Skill 执行结果"""
    skill_name: str
    layer: int
    output: dict[str, Any]
    tokens_used: int = 0
    success: bool = True
    error: str | None = None


@dataclass
class SkillMeta:
    """Skill 元信息"""
    name: str
    domain: str                     # psychology / social_science / world_science / narrative
    layer: int                      # 0-5 (五层时序)
    description: str
    scientific_basis: str           # 论文/著作引用
    scientific_rating: int          # 1-5 星
    trigger_conditions: list[str] = field(default_factory=list)  # always / social / romantic / conflict / moral / trauma / reflective
    estimated_tokens: int = 500
    can_parallel: bool = True
    input_dependencies: list[str] = field(default_factory=list)  # 依赖的其他 Skill 名称


class BaseSkill(ABC):
    """Skill 抽象基类"""

    meta: SkillMeta

    @abstractmethod
    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        """根据当前状态构建分析 prompt"""
        ...

    @abstractmethod
    def parse_output(self, raw_output: str) -> dict:
        """解析 AI 输出为结构化结果"""
        ...

    async def run(self, provider, character_state: dict, event: dict, context: dict) -> SkillResult:
        """执行 Skill — 自动注入反RLHF偏差提示"""
        prompt = self.build_prompt(character_state, event, context)

        # 如果context中有反RLHF提示，注入到prompt最前面
        anti_hint = context.get("_anti_alignment_hint", "")
        token_buffer = 0
        if anti_hint:
            prompt = anti_hint + "\n\n---\n\n" + prompt
            token_buffer = 200  # hint增加了prompt长度，给输出留余量

        try:
            result = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,  # 分析任务用低温
                max_tokens=self.meta.estimated_tokens + token_buffer,
            )
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            parsed = self.parse_output(content)
            return SkillResult(
                skill_name=self.meta.name,
                layer=self.meta.layer,
                output=parsed,
                tokens_used=result.get("usage", {}).get("total_tokens", 0),
            )
        except Exception as e:
            return SkillResult(
                skill_name=self.meta.name,
                layer=self.meta.layer,
                output={},
                success=False,
                error=str(e),
            )
