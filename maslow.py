"""Maslow 需求层次 Skill — Layer 4"""
from .base import BaseSkill, SkillMeta

class MaslowSkill(BaseSkill):
    meta = SkillMeta(
        name="maslow_need_stack", domain="psychology", layer=4,
        description="分析角色当前的需求层次和动机优先级",
        scientific_basis="Maslow (1943, 1954); LLM Agent自发人格研究 (Fujiyama 2025)",
        scientific_rating=4, trigger_conditions=["reflective"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是Maslow需求层次专家。事件: {event.get('description', '')}

五层需求(高→低):
5 自我实现: 成为我能成为的人
4 尊重: 被认可/成就/地位
3 归属: 被爱/属于群体
2 安全: 健康/住所/稳定
1 生理: 食物/水/睡眠

波浪模型: 下层需求满足后上层才驱动行为。

输出 JSON:
{{"current_dominant": "1-5 当前最迫切的需求层次",
 "need_stack": [{{"level": 1-5, "name": "需求名", "satisfaction": "0.0-1.0", "urgency": "0.0-1.0"}}],
 "blocked_needs": ["被阻碍的需求"],
 "deficiency_vs_growth": "deficiency/growth motivation",
 "behavior_explanation": "当前行为由哪层需求驱动（一句话）"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"current_dominant": 3}
