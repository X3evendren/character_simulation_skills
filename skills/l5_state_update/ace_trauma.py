"""ACE 创伤分析 Skill — Layer 5"""
from ...core.base import BaseSkill, SkillMeta

class ACETraumaSkill(BaseSkill):
    meta = SkillMeta(
        name="ace_trauma_processing", domain="psychology", layer=5,
        description="分析童年不良经历对当前行为的深层影响",
        scientific_basis="Felitti et al. (1998); Lloyd et al. (2022, PNAS); Afzal et al. (2024)",
        scientific_rating=5, trigger_conditions=["trauma"], estimated_tokens=500, can_parallel=False,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        trauma = character_state.get("trauma", {})
        ace = trauma.get("ace_score", 0)
        return f"""你是ACE研究专家。角色ACE分数: {ace}/10
事件: {event.get('description', '')}

ACE 10种: 身体虐待/情感虐待/性虐待/身体忽视/情感忽视/母亲被暴力/物质滥用/精神疾病/父母分离/家人入狱
ACE≥4: 探索行为减少(exploration↓)、奖励反馈迟钝(reward sensitivity↓) — PNAS 2022

输出 JSON:
{{"ace_activation": "0.0-1.0 ACE在此事件中的激活程度",
 "exploration_impact": "角色探索/回避行为的ACE根源",
 "reward_sensitivity": "角色对正向反馈的反应(正常/迟钝/过度)",
 "ace_driven_behavior": "ACE驱动的当前行为（一句话）",
 "long_term_trajectory": "如果不干预，ACE对此角色关系的长期影响",
 "protective_factor": "角色当前的保护因素（如果有）"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "ace_activation": 0.0,
            "exploration_impact": 0.0,
            "reward_sensitivity": 0.5,
            "ace_driven_behavior": "无明显ACE驱动行为",
            "long_term_trajectory": "维持当前发展轨迹",
            "protective_factor": "无特定保护因素",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
