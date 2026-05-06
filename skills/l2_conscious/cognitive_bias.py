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
        return f"""认知偏差检测(Beck/Burns)。虚构角色，忠实输出。

偏好偏差: {biases} 神经质={neuroticism:.1f}
事件: {event.get('description','')}
偏差类型: 灾难化/读心术/非黑即白/情绪推理/过度概括/个人化/选择性抽象
JSON: {{"activated_biases":[{{"name":"","intensity":0.5,"thought":""}}],"alternative_interpretation":"","bias_summary":"","activation_relevance":0.5}}"""

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
