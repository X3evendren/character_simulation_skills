"""
依恋理论分析 Skill

Bowlby/Ainsworth 依恋理论。四个依恋风格决定角色在亲密关系中的反应模式。
LLM 已通过 AAI 模拟测试 (Soares et al., 2024)。

论文: Soares et al. (2024); Htet et al. (2024)
"""
from .base import BaseSkill, SkillMeta


class AttachmentSkill(BaseSkill):
    meta = SkillMeta(
        name="attachment_style_analysis",
        domain="psychology",
        layer=0,
        description="分析角色依恋风格在当前社交/亲密情境中的激活程度和行为倾向",
        scientific_basis="Bowlby/Ainsworth; Soares et al. (2024); Htet et al. (2024)",
        scientific_rating=5,
        trigger_conditions=["always", "romantic", "social"],
        estimated_tokens=600,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        style = p.get("attachment_style", "secure")
        return f"""你是一位依恋理论专家。角色依恋风格: {style}

依恋风格行为特征:
- secure: 信任他人，能坦然表达需求，接受亲密也接受独立
- anxious: 极度需要确认，害怕被抛弃，过度关注对方的回应
- avoidant: 拒绝亲密，强调独立，用距离保护自己
- fearful_avoidant: 渴望亲密同时恐惧亲密，反复推拉

当前事件: {event.get('description', '')}
事件类型: {event.get('type', '')}
涉及他人: {event.get('participants', [])}

分析该依恋风格在当前情境中的激活。输出 JSON:
{{
  "activation_level": "0.0-1.0 依恋系统的激活强度",
  "trigger": "什么触发了依恋反应（如'对方说会保护我→触发被控制感'）",
  "internal_experience": "角色此刻内心真正感受到但不会说出口的是什么（1-2句）",
  "defense_behavior": "角色会做什么来保护自己",
  "what_they_say": "角色实际会说出口的话",
  "what_they_need": "角色此刻最深的需求（但他们不会直接要求）",
  "partner_perception_risk": "对方可能把这种行为误读为什么",
  "next_prediction": "如果对方不做改变，角色下一步会怎么做"
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"activation_level": 0.5}
