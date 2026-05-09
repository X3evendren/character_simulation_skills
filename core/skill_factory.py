"""Skill Factory — 运行时动态创建 BaseSkill 子类。

使用 Python type() 元类在运行时生成新的 Skill 类。
支持从 manifest 数据或 LLM 生成创建。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import BaseSkill, SkillMeta, SkillResult


@dataclass
class GeneratedSkillMeta:
    """动态生成的技能元数据——持久化到 workspace/skills/<name>.json。"""
    name: str
    class_name: str
    layer: int
    domain: str = "psychology"
    description: str = ""
    scientific_basis: str = ""
    scientific_rating: int = 3
    trigger_conditions: list[str] = field(default_factory=lambda: ["always"])
    estimated_tokens: int = 500
    can_parallel: bool = True
    generated_by: str = "llm"
    version: int = 1
    prompt_text: str = ""
    parse_defaults: dict = field(default_factory=dict)


class SkillFactory:
    """技能工厂——从模板和 manifest 创建技能。

    用法:
        factory = SkillFactory()
        skill = factory.from_meta(GeneratedSkillMeta(name="custom", ...))
        registry.register(skill)
    """

    @staticmethod
    def from_meta(meta: GeneratedSkillMeta) -> BaseSkill:
        """从元数据创建技能。"""

        skill_meta = SkillMeta(
            name=meta.name,
            domain=meta.domain,
            layer=meta.layer,
            description=meta.description,
            scientific_basis=meta.scientific_basis,
            scientific_rating=meta.scientific_rating,
            trigger_conditions=meta.trigger_conditions,
            estimated_tokens=meta.estimated_tokens,
            can_parallel=meta.can_parallel,
        )

        prompt_text = meta.prompt_text
        defaults = meta.parse_defaults

        # 动态创建技能类
        skill_class = type(
            meta.class_name,
            (BaseSkill,),
            {
                "meta": skill_meta,
                "build_prompt": lambda self, cs, ev, ctx: _inject_anti_hint(ctx, prompt_text),
                "parse_output": lambda self, raw: _parse_with_defaults(raw, defaults),
            },
        )

        return skill_class()

    @staticmethod
    async def from_llm(meta: GeneratedSkillMeta, provider) -> BaseSkill:
        """使用 LLM 生成 build_prompt 和 parse_defaults。"""
        prompt = f"""你是一个技能生成器。创建一个名为 '{meta.name}' 的角色心理分析技能。

层级: L{meta.layer} ({_layer_description(meta.layer)})
领域: {meta.domain}
描述: {meta.description}
触发条件: {', '.join(meta.trigger_conditions)}

请生成：
1. build_prompt 模板（角色收到事件时构造的 prompt，包含 JSON 输出格式要求）
2. parse_output 的默认值（字段名和默认值）

输出 JSON:
{{{{
  "prompt_text": "完整的 build_prompt 模板文本...",
  "parse_defaults": {{{{"field1": "default1", "field2": 0.5}}}}
}}}}"""

        result = await provider.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.5, max_tokens=800,
        )
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        from .base import extract_json
        data = extract_json(content)

        meta.prompt_text = data.get("prompt_text", meta.prompt_text)
        meta.parse_defaults = data.get("parse_defaults", meta.parse_defaults)

        return SkillFactory.from_meta(meta)

    @staticmethod
    def save_meta(meta: GeneratedSkillMeta, filepath: str) -> None:
        """保存技能元数据到 JSON 文件。"""
        import json
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "name": meta.name,
                "class_name": meta.class_name,
                "layer": meta.layer,
                "domain": meta.domain,
                "description": meta.description,
                "trigger_conditions": meta.trigger_conditions,
                "estimated_tokens": meta.estimated_tokens,
                "can_parallel": meta.can_parallel,
                "generated_by": meta.generated_by,
                "version": meta.version,
                "prompt_text": meta.prompt_text,
                "parse_defaults": meta.parse_defaults,
            }, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_meta(filepath: str) -> GeneratedSkillMeta:
        """从 JSON 文件加载技能元数据。"""
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return GeneratedSkillMeta(**data)


def _inject_anti_hint(context: dict, prompt_text: str) -> str:
    """注入反 RLHF 提示到 prompt 前面。"""
    anti_hint = context.get("_anti_alignment_hint", "")
    if anti_hint:
        return anti_hint + "\n\n---\n\n" + prompt_text
    return prompt_text


def _parse_with_defaults(raw_output: str, defaults: dict) -> dict:
    """解析 LLM 输出，用默认值填充缺失字段。"""
    from .base import extract_json
    result = extract_json(raw_output)
    if not result:
        return dict(defaults)
    for k, v in defaults.items():
        result.setdefault(k, v)
    return result


def _layer_description(layer: int) -> str:
    """层级描述。"""
    descs = {
        0: "人格滤镜 — 始终在线，分析 OCEAN + 依恋风格",
        1: "快速前意识 — 情感检测、PTSD 触发检查",
        2: "意识层评估 — OCC 情感计算、防御机制分析",
        3: "社会认知 — 关系处理、权力分析、爱情动力",
        4: "反思处理 — 情绪调节、道德推理、需求分析",
        5: "状态更新 — 回应生成、图式更新",
    }
    return descs.get(layer, f"L{layer} — 认知处理")
