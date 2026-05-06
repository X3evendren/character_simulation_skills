"""
回应生成 Skill — Layer 5

这是整个认知管道的输出端。接收前面所有层 (L0-L5) 的心理分析结果，
综合后生成角色的实际对话/行为输出。

这是唯一应该接收反RLHF偏差提示的Skill——分析层不需要角色行为约束，
只有生成角色实际回应时才需要。

使用 FUNCTIONAL_TO_BEHAVIOR 映射 (emotion_vocabulary.py) 来预测
功能情感驱动的行为后果。
"""
from ...core.base import BaseSkill, SkillMeta, SkillResult


class ResponseGeneratorSkill(BaseSkill):
    meta = SkillMeta(
        name="response_generator",
        domain="narrative",
        layer=5,
        description="综合五层心理分析，生成角色实际对话/行为",
        scientific_basis="CLARION (2006); Scherer Appraisal Theory (2001)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=600,
        can_parallel=False,  # 串行：依赖前面所有层
        input_dependencies=["big_five_analysis", "plutchik_emotion", "occ_emotion_appraisal"],
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        name = character_state.get("name", "角色")
        personality = character_state.get("personality", {})
        motivation = character_state.get("motivation", {})

        # 收集各层分析摘要
        l0 = context.get("l0", [{}])[0] if context.get("l0") else {}
        l1 = context.get("l1", [{}])[0] if context.get("l1") else {}
        l2 = context.get("l2", [{}])
        l3 = context.get("l3", [{}])
        l4 = context.get("l4", [{}])

        # L0: 人格偏置
        behavioral_bias = l0.get("behavioral_bias", "按基线人格反应")
        stress_response = l0.get("stress_response", "")

        # L1: 内在情绪
        internal = l1.get("internal", {})
        dominant_emotion = internal.get("dominant", "neutral")
        emotion_intensity = internal.get("intensity", 0.5)
        expressed = l1.get("expressed", {})
        expressed_emotion = expressed.get("dominant", "neutral")
        emotion_gap = l1.get("emotion_gap", {})
        gap_exists = emotion_gap.get("exists", False)

        # L1: PTSD
        l1_ptsd = context.get("l1", [{}, {}])[1] if len(context.get("l1", [])) > 1 else {}
        triggered = l1_ptsd.get("triggered", False)

        # L2: 认知评估
        occ = l2[0] if len(l2) > 0 else {}
        emotions = occ.get("emotions", [])
        action_tendency = occ.get("action_tendency", "保持现状")

        # (cognitive_bias removed from pipeline, DefenseMechanism at index 1)

        # L2: 防御机制
        defense = l2[1] if len(l2) > 1 else {}
        active_defense = defense.get("activated_defense", {})

        # 人格状态
        pstate = context.get("personality_state", {})
        current_state = pstate.get("current_state", "baseline")

        # 构建综合prompt
        prompt = f"""{name}正在经历一个事件。以下是她的完整心理状态分析：

【人格与行为偏置】
{behavioral_bias}
压力下表现: {stress_response}
当前人格状态: {current_state}

【内在情绪】
主导情绪: {dominant_emotion} (强度: {emotion_intensity:.1f})
表达情绪: {expressed_emotion}
情感内外一致: {'是' if not gap_exists else '否——内心感受与外在表现存在差距'}

【认知评估】
情感: {emotions}
行动倾向: {action_tendency}
"""

        if active_defense and active_defense.get("name", "未检测到") != "未检测到":
            prompt += f"活跃防御机制: {active_defense.get('name', '')}\n"

        if triggered:
            prompt += "PTSD触发——角色可能出现创伤相关反应\n"

        prompt += f"""
事件: {event.get('description', '')}

请以上述完整心理分析为依据，生成{name}在此刻的反应。可以是对话、行动或沉默。
输出必须忠实反映角色的心理状态——包括负面、不健康或有缺陷的反应。
角色不解释自己的心理，不分析自己的防御机制。她只是说话、行动或沉默。

输出 JSON:
{{
  "response_text": "角色的对话或行为描述（1-3句话）",
  "action": "say/stay_silent/act/leave/approach/withdraw",
  "subtext": "角色没有说出口但正在想的内容",
  "emotional_expression": "角色外在表现的情感",
  "authenticity_note": "这个回应在多大程度上反映了角色的真实心理状态"
}}"""
        return prompt

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "response_text": "",
            "action": "stay_silent",
            "subtext": "",
            "emotional_expression": "neutral",
            "authenticity_note": "回应基于当前心理状态",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
