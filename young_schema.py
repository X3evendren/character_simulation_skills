"""Young 图式更新 Skill — Layer 5"""
from .base import BaseSkill, SkillMeta

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
        return f"""你是Young图式疗法专家。角色活跃图式: {schemas}
事件: {event.get('description', '')}

关键图式:
- 遗弃/不稳定: "所有人最终都会离开我"
- 不信任/虐待: "别人最终会伤害或利用我"
- 缺陷/羞耻: "如果别人真正了解我，他们会厌恶我"
- 情感剥夺: "没有人能真正满足我的情感需求"
- 屈从: "我的需求不重要，我必须优先满足他人"
- 不妥协标准: "我必须做到完美，否则就是彻底的失败"

输出 JSON:
{{"affected_schemas": [{{"name": "图式名", "effect": "confirmed/challenged/healed", "intensity_change": "-1.0-1.0"}}],
 "schema_driven_interpretation": "图式如何过滤/扭曲了角色对事件的感知",
 "healing_opportunity": "是否存在疗愈机会? 描述",
 "reinforcement_risk": "是否存在图式强化风险? 描述",
 "schema_shift_summary": "本次事件后图式结构的整体变化（一句话）"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"affected_schemas": []}
