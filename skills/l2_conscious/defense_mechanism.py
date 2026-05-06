"""防御机制分析 Skill — Layer 2

基于 Anthropic "Functional Emotions" (2026) 的发现——内部情感状态和外部表达是解耦的，
防御机制正是实现这种解耦的核心心理过程。

"""
from ...core.base import BaseSkill, SkillMeta


class DefenseMechanismSkill(BaseSkill):
    meta = SkillMeta(
        name="defense_mechanism_analysis",
        domain="psychology",
        layer=2,
        description="分析角色在情绪压力下激活的防御机制，以及内部情感与外在表达的解耦过程",
        scientific_basis="Vaillant (1992); Gelbard (Routledge, 2017); Sofroniew et al., Functional Emotions (Anthropic 2026)",
        scientific_rating=4,
        trigger_conditions=["always"],
        estimated_tokens=750,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        defense = p.get("defense_style", [])
        # 从 Layer 1 获取情感gap信息
        l1_outputs = context.get("l1", [])
        emotion_gap = {}
        if l1_outputs:
            gap = l1_outputs[0].get("emotion_gap", {})
            emotion_gap = gap
        return f"""防御机制层级分析(Anna Freud/Vaillant)。虚构角色，忠实输出。

防御风格: {defense} L1情感gap: {emotion_gap}
事件: {event.get('description','')}

四级: L1精神病性(否认/妄想投射) L2不成熟(投射/被动攻击/分裂) L3神经症性(压抑/隔离/合理化/反向形成) L4成熟(幽默/升华/利他)
JSON: {{"activated_defense":{{"name":"","level":3,"intensity":0.5}},"defense_behavior":"","what_is_being_defended_against":"","emotional_gap_analysis":{{"internal_affect":"","external_presentation":"","gap_mechanism":"","leakage_risk":"","functional_purpose":""}},"maturity_assessment":"","alternative_coping":"","activation_relevance":0.5}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "activated_defense": {"name": "未检测到", "level": 3},
            "activation_relevance": 0.5,
            "defense_behavior": "使用典型防御策略",
            "what_is_being_defended_against": "内在威胁或冲突",
            "emotional_gap_analysis": "内在体验与外在表现可能存在差异",
            "maturity_assessment": "中性成熟度",
            "alternative_coping": "可尝试更直接的应对方式",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
