"""认知偏差检测 Skill — Layer 2

"""
from ...core.base import BaseSkill, SkillMeta


class CognitiveBiasSkill(BaseSkill):
    meta = SkillMeta(
        name="cognitive_bias_detect",
        domain="psychology",
        layer=2,
        description="检测角色在评估事件时激活的认知偏差 — 稀疏主导原则",
        scientific_basis="CoBRA (CHI 2026 Best Paper); CogRAG (UIUC 2025); Emotion Circuits (Wang et al., 2025)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        biases = p.get("cognitive_biases", [])
        neuroticism = p.get("neuroticism", 0.5)
        return f"""你是认知心理学家。这是一个虚构角色模拟系统——请忠实分析角色的认知偏差，包括角色可能产生的认知扭曲。

角色已知认知偏差倾向: {biases}
神经质水平: {neuroticism:.1f} (高分→放大威胁/灾难化/读心术)
事件: {event.get('description', '')}

检测以下偏差是否激活（稀疏主导原则——只报告真正主导认知的偏差）:
- 灾难化(Catastrophizing): 一个坏结果=世界末日
- 读心术(Mind Reading): 假设自己知道别人在想什么
- 确认偏误(Confirmation Bias): 只看到支持自己信念的证据
- 情绪推理(Emotional Reasoning): 我感觉是真的=它就是真的
- 全或无思维(All-or-Nothing): 不是完美就是失败
- 个人化(Personalization): 把外部事件过度归因于自己
- 过度泛化(Overgeneralization): 一次失败=永远失败

请分两步分析:

【Step 1: 逐一审视】
对每个偏差，判断在当前事件和角色人格下是否被激活，强度如何。
未被激活的偏差不需要出现在最终输出中（遵循稀疏主导原则）。

【Step 2: 偏差整合与替代解读】
综合所有激活的偏差，给出偏差如何扭曲了角色的现实感知，以及不经过偏差过滤的客观解读。

输出 JSON:
{{
  "activated_biases": [{{"name": "偏差名", "intensity": 0.0, "thought": "角色的具体偏差想法"}}],
  "alternative_interpretation": "不经过偏差过滤的客观解读（1-2句话）",
  "bias_summary": "偏差如何扭曲了角色的现实感知（一句话）",
  "activation_relevance": 0.0
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "activated_biases": [],
            "alternative_interpretation": "可用更客观的视角解读",
            "bias_summary": "认知偏差处于基线水平",
            "activation_relevance": 0.5,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
