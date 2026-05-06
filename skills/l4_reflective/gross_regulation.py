"""Gross 情绪调节 Skill — Layer 4

基于 Anthropic "Functional Emotions" (2026) 的发现：
- 内部情感状态和外部表达是解耦的
- "Functional"情绪调节策略直接影响行为选择（如calm→道德行为，desperate→高风险行为）

"""
from ...core.base import BaseSkill, SkillMeta


class GrossRegulationSkill(BaseSkill):
    meta = SkillMeta(
        name="gross_emotion_regulation",
        domain="psychology",
        layer=4,
        description="分析角色使用的情绪调节策略及其对内部情感→外部表达的转换效果",
        scientific_basis="Gross (1998, 2015); Sofroniew et al., Functional Emotions (Anthropic 2026); RESORT (COLM 2024)",
        scientific_rating=4,
        trigger_conditions=["reflective", "conflict"],
        estimated_tokens=750,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        e = character_state.get("emotion", {})
        strategy = e.get("regulation_strategy", "")
        p = character_state.get("personality", {})
        # 收集前面各层的情感数据
        l1_data = context.get("l1", [{}])[0] if context.get("l1") else {}
        l2_data = context.get("l2", [{}])[0] if context.get("l2") else {}

        internal_emotion = l1_data.get("internal", {}).get("dominant", "未知")
        expressed_emotion = l1_data.get("expressed", {}).get("dominant", "未知")
        emotion_gap = l1_data.get("emotion_gap", {})

        return f"""情绪调节策略分析(Gross)。虚构角色，忠实输出。

策略: {strategy} 人格: N={p.get('neuroticism',0.5):.1f} A={p.get('agreeableness',0.5):.1f}
L1数据: {l1_data}
事件: {event.get('description','')}
策略: situation_selection/modification/attention_deployment/cognitive_change/response_modulation/expressive_suppression
JSON: {{"detected_strategy":"","internal_to_external_path":{{"internal":"","external":""}},"effectiveness":0.5,"cost":"","functional_emotion_shift":{{"from":"","to":""}},"alternative_strategy":"","long_term_impact":"","regulation_insight":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "detected_strategy": "no_regulation",
            "internal_to_external_path": "内在体验直接外化",
            "effectiveness": 0.5,
            "cost": "无显著代价",
            "functional_emotion_shift": "情感无显著变化",
            "alternative_strategy": "无需替代策略",
            "long_term_impact": "维持现状",
            "regulation_insight": "无需特别调节",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
