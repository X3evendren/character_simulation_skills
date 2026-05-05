"""DiriGent 理想世界分析 Skill — Layer 3/4

基于 DiriGent (ETH Zurich, AAAI AIIDE 2025):
- 角色有"理想世界"表征（values, desired relationships, goals）
- LLM分析理想世界 vs 感知现实世界的张力
- 张力驱动信念动机行为

这个skill分析角色"想要的"和"得到的"之间的差距——驱动角色行动的根本动力。
"""
from .base import BaseSkill, SkillMeta


class DiriGentSkill(BaseSkill):
    meta = SkillMeta(
        name="dirigent_world_tension",
        domain="psychology",
        layer=3,
        description="分析角色理想世界与现实感知的张力 — 驱动角色行动的根本动机分析",
        scientific_basis="DiriGent (ETH, AAAI AIIDE 2025); Cognitive Dissonance (Festinger 1957); Self-Discrepancy Theory (Higgins 1987)",
        scientific_rating=4,
        trigger_conditions=["reflective", "conflict", "romantic"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        ideal = character_state.get("ideal_world", {})
        p = character_state.get("personality", {})
        m = character_state.get("motivation", {})

        return f"""你是角色动机分析专家。这是一个虚构角色模拟系统，请忠实分析角色的内心张力。

角色理想世界 (Ideal World):
- 理想自我: {ideal.get('ideal_self', '未定义')}
- 理想关系: {ideal.get('ideal_relationships', '未定义')}
- 理想秩序: {ideal.get('ideal_order', '未定义')}
- 核心价值: {ideal.get('core_values', [])}
- 追求目标: {m.get('current_goal', '未定义')}

当前事件: {event.get('description', '')}

请按以下步骤分析理想世界与现实世界的张力:

【Step 1: 现实感知】
角色在当前事件中感知到的现实是什么？事件中的事实与角色的理想世界在哪些维度上存在差距？

【Step 2: 张力计算】
量化以下维度的理想-现实差距（0.0=无差距/完全一致, 1.0=极端差距/完全背离）:
- 自我差距 (Self-Discrepancy): 角色"实际是谁" vs "想成为谁"
- 关系差距 (Relationship Gap): 角色"实际的关系" vs "想要的关系"
- 秩序差距 (Order Gap): 角色"世界实际如何运作" vs "世界应该如何运作"
- 价值冲突 (Value Conflict): 事件是否与角色的核心价值冲突？
- 权力差距 (Power Gap): 角色在当前情境中的实际权力 vs 理想权力位置

【Step 3: 张力驱动的行为预测】
基于差距分析，预测角色会产生什么行为来缩小差距:
- 同化 (Assimilation): 试图改变现实以适应理想
- 顺应 (Accommodation): 调整理想以适应现实
- 回避 (Avoidance): 逃避差距的存在
- 对抗 (Confrontation): 攻击制造差距的源头

输出 JSON:
{{
  "perceived_reality": "角色感知到的现实（一句话）",
  "tension_dimensions": {{
    "self_discrepancy": {{"gap": 0.0, "actual": "角色此刻是谁", "ideal": "角色想成为谁", "pain": 0.0}},
    "relationship_gap": {{"gap": 0.0, "actual": "实际关系状态", "ideal": "想要的关系", "pain": 0.0}},
    "order_gap": {{"gap": 0.0, "actual": "世界如何运作", "ideal": "世界应该如何", "pain": 0.0}},
    "value_conflict": {{"gap": 0.0, "violated_value": "被冒犯的价值", "pain": 0.0}},
    "power_gap": {{"gap": 0.0, "actual_power": 0.0, "ideal_power": 0.0, "pain": 0.0}}
  }},
  "dominant_tension": "最主要的张力维度",
  "overall_cognitive_dissonance": 0.0,
  "coping_strategy": "assimilation/accommodation/avoidance/confrontation",
  "predicted_action": "角色缩小差距的具体行为（一句话）",
  "long_term_arc_impact": "如果差距持续存在，对角色发展的长期影响"
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"overall_cognitive_dissonance": 0.5, "coping_strategy": "unknown"}
