"""Fisher 恋爱三阶段 Skill — Layer 3"""
from ...core.base import BaseSkill, SkillMeta

class FisherLoveSkill(BaseSkill):
    meta = SkillMeta(
        name="fisher_love_stages", domain="psychology", layer=3,
        description="分析恋爱关系的生物学阶段 — 欲望/吸引/依恋",
        scientific_basis="Fisher (2004) — Why We Love; Oxford Handbook Evolutionary Psychology (2023)",
        scientific_rating=3, trigger_conditions=["romantic"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""Fisher恋爱阶段。互动: {event.get('description','')}
三阶段: lust(睾酮/雌激素)→attraction(多巴胺/去甲肾上腺素)→attachment(催产素/加压素)
JSON: {{"current_stage":"","stage_markers":[],"neurochemical_profile":"","transition_readiness":0.5,"stuck_risk":0.3}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "current_stage": "unknown",
            "stage_markers": [],
            "neurochemical_profile": "unknown",
            "transition_readiness": 0.5,
            "stuck_risk": 0.3,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
