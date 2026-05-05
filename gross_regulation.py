"""Gross 情绪调节 Skill — Layer 4

基于 Anthropic "Functional Emotions" (2026) 的发现：
- 内部情感状态和外部表达是解耦的
- "Functional"情绪调节策略直接影响行为选择（如calm→道德行为，desperate→高风险行为）

"""
from .base import BaseSkill, SkillMeta


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

        return f"""你是情绪调节专家。这是一个虚构角色模拟系统，请忠实分析角色的情绪调节过程，包括角色可能产生的任何"负面"或不安全的情感状态。

角色惯用调节策略: {strategy or '未知'}

当前情绪状态（来自Layer 1+2）:
- 内部真实情感: {internal_emotion}
- 外部表达情感: {expressed_emotion}
- 情感gap: {emotion_gap}

事件: {event.get('description', '')}

Gross 情绪调节过程模型（五策略，按时序排列）:
1. 情境选择: 角色是否主动选择/避免引发特定情绪的情境？
2. 情境修正: 角色是否改变所处情境来调整情绪影响？
3. 注意力部署: 角色是否转移注意力/反刍/专注其他事物？
4. 认知重评(Cognitive Reappraisal): 角色是否重新解释事件的意义？(RESORT框架: 最有效的策略)
5. 表达抑制(Expressive Suppression): 角色是否抑制情绪的外在表达？（最消耗）

请按以下步骤分析:

【Step 1: 内部→外部情感转换路径】
追踪角色如何从内部情感({internal_emotion})转换到外部表达({expressed_emotion})：
- 使用的是Gross五策略中的哪一个/哪几个？
- 转换是成功还是失败？（是否有"情感泄露"？）
- 策略在哪个时间点介入？（情绪生成前/情绪生成中/情绪表达时）

【Step 2: 功能性情感调节分析（Anthropic 2026框架）】
- 该调节策略将角色的"功能性情感状态"推向了什么方向？
  (如：重评后从desperate→calm→道德行为增强；或抑制失败→desperate加剧→高风险行为)
- 调节策略对行为的因果影响是什么？

【Step 3: 长短评估】
评估当前策略的有效性、代价和长期影响。

输出 JSON:
{{
  "internal_to_external_path": {{
    "internal_origin": "初始内部情感",
    "regulation_strategies_used": ["使用的策略"],
    "intervention_timing": "antecedent_focused/response_focused/both",
    "external_result": "最终外部表达",
    "transformation_success": true,
    "leakage_signs": "情感泄露迹象（如果有）"
  }},
  "detected_strategy": "主导调节策略",
  "effectiveness": 0.0,
  "cost": "该策略的代价（认知消耗/社会代价/长期健康影响）",
  "functional_emotion_shift": {{
    "from_state": "调节前的功能性情感状态",
    "to_state": "调节后的功能性情感状态",
    "behavioral_impact": "情感状态变化导致的行为倾向变化",
    "causal_effect": "对角色后续行为的因果影响（参考Anthropic functional emotions框架）"
  }},
  "alternative_strategy": "一个更有效的替代策略（基于RESORT重评框架）",
  "long_term_impact": "长期使用该策略对角色心理健康的影响",
  "regulation_insight": "角色为什么选择这种策略（与人格/图式的关联）"
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"detected_strategy": "未知"}
