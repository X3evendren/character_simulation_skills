"""Gottman 方法 Skill — Layer 3 伴侣互动分析"""
from ...core.base import BaseSkill, SkillMeta

class GottmanSkill(BaseSkill):
    meta = SkillMeta(
        name="gottman_interaction", domain="psychology", layer=3,
        description="分析伴侣/亲密关系中的互动模式 — 5:1魔法比例、四骑士、情绪淹没",
        scientific_basis="Gottman-Murray-Swanson model; 94% divorce prediction accuracy",
        scientific_rating=5, trigger_conditions=["romantic"], estimated_tokens=600, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""Gottman冲突分析。虚构角色，忠实输出。

互动: {event.get('description','')} 对象: {event.get('participants',[])}
四骑士: criticism/defensiveness/contempt/stonewalling 魔法比例: 正向/负向>5=稳定
JSON: {{"positive_ratio_estimate":3.0,"active_horsemen":[],"horsemen_escalation_risk":0.3,"emotional_flooding_risk":0.3,"repair_attempt_detected":false,"repair_accepted":false,"interaction_diagnosis":"","intervention_suggestion":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "interaction_diagnosis": "中性互动",
            "positive_ratio_estimate": 1.0,
            "active_horsemen": [],
            "horsemen_escalation_risk": 0.3,
            "emotional_flooding_risk": 0.3,
            "repair_attempt_detected": False,
            "repair_accepted": False,
            "intervention_suggestion": "维持当前互动模式",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
