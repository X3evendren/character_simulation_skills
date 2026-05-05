"""SDT 自我决定理论 Skill — Layer 4"""
from .base import BaseSkill, SkillMeta

class SDTSkill(BaseSkill):
    meta = SkillMeta(
        name="sdt_motivation_analysis", domain="psychology", layer=4,
        description="分析角色的自主性/胜任感/归属感三需求满足状态",
        scientific_basis="Deci & Ryan (2000); Self++ (2026, arXiv)",
        scientific_rating=5, trigger_conditions=["reflective"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        m = character_state.get("motivation", {})
        return f"""你是SDT专家。事件: {event.get('description', '')}

三种内在需求:
- 自主性(Autonomy): 我感觉我的行为是我自己选择的 (当前: {m.get('autonomy_satisfaction',0.5):.1f})
- 胜任感(Competence): 我感觉我有能力做好 (当前: {m.get('competence_satisfaction',0.5):.1f})
- 归属感(Relatedness): 我感觉我和他人有连接 (当前: {m.get('relatedness_satisfaction',0.5):.1f})

三需求满足→内在动机→创造力+坚持+幸福
某种需求受阻→防御或补偿行为

输出 JSON:
{{"autonomy_impact": "事件如何影响自主性(-1.0-1.0)",
 "competence_impact": "事件如何影响胜任感(-1.0-1.0)",
 "relatedness_impact": "事件如何影响归属感(-1.0-1.0)",
 "most_threatened": "受威胁最大的需求",
 "compensation_behavior": "如果需求受阻，角色可能的补偿行为",
 "intrinsic_motivation_level": "0.0-1.0 当前内在动机水平"}}"""

    def parse_output(self, raw_output: str) -> dict:
        import json
        text = raw_output.strip().lstrip("```json").rstrip("```").strip()
        try: return json.loads(text)
        except json.JSONDecodeError: return {"intrinsic_motivation_level": 0.5}
