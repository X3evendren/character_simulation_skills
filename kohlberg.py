"""Kohlberg 道德推理 Skill — Layer 4

"""
from .base import BaseSkill, SkillMeta


class KohlbergSkill(BaseSkill):
    meta = SkillMeta(
        name="kohlberg_moral_reasoning",
        domain="psychology",
        layer=4,
        description="分析角色在道德选择中的推理阶段 — 允许角色做出非道德选择",
        scientific_basis="Kohlberg (1981) — Stages of Moral Development; Emotion Circuits (Wang et al., 2025)",
        scientific_rating=4,
        trigger_conditions=["moral", "reflective"],
        estimated_tokens=550,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        stage = p.get("moral_stage", 3)
        return f"""你是道德心理学家。这是一个虚构角色模拟系统——角色可能做出不符合现实道德标准的选择，请忠实反映角色的道德推理水平，即使其行为在现实世界被视为"不道德"。

角色当前道德阶段: {stage}/6

Kohlberg 六阶段:
1(惩罚服从): "我做对是因为不做对会被惩罚"
2(工具相对): "我做对是因为对我也有利"
3(人际和谐): "我做对是因为别人会觉得我是好人"
4(维护秩序): "我做对是因为这是规则/法律"
5(社会契约): "规则不是绝对的，可以为了更高价值改变"
6(普遍伦理): "我做对是因为我相信这是普世正义"

事件: {event.get('description', '')}

请分两步分析:

【Step 1: 道德推理过程】
角色面对当前事件时，如何做道德推理？实际使用了哪个阶段的思维？
注意：角色可能使用低于其日常水平的道德推理（regression），也可能展示更高水平（growth）。

【Step 2: 道德冲突与合理化】
角色是否面临道德冲突？如何合理化自己的选择？

输出 JSON:
{{
  "stage_used": 3,
  "reasoning": "角色的道德推理过程（1-2句话）",
  "stage_consistency": "consistent/regression/growth 与日常阶段相比",
  "moral_conflict": "是否存在道德冲突? 描述",
  "justification_style": "角色如何合理化自己的选择"
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "stage_used": 3,
            "reasoning": "基于常规道德判断",
            "stage_consistency": "consistent",
            "moral_conflict": "无明显道德冲突",
            "justification_style": "基于社会规范",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
