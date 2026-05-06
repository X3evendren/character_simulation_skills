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
        n, a, c, e = p.get('neuroticism',0.5), p.get('agreeableness',0.5), p.get('conscientiousness',0.5), p.get('extraversion',0.5)
        traits = f"O={p.get('openness',0.5):.1f} C={c:.1f} E={e:.1f} A={a:.1f} N={n:.1f}"
        hints = []
        if n>=0.7: hints.append("高神经质→威胁敏感+焦虑")
        elif n<=0.35: hints.append("低神经质→情绪稳定")
        if a<=0.3: hints.append("低宜人→自我中心+不妥协")
        elif a>=0.7: hints.append("高宜人→迎合+回避冲突")
        if c>=0.75: hints.append("高尽责→审慎+计划")
        if e<=0.3: hints.append("低外向→内向克制")
        hint = "; ".join(hints) or "中性"
        return f"""OCEAN: {traits} | {hint}
事件: {event.get('description','')}
JSON: {{"behavioral_bias":"","emotional_reactivity":0.5,"social_approach":"neutral","decision_style":"deliberate","stress_response":"","interpretation_bias":""}}"""

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
