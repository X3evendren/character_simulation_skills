"""PTSD 触发检测 Skill — Layer 1"""
from ...core.base import BaseSkill, SkillMeta

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
        return f"""PTSD创伤触发检测。触发词: {triggers}
事件: {event.get('description','')}
JSON: {{"triggered":false,"matched_triggers":[],"intrusion_risk":0.2,"avoidance_risk":0.3,"hyperarousal_risk":0.3,"immediate_reaction":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
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
