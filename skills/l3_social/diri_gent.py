"""DiriGent 理想世界分析 Skill — Layer 3/4

基于 DiriGent (ETH Zurich, AAAI AIIDE 2025):
- 角色有"理想世界"表征（values, desired relationships, goals）
- LLM分析理想世界 vs 感知现实世界的张力
- 张力驱动信念动机行为

这个skill分析角色"想要的"和"得到的"之间的差距——驱动角色行动的根本动力。
"""
from ...core.base import BaseSkill, SkillMeta


class DiriGentSkill(BaseSkill):
    meta = SkillMeta(
        name="dirigent_world_tension",
        domain="psychology",
        layer=3,
        description="分析角色理想世界与现实感知的张力 — 驱动角色行动的根本动机分析",
        scientific_basis="DiriGent (ETH, AAAI AIIDE 2025); Cognitive Dissonance (Festinger 1957); Self-Discrepancy Theory (Higgins 1987)",
        scientific_rating=4,
        trigger_conditions=["reflective", "conflict", "romantic"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        ideal = character_state.get("ideal_world", {})
        p = character_state.get("personality", {})
        m = character_state.get("motivation", {})

        return f"""DiriGent理想世界张力。虚构角色，忠实输出。

理想自我: {ideal.get('ideal_self','')} 理想关系: {ideal.get('ideal_relationships','')}
人格: O={p.get('openness',0.5):.1f} C={p.get('conscientiousness',0.5):.1f} E={p.get('extraversion',0.5):.1f} A={p.get('agreeableness',0.5):.1f} N={p.get('neuroticism',0.5):.1f}
目标: {m.get('current_goal','')} 事件: {event.get('description','')}
张力维度: self/relationship/social/values/existential 对应 ideal vs actual 的 gap→pain
JSON: {{"perceived_reality":"","tension_dimensions":{{"self":{{"gap":0.3,"actual":"","ideal":"","pain":0.3}},"relationship":{{"gap":0.3,"actual":"","ideal":"","pain":0.3}}}},"dominant_tension":"self","overall_cognitive_dissonance":0.5,"coping_strategy":"emotion_focused","predicted_action":"","long_term_arc_impact":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "overall_cognitive_dissonance": 0.5,
            "coping_strategy": "mixed",
            "perceived_reality": "当前感知的现实",
            "tension_dimensions": {},
            "dominant_tension": "self",
            "predicted_action": "维持现状",
            "long_term_arc_impact": "持续张力将影响角色发展",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
