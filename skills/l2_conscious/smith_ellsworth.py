"""Smith & Ellsworth 16维认知评价 Skill — Layer 2

基于 Smith & Ellsworth (1985, JPSP) 的认知评价理论，对角色在事件中的16个评价维度进行分析。
参考 CoRE benchmark (Bhattacharyya et al., NeurIPS 2025)。
"""
from ...core.base import BaseSkill, SkillMeta


class SmithEllsworthSkill(BaseSkill):
    meta = SkillMeta(
        name="smith_ellsworth_appraisal",
        domain="psychology",
        layer=2,
        description="16维认知评价 — 角色对事件在确定性/愉悦度/控制感/目标相关等维度的系统评估",
        scientific_basis="Smith & Ellsworth (1985, JPSP); Bhattacharyya et al., CoRE (NeurIPS 2025)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=900,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        return f"""Smith & Ellsworth (1985) 16维认知评价。虚构角色模拟，忠实输出。

神经质={p.get('neuroticism',0.5):.1f}(高→威胁/低控制) 尽责性={p.get('conscientiousness',0.5):.1f}(高→努力/责任)
事件: {event.get('description','')}

16维: certainty(确定性) pleasantness(愉悦度,-1~1) attentional_activity anticipated_effort situational_control self_agency other_agency responsibility(self/other/circumstance) legitimacy(-1~1) goal_relevance goal_conduciveness(-1~1) coping_potential future_expectancy norm_compatibility(-1~1) perceived_obstacle urgency

范围: 默认0-1, 带(-1~1)的为-1到1。输出JSON:
{{"certainty":0.5,"pleasantness":0,"attentional_activity":0.5,"anticipated_effort":0.5,"situational_control":0.5,"self_agency":0.5,"other_agency":0.5,"responsibility":"self","legitimacy":0,"goal_relevance":0.5,"goal_conduciveness":0,"coping_potential":0.5,"future_expectancy":0.5,"norm_compatibility":0,"perceived_obstacle":0.5,"urgency":0.5,"appraisal_profile":"","appraisal_emotion_link":"","cognitive_vulnerability":"","activation_relevance":0.5}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "appraisal_profile": "标准认知评价",
            "certainty": 0.5,
            "pleasantness": 0.0,
            "attentional_activity": 0.5,
            "anticipated_effort": 0.5,
            "control": 0.5,
            "situational_control": 0.5,
            "other_agency": 0.5,
            "self_agency": 0.5,
            "responsibility": "不确定",
            "appraisal_emotion_link": "评价模式驱动情感反应",
            "cognitive_vulnerability": 0.5,
            "activation_relevance": 0.5,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
