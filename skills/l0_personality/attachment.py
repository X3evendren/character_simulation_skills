"""
依恋理论分析 Skill

Bowlby/Ainsworth 依恋理论。四个依恋风格决定角色在亲密关系中的反应模式。
LLM 已通过 AAI 模拟测试 (Soares et al., 2024)。

论文: Soares et al. (2024); Htet et al. (2024)
"""
from ...core.base import BaseSkill, SkillMeta


class AttachmentSkill(BaseSkill):
    meta = SkillMeta(
        name="attachment_style_analysis",
        domain="psychology",
        layer=0,
        description="分析角色依恋风格在当前社交/亲密情境中的激活程度和行为倾向",
        scientific_basis="Bowlby/Ainsworth; Soares et al. (2024); Htet et al. (2024)",
        scientific_rating=5,
        trigger_conditions=["romantic", "social"],
        estimated_tokens=600,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        style = character_state.get("personality", {}).get("attachment_style", "secure")
        styles = {"secure":"信任+独立","anxious":"需要确认+怕被弃","avoidant":"拒绝亲密+用距离保护","fearful_avoidant":"渴望亲密又恐惧+推拉"}
        return f"""依恋风格: {style} ({styles.get(style,'')})
事件: {event.get('description','')}

分析依恋激活。JSON: {{"activation_level":0.5,"trigger":"","internal_experience":"","defense_behavior":"","what_they_say":"","what_they_need":"","partner_perception_risk":"","next_prediction":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "activation_level": 0.5,
            "trigger": "当前事件引发依恋系统",
            "internal_experience": "依恋相关的内在体验",
            "defense_behavior": "使用典型防御行为",
            "what_they_say": "依恋驱动的言语表达",
            "what_they_need": "依恋需求未明确",
            "partner_perception_risk": "可能存在偏差解读",
            "next_prediction": "维持当前依恋行为模式",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
