"""Fisher 恋爱三阶段 Skill — Layer 3"""
from .base import BaseSkill, SkillMeta

class FisherLoveSkill(BaseSkill):
    meta = SkillMeta(
        name="fisher_love_stages", domain="psychology", layer=3,
        description="分析恋爱关系的生物学阶段 — 欲望/吸引/依恋",
        scientific_basis="Fisher (2004) — Why We Love; Oxford Handbook Evolutionary Psychology (2023)",
        scientific_rating=3, trigger_conditions=["romantic"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是Fisher恋爱阶段专家。互动: {event.get('description', '')}

三阶段(可重叠):
1. 欲望(Lust) — 睾酮/雌激素驱动，寻找潜在伴侣
2. 吸引(Attraction) — 多巴胺/去甲肾上腺素，强迫性专注
3. 依恋(Attachment) — 催产素/加压素，长期平静

输出 JSON:
{{"current_stage": "lust/attraction/attachment/transition",
 "stage_markers": ["当前阶段的标志性表现"],
 "neurochemical_profile": "主导神经化学物质及其效应",
 "transition_readiness": "0.0-1.0 向下一阶段过渡的准备度",
 "stuck_risk": "是否卡在当前阶段? 风险描述"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"current_stage": "unknown"}
