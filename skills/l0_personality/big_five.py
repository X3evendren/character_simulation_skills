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
        n = p.get('neuroticism', 0.5)
        a = p.get('agreeableness', 0.5)
        c = p.get('conscientiousness', 0.5)
        e = p.get('extraversion', 0.5)
        o = p.get('openness', 0.5)

        # 根据数值生成具体的人格描述
        trait_desc = []
        if n >= 0.7:
            trait_desc.append(f"神经质极高({n:.1f})——对威胁信号敏感，容易焦虑和灾难化思考，情绪反应强烈且持续时间长")
        elif n >= 0.55:
            trait_desc.append(f"神经质偏高({n:.1f})——容易担忧，对负面信息更敏感，情绪波动较大")
        elif n <= 0.35:
            trait_desc.append(f"神经质低({n:.1f})——情绪稳定，压力下保持冷静，不易被负面信息扰动")
        if a <= 0.3:
            trait_desc.append(f"宜人性低({a:.1f})——以自我为中心，质疑他人动机，在冲突中坚持己见，不轻易妥协")
        elif a >= 0.7:
            trait_desc.append(f"宜人性高({a:.1f})——优先考虑他人感受，容易妥协，回避冲突，渴望和谐")
        if c >= 0.75:
            trait_desc.append(f"尽责性高({c:.1f})——审慎决策，重视计划和秩序，追求完美，对自己要求严格")
        elif c <= 0.3:
            trait_desc.append(f"尽责性低({c:.1f})——随性灵活，不喜欢被规则束缚，可能拖延或冲动行事")
        if e <= 0.3:
            trait_desc.append(f"外向性低({e:.1f})——内向克制，在社交中消耗能量，倾向于独处和小圈子互动")
        elif e >= 0.7:
            trait_desc.append(f"外向性高({e:.1f})——从社交中获得能量，喜欢表达和互动，主动发起对话")

        trait_text = "\n".join(trait_desc) if trait_desc else "各项人格指标处于中等水平，无明显极端倾向"

        return f"""基于大五人格模型分析角色在当前情境中的行为倾向。

【人格特征】
{trait_text}

【情境】
事件: {event.get('description', '日常')}
类型: {event.get('type', 'neutral')}

请根据人格特征预测角色在此情境中的反应。注意：
- 数值极端(>0.7或<0.3)的人格维度会显著影响行为
- 神经质直接决定情绪反应强度
- 宜人性决定社交倾向和冲突处理方式
- 尽责性影响决策的审慎程度

只输出 JSON:
{{
  "behavioral_bias": "角色最可能的行为反应（1-2句，具体到会说什么或做什么）",
  "emotional_reactivity": 0.5,
  "social_approach": "approach/avoid/neutral",
  "decision_style": "impulsive/deliberate/cautious/risk_taking",
  "stress_response": "压力下的具体表现（1句话）",
  "interpretation_bias": "角色如何主观解读这个事件（1-2句，反映人格偏置）"
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
