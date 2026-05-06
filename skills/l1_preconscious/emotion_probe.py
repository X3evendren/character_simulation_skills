"""
情感探针 Skill — Layer 1

检测 LLM 文本输出中隐含的细粒度情感信号和功能情感。
与 plutchik_emotion (显式情感分析) 并行运行。

基于: Anthropic 171 情感向量研究 (Sofroniew et al., 2026)
       Quantitative Introspection in LLMs (Martorell et al., TMLR 2026)
"""
from ...core.base import BaseSkill, SkillMeta, SkillResult


class EmotionProbeSkill(BaseSkill):
    meta = SkillMeta(
        name="emotion_probe",
        domain="psychology",
        layer=1,
        description="检测 LLM 输出中隐含的细粒度情感信号和功能情感",
        scientific_basis="Anthropic 171 Functional Emotions (2026); Quantitative Introspection (TMLR 2026)",
        scientific_rating=4,
        trigger_conditions=["always"],
        estimated_tokens=400,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        personality = character_state.get("personality", {})
        neuroticism = personality.get("neuroticism", 0.5)
        extraversion = personality.get("extraversion", 0.5)
        agreeableness = personality.get("agreeableness", 0.5)

        # 从上下文获取已有的 Plutchik 分析或事件信息
        l0 = context.get("l0", [{}])[0] if context.get("l0") else {}
        behavioral_bias = l0.get("behavioral_bias", "")

        prompt = f"""你是情感信号检测专家。分析当前事件中角色可能隐含的情感信号。

角色人格基线: 神经质={neuroticism:.1f}, 外向性={extraversion:.1f}, 宜人性={agreeableness:.1f}
行为偏置: {behavioral_bias}
事件: {event.get('description', '')}

请在以下维度上评估角色可能隐含但未明说的情感信号:

【细粒度情感】
从以下类别中检测最可能存在的 3-5 种细粒度情感:
- 喜悦类: 满足/自豪/欣慰/释然/雀跃
- 悲伤类: 失落/惆怅/忧郁/沮丧/孤独/心碎
- 恐惧类: 焦虑/不安/恐慌/无助/窒息感
- 愤怒类: 恼怒/怨恨/嫉妒/委屈/隐忍的怒火
- 厌恶类: 反感/鄙夷/不屑/轻蔑/嫌弃
- 信任类: 依赖/安心/钦佩/依恋/温暖
- 惊奇类: 震惊/困惑/茫然/好奇/错愕
- 期待类: 希望/渴望/忐忑/急切/患得患失

【功能情感】
检测角色可能处于的功能情感状态 (选择最可能的 1-2 种):
- desperate (绝望的/不择手段)
- caring (关怀的/自我牺牲)
- defiant (反抗的/挑战权威)
- submissive (顺从的/边界退让)
- detached (疏离的/情感隔离)
- yearning (渴望的/冒险追求)
- numb (麻木的/无反应)
- wary (警惕的/过度防御)

输出 JSON:
{{
  "fine_grained": [{{"emotion": "情感名", "intensity": 0.0-1.0, "evidence": "文本证据"}}],
  "functional": [{{"emotion": "功能情感名", "intensity": 0.0-1.0, "behavioral_consequence": "可能的行为后果"}}],
  "primary_undisclosed_emotion": "角色最可能隐藏的情感",
  "emotional_complexity": "simple/moderate/complex/turbulent"
}}"""
        return prompt

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "fine_grained": [],
            "functional": [],
            "primary_undisclosed_emotion": "未检测到",
            "emotional_complexity": "moderate",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
