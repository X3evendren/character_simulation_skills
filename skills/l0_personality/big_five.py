"""
Big Five (OCEAN) 人格分析 Skill

基于大五人格模型 (Costa & McCrae, 1992)，对角色在当前情境中的行为倾向进行分析。
替代 MBTI — 连续测量，包含神经质维度，重测信度 0.80-0.90。

论文: P-React (2024), Orca (2024), CB-POCL (2013)
"""
from ...core.base import BaseSkill, SkillMeta, SkillResult


class BigFiveSkill(BaseSkill):
    meta = SkillMeta(
        name="big_five_analysis",
        domain="psychology",
        layer=0,
        description="分析角色大五人格在当前情境中的行为偏置",
        scientific_basis="Costa & McCrae (1992); P-React (2024); Orca (2024)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=500,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        return f"""你是一位人格心理学专家，基于大五人格模型 (OCEAN) 分析角色。

角色人格数据:
- 开放性: {p.get('openness', 0.5):.1f} (对新鲜体验的接受度)
- 尽责性: {p.get('conscientiousness', 0.5):.1f} (自律/条理/目标驱动)
- 外向性: {p.get('extraversion', 0.5):.1f} (社交能量来源)
- 宜人性: {p.get('agreeableness', 0.5):.1f} (合作 vs 竞争)
- 神经质: {p.get('neuroticism', 0.5):.1f} (情绪稳定性，高分=容易焦虑)

当前事件: {event.get('description', '日常')}
事件类型: {event.get('type', 'neutral')}

请分析该人格在当前情境中的行为偏置。输出 JSON:
{{
  "behavioral_bias": "角色最可能的行为方向（一句话）",
  "emotional_reactivity": "0.0-1.0 情绪反应强度预判",
  "social_approach": "approach/avoid/neutral 社交倾向",
  "decision_style": "impulsive/deliberate/cautious/risk_taking",
  "stress_response": "角色在压力下最可能的表现（一句话）",
  "interpretation_bias": "角色会如何解读当前事件（1-2句话，体现人格偏置）"
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "behavioral_bias": "按基线人格做出反应",
            "emotional_reactivity": 0.5,
            "social_approach": "neutral",
            "decision_style": "deliberate",
            "stress_response": "在压力下保持惯常应对模式",
            "interpretation_bias": "从自身人格视角解读事件",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
