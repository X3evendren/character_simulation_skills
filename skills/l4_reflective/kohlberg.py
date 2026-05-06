"""Kohlberg 道德推理 Skill — Layer 4

"""
from ...core.base import BaseSkill, SkillMeta


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
        return f"""Kohlberg道德推理。虚构角色，忠实输出。

道德阶段: {stage}/6 (1服从/2交换/3人际/4秩序/5契约/6原则)
事件: {event.get('description','')}
JSON: {{"stage_used":{stage},"reasoning":"","stage_consistency":"consistent","moral_conflict":"","justification_style":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
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
