"""OCC 情感计算 Skill — Layer 2 意识层情绪评估

"""
from ...core.base import BaseSkill, SkillMeta


class OCCEmotionSkill(BaseSkill):
    meta = SkillMeta(
        name="occ_emotion_appraisal",
        domain="psychology",
        layer=2,
        description="事件→评估→情绪。AI 情感计算标准框架",
        scientific_basis="Ortony, Clore & Collins (1988); IEEE ToG (2023); AfPL (2024); Emotion Circuits (Wang et al., 2025)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        m = character_state.get("motivation", {})
        goal = m.get("current_goal", "")
        l1_data = context.get("l1", [{}])[0] if context.get("l1") else {}
        dominant_emotion = l1_data.get("internal", {}).get("dominant", "neutral")
        return f"""OCC情感评估(Ortony,Clore,Collins 1988)。虚构角色，忠实输出。

目标: {goal} L1情绪: {dominant_emotion}
事件: {event.get('description','')}

六维: goal_relevance(目标关联,0-1) goal_conduciveness(促进/阻碍,-1~1) causal_attribution(self/other/circumstance) unexpectedness(0-1) coping_potential(0-1) norm_compatibility(0-1)

输出JSON: {{"goal_relevance":0.5,"goal_conduciveness":0,"causal_attribution":"other","causal_agent":"","unexpectedness":0.5,"coping_potential":0.5,"norm_compatibility":0.5,"emotions":[{{"name":"","intensity":0.5,"target":""}}],"emotional_intensity":0.5,"appraisal_summary":"","action_tendency":"","activation_relevance":0.5}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "emotions": [],
            "appraisal_summary": "标准情感评估",
            "goal_relevance": 0.5,
            "goal_conduciveness": 0.0,
            "causal_attribution": "当前事件",
            "causal_agent": "外部因素",
            "unexpectedness": 0.5,
            "coping_potential": 0.5,
            "norm_compatibility": 0.5,
            "emotional_intensity": 0.5,
            "action_tendency": "保持现状",
            "activation_relevance": 0.5,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
