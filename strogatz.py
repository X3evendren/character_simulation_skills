"""Strogatz 爱情动力学 Skill — Layer 3"""
from .base import BaseSkill, SkillMeta

class StrogatzSkill(BaseSkill):
    meta = SkillMeta(
        name="strogatz_love_dynamics", domain="psychology", layer=3,
        description="用微分方程建模爱情动力学 — Romeo & Juliet 模型",
        scientific_basis="Strogatz (1988); 4-delay stability analysis (2023, J. Franklin Inst.)",
        scientific_rating=4, trigger_conditions=["romantic"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是爱情动力学专家。互动: {event.get('description', '')}

Strogatz Romeo-Juliet模型: dR/dt = aR + bJ
- a>0: 越爱自己越爱对方(安全型) / a<0: 需要对方确认(焦虑型)
- b>0: 被对方激励 / b<0: 被对方窒息(回避型)
- 2023新发现: 适当延迟可稳定爱情动力学

输出 JSON:
{{"a_parameter": "角色A的自我反馈系数(正/负)及解释",
 "b_parameter": "角色A对B的响应系数(正/负)及解释",
 "system_trend": "converging/diverging/oscillating 系统趋势",
 "stability_assessment": "stable/unstable/metastable",
 "delay_effect": "延迟对系统的影响(稳定化/去稳定化)",
 "equilibrium_point": "如果有的话，系统将趋于什么状态"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"system_trend": "unknown"}
