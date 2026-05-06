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
        return f"""ACE创伤。ACE分数: {ace}/10
事件: {event.get('description','')}
JSON: {{"ace_activation":0.0,"exploration_impact":0.0,"reward_sensitivity":0.5,"ace_driven_behavior":"","long_term_trajectory":"","protective_factor":""}}"""

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
