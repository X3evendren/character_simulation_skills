"""PTSD 触发检测 Skill — Layer 1"""
from .base import BaseSkill, SkillMeta

class PTSDTriggerSkill(BaseSkill):
    meta = SkillMeta(
        name="ptsd_trigger_check", domain="psychology", layer=1,
        description="检测事件是否激活角色的创伤触发点",
        scientific_basis="DSM-5 PTSD criteria; Lloyd et al. (2022, PNAS)",
        scientific_rating=5, trigger_conditions=["trauma", "conflict"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        trauma = character_state.get("trauma", {})
        triggers = trauma.get("trauma_triggers", [])
        return f"""你是创伤心理学专家。角色已知创伤触发: {triggers}
当前事件: {event.get('description', '')}

分析是否触发创伤。输出 JSON:
{{"triggered": true/false,
 "matched_triggers": ["匹配到的触发点"],
 "intrusion_risk": "0.0-1.0 侵入症状风险",
 "avoidance_risk": "0.0-1.0 回避行为风险",
 "hyperarousal_risk": "0.0-1.0 过度警觉风险",
 "immediate_reaction": "角色的即刻创伤反应（一句话）"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "triggered": False,
            "matched_triggers": [],
            "intrusion_risk": 0.3,
            "avoidance_risk": 0.3,
            "hyperarousal_risk": 0.3,
            "immediate_reaction": "无明显创伤反应",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
