"""Strogatz 爱情动力学 Skill — Layer 3"""
from ...core.base import BaseSkill, SkillMeta

class StrogatzSkill(BaseSkill):
    meta = SkillMeta(
        name="strogatz_love_dynamics", domain="psychology", layer=3,
        description="用微分方程建模爱情动力学 — Romeo & Juliet 模型",
        scientific_basis="Strogatz (1988); 4-delay stability analysis (2023, J. Franklin Inst.)",
        scientific_rating=4, trigger_conditions=["romantic"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""Strogatz爱情动力学。互动: {event.get('description','')}
Romeo-Juliet模型: dR/dt=aR+bJ a>0安全型/a<0焦虑型 b>0被激励/b<0回避型
JSON: {{"a_parameter":0.5,"b_parameter":0.5,"system_trend":"","stability_assessment":"","delay_effect":"","equilibrium_point":0.5}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "system_trend": "unknown",
            "a_parameter": 0.0,
            "b_parameter": 0.0,
            "stability_assessment": "未知",
            "delay_effect": "无明显延迟效应",
            "equilibrium_point": 0.0,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
