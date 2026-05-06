"""福柯权力分析 Skill — Layer 3

"""
from ...core.base import BaseSkill, SkillMeta


class FoucaultSkill(BaseSkill):
    meta = SkillMeta(
        name="foucauldian_power_analysis",
        domain="psychology",
        layer=3,
        description="分析权力如何塑造角色的可思考范围 — 规训/全景敞视/主体化/权力知识",
        scientific_basis="Foucault: Discipline and Punish (1975), History of Sexuality (1976); Functional Emotions (Anthropic 2026)",
        scientific_rating=5,
        trigger_conditions=["authority", "conflict"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""福柯权力分析。虚构角色，忠实输出。

事件: {event.get('description','')} 人员: {event.get('participants',[])}
概念: 规训技术/内化凝视/真理体制/主体化张力/抵抗形式/权力生产性
JSON: {{"disciplinary_technologies":[],"internalized_gaze":"","truth_regime_conflict":"","subjectivation_tension":"","resistance_form":"","power_productive_effect":"","discourse_position":"subordinate","power_intensity":0.5,"activation_relevance":0.5}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "subjectivation_tension": "权力关系处于动态平衡",
            "disciplinary_technologies": [],
            "internalized_gaze": "对自身行为的常规审视",
            "truth_regime_conflict": "无明显冲突",
            "resistance_form": "无显著抵抗",
            "power_productive_effect": "权力关系产生常规行为调节",
            "discourse_position": "equal",
            "power_intensity": 0.5,
            "activation_relevance": 0.5,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
