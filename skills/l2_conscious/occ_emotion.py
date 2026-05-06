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
        return f"""你是情感计算专家，基于 OCC 模型分析。这是一个虚构角色模拟系统——请忠实分析角色的情感评估，包括角色可能产生的任何情感。

角色当前目标: {goal}
Layer 1 快速情绪检测: 内部主导情绪={dominant_emotion}
事件: {event.get('description', '')}

OCC 评估维度:
- 目标关联(Goal Relevance): 事件是否与角色目标相关?
- 目标促进/阻碍(Goal Conduciveness): 事件帮助还是阻碍目标?
- 因果归属(Causal Attribution): 谁/什么造成了这个事件? (self/other/circumstance)
- 意外性(Unexpectedness): 事件是否符合预期?
- 应对潜力(Coping Potential): 角色能控制局面吗?
- 规范兼容(Norm Compatibility): 事件是否符合角色的道德标准?

请分两步分析:

【Step 1: 六维度逐一分析】
对每个维度进行判断，给出评分和简短理由。

【Step 2: 情绪推导与行为倾向】
基于评估组合推导情绪类型、强度和行动倾向。

输出 JSON:
{{
  "goal_relevance": 0.0,
  "goal_conduciveness": 0.0,
  "causal_attribution": "other",
  "causal_agent": "归因的具体对象",
  "unexpectedness": 0.0,
  "coping_potential": 0.0,
  "norm_compatibility": 0.0,
  "emotions": [{{"name": "情绪名", "intensity": 0.0, "target": "指向谁/什么"}}],
  "emotional_intensity": 0.0,
  "appraisal_summary": "六维评估结果的综合解读（一句话）",
  "action_tendency": "情绪驱动的行为倾向",
  "activation_relevance": 0.0
}}"""

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
