"""Young 图式更新 Skill — Layer 5"""
from ...core.base import BaseSkill, SkillMeta

class YoungSchemaSkill(BaseSkill):
    meta = SkillMeta(
        name="young_schema_update", domain="psychology", layer=5,
        description="分析当前事件是否确认/挑战/修改了角色的早期适应不良图式",
        scientific_basis="Young (2003); PsyAgent (2026); MATE (AAAI 2026)",
        scientific_rating=4, trigger_conditions=["trauma", "reflective"], estimated_tokens=500, can_parallel=False,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        trauma = character_state.get("trauma", {})
        schemas = trauma.get("active_schemas", [])
        return f"""Young图式疗法。活跃图式: {schemas}
事件: {event.get('description','')}
JSON: {{"affected_schemas":[{{"name":"","effect":"reinforced/weakened","intensity_change":0.0}}],"schema_driven_interpretation":"","healing_opportunity":"","reinforcement_risk":0.5,"schema_shift_summary":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "affected_schemas": [],
            "schema_driven_interpretation": "基于已有图式的解读",
            "healing_opportunity": "无明显疗愈机会",
            "reinforcement_risk": 0.5,
            "schema_shift_summary": "图式无显著变化",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
