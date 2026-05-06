"""
心理理论 (Theory of Mind) Skill — Layer 3

基于 MetaMind (NeurIPS 2025 Spotlight):
- 生成关于其他角色心理状态的假设 (信念/欲望/意图/情感)
- 根据情境规范和文化背景验证假设
- 为回应生成提供社交智能输入

与现有 L3 社交技能互补: Gottman 分析互动模式, Sternberg 分析关系维度,
ToM 分析角色对他人的心理状态推理。
"""
from ...core.base import BaseSkill, SkillMeta, SkillResult


class TheoryOfMindSkill(BaseSkill):
    meta = SkillMeta(
        name="theory_of_mind",
        domain="psychology",
        layer=3,
        description="分析角色对他人心理状态的推理 (信念/欲望/意图/情感)",
        scientific_basis="MetaMind ToM Architecture (NeurIPS 2025); Premack & Woodruff (1978)",
        scientific_rating=5,
        trigger_conditions=["social", "romantic", "conflict", "authority"],
        estimated_tokens=500,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        personality = character_state.get("personality", {})
        name = character_state.get("name", "角色")
        participants = event.get("participants", [])
        other_names = [p.get("name", "某人") for p in participants if p.get("name") != name]

        neuroticism = personality.get("neuroticism", 0.5)
        agreeableness = personality.get("agreeableness", 0.5)
        attachment = personality.get("attachment_style", "secure")

        # 获取已有分析
        l0 = context.get("l0", [{}])[0] if context.get("l0") else {}
        interpretation_bias = l0.get("interpretation_bias", "从自身视角解读")
        l1 = context.get("l1", [{}])[0] if context.get("l1") else {}
        dominant_emotion = l1.get("internal", {}).get("dominant", "neutral")

        biases = personality.get("cognitive_biases", [])
        bias_hint = ""
        if "读心术" in biases:
            bias_hint = "注意：角色有读心术偏差——倾向于假设自己知道别人在想什么（通常是负面的）。"
        elif "个人化" in biases:
            bias_hint = "注意：角色有人个化偏差——倾向于将外部事件归因于自己。"

        prompt = f"""{name}正在与{'、'.join(other_names) if other_names else '他人'}互动。

【角色心理特征】
- 神经质: {neuroticism:.1f} (高分=更容易负面解读他人意图)
- 宜人性: {agreeableness:.1f} (低分=更不信任他人动机)
- 依恋风格: {attachment}
- 当前主导情绪: {dominant_emotion}
- 认知解读偏置: {interpretation_bias}
{bias_hint}

【事件】
{event.get('description', '')}

请分析{name}对{'、'.join(other_names) if other_names else '他人'}的心理状态推理。分三步:

Step 1: 心理状态假设 (ToM Agent 启发)
- {name}认为{'、'.join(other_names) if other_names else '对方'}此刻在想什么？
- {name}认为对方的意图是什么？
- {name}认为对方对自己有什么感觉？

Step 2: 现实检验 (Domain Agent 启发)
- {name}的假设是否基于证据还是投射？
- 有什么被忽略的替代解释？
- 角色的人格和情绪如何扭曲了判断？

Step 3: 行为影响 (Response Agent 启发)
- 这些 ToM 推理将如何影响{name}接下来的行为？

输出 JSON:
{{
  "perceived_thoughts": ["对方可能在想..."],
  "perceived_intentions": ["对方意图..."],
  "perceived_feelings_toward_self": "对方对自己的情感态度",
  "evidence_basis": "strong/moderate/weak/projection",
  "alternative_interpretations": ["被忽略的替代解释"],
  "distortion_factors": ["人格/情绪导致的判断扭曲"],
  "behavioral_influence": "ToM推理对角色行为的预期影响",
  "ToM_accuracy_estimate": "角色ToM推理的估计准确度 (0.0-1.0)"
}}"""
        return prompt

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "perceived_thoughts": [],
            "perceived_intentions": [],
            "perceived_feelings_toward_self": "不确定",
            "evidence_basis": "moderate",
            "alternative_interpretations": [],
            "distortion_factors": [],
            "behavioral_influence": "ToM推理将影响角色行为",
            "ToM_accuracy_estimate": 0.5,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
