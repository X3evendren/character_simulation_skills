"""SDT 自我决定理论 Skill — Layer 4"""
from ...core.base import BaseSkill, SkillMeta

class SDTSkill(BaseSkill):
    meta = SkillMeta(
        name="sdt_motivation_analysis", domain="psychology", layer=4,
        description="分析角色的自主性/胜任感/归属感三需求满足状态",
        scientific_basis="Deci & Ryan (2000); Self++ (2026, arXiv)",
        scientific_rating=5, trigger_conditions=["reflective"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        m = character_state.get("motivation", {})
        return f"""SDT自我决定。事件: {event.get('description','')}
三需求: 自主性({m.get('autonomy_satisfaction',0.5):.1f}) 胜任感({m.get('competence_satisfaction',0.5):.1f}) 关系感({m.get('relatedness_satisfaction',0.5):.1f})
JSON: {{"autonomy_impact":0,"competence_impact":0,"relatedness_impact":0,"most_threatened":"","compensation_behavior":"","intrinsic_motivation_level":0.5}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "intrinsic_motivation_level": 0.5,
            "autonomy_impact": 0.0,
            "competence_impact": 0.0,
            "relatedness_impact": 0.0,
            "most_threatened": "none",
            "compensation_behavior": "无显著补偿行为",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
