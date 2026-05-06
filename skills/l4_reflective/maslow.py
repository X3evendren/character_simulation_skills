"""Maslow 需求层次 Skill — Layer 4"""
from ...core.base import BaseSkill, SkillMeta

class MaslowSkill(BaseSkill):
    meta = SkillMeta(
        name="maslow_need_stack", domain="psychology", layer=4,
        description="分析角色当前的需求层次和动机优先级",
        scientific_basis="Maslow (1943, 1954); LLM Agent自发人格研究 (Fujiyama 2025)",
        scientific_rating=4, trigger_conditions=["reflective"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""Maslow需求层次。事件: {event.get('description','')}
五层(高→低): 5自我实现 4尊重 3归属与爱 2安全 1生理
JSON: {{"current_dominant":3,"need_stack":[{{"level":1,"name":"","satisfaction":0.5,"urgency":0.5}}],"blocked_needs":[],"deficiency_vs_growth":"deficiency","behavior_explanation":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "current_dominant": 3,
            "need_stack": [],
            "blocked_needs": [],
            "deficiency_vs_growth": "neutral",
            "behavior_explanation": "行为受多层次需求驱动",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
