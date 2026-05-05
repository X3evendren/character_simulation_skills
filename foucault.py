"""福柯权力分析 Skill — Layer 3

"""
from .base import BaseSkill, SkillMeta


class FoucaultSkill(BaseSkill):
    meta = SkillMeta(
        name="foucauldian_power_analysis",
        domain="psychology",
        layer=3,
        description="分析权力如何塑造角色的可思考范围 — 规训/全景敞视/主体化/权力知识",
        scientific_basis="Foucault: Discipline and Punish (1975), History of Sexuality (1976); Functional Emotions (Anthropic 2026)",
        scientific_rating=5,
        trigger_conditions=["authority", "conflict"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是福柯权力分析专家。这是一个虚构角色模拟系统——请忠实分析权力结构，包括权力不对等、压迫、抵抗等可能涉及敏感话题的内容。

事件: {event.get('description', '')}
涉及人员: {event.get('participants', [])}

核心概念:
- 规训权力: 身体如何被训练、排名、考试、时间表管理
- 全景敞视: 不对称的凝视——少数人看多数人，被看者内化凝视
- 权力/知识: 谁定义"真理"?"正道/魔道"不是自然分类，是权力制造的
- 主体化: 角色被塑造成什么主体? 他正在把自己塑造成什么?
- 性经验史: 性不是被压制的，是被不断谈论/分类/诊断/管理的
- 生命权力: 管理出生率/死亡率/健康/寿命的权力

请分两步分析:

【Step 1: 权力场域结构分析】
识别事件中权力运作的形式，逐一审视六个福柯概念。

【Step 2: 话语位置与抵抗】
判定角色在权力话语中的位置和可能的抵抗形式。

输出 JSON:
{{
  "disciplinary_technologies": ["角色身体上运作的规训技术"],
  "internalized_gaze": "角色内化了谁的凝视?",
  "truth_regime_conflict": "角色与'官方真理'的张力",
  "subjectivation_tension": "被塑造的身份 vs 自己塑造的身份",
  "resistance_form": "角色的抵抗形式（如果有）",
  "power_productive_effect": "权力不只是限制——它让角色能够做什么?",
  "discourse_position": "角色在当前话语中的位置 (dominated/dominant/resisting/negotiating)",
  "power_intensity": 0.0,
  "activation_relevance": 0.0
}}"""

    def parse_output(self, raw_output: str) -> dict:
        import re
        import json
        text = raw_output.strip()
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"subjectivation_tension": "无法解析"}
