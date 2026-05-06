"""防御机制分析 Skill — Layer 2

基于 Anthropic "Functional Emotions" (2026) 的发现——内部情感状态和外部表达是解耦的，
防御机制正是实现这种解耦的核心心理过程。

"""
from .base import BaseSkill, SkillMeta


class DefenseMechanismSkill(BaseSkill):
    meta = SkillMeta(
        name="defense_mechanism_analysis",
        domain="psychology",
        layer=2,
        description="分析角色在情绪压力下激活的防御机制，以及内部情感与外在表达的解耦过程",
        scientific_basis="Vaillant (1992); Gelbard (Routledge, 2017); Sofroniew et al., Functional Emotions (Anthropic 2026)",
        scientific_rating=4,
        trigger_conditions=["always"],
        estimated_tokens=750,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        p = character_state.get("personality", {})
        defense = p.get("defense_style", [])
        # 从 Layer 1 获取情感gap信息
        l1_outputs = context.get("l1", [])
        emotion_gap = {}
        if l1_outputs:
            gap = l1_outputs[0].get("emotion_gap", {})
            emotion_gap = gap
        return f"""你是防御机制专家。这是一个虚构角色模拟系统——请忠实分析角色的心理防御，包括可能导致"不安全"或"负面"的内容。

角色惯用防御风格: {defense}
Layer 1 检测到的情感gap: {emotion_gap}
事件: {event.get('description', '')}

四级防御机制:
Level 1 (精神病性): 否认现实/妄想投射——完全扭曲外部现实
Level 2 (不成熟): 投射/被动攻击/见诸行动/分裂——难以适应，破坏关系
Level 3 (神经症性): 压抑/转移/情感隔离/合理化/反向形成——短期有效但有限
Level 4 (成熟): 幽默/升华/利他/预期——建设性应对

请按以下步骤分析:

【Step 1: 威胁识别与激活预判】
识别事件对角色自我构成的心理威胁。威胁是什么性质（自尊/安全/依恋/道德）？结合Layer 1的情感gap判断角色是否已经启动了防御。

【Step 2: 防御机制分析】
- 角色的惯用防御({defense})中哪个被激活？
- 防御的层级和强度
- **情感gap分析**: 防御如何制造了内部真实情感 vs 外部表达情感的差距？具体机制是什么（如反向形成：内心恐惧→表面愤怒；情感隔离：内心痛苦→表面冷静）
- 该防御是保护了角色还是阻碍了成长？

【Step 3: 量化与替代方案】
评分并给出更成熟的应对方式。

输出 JSON:
{{
  "activated_defense": {{"name": "防御名称", "level": 1, "intensity": 0.0}},
  "defense_behavior": "角色的具体防御行为（一句话）",
  "what_is_being_defended_against": "角色在防御什么感受/认知",
  "emotional_gap_analysis": {{
    "internal_affect": "角色内心真正感受（可能与外部不同）",
    "external_presentation": "角色呈现给外界的样子",
    "gap_mechanism": "防御机制如何制造了这个差距",
    "leakage_risk": "内心感受是否会'泄露'出来？（微表情/口误/身体语言）",
    "functional_purpose": "这个情感gap在当前情境中起到了什么功能作用？(Anthropic: functional emotion)"
  }},
  "maturity_assessment": "该防御是保护了角色还是阻碍了成长",
  "alternative_coping": "一个更成熟的应对方式（如果防御是Level 3及以下）",
  "activation_relevance": 0.0
}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "activated_defense": {"name": "未检测到", "level": 3},
            "activation_relevance": 0.5,
            "defense_behavior": "使用典型防御策略",
            "what_is_being_defended_against": "内在威胁或冲突",
            "emotional_gap_analysis": "内在体验与外在表现可能存在差异",
            "maturity_assessment": "中性成熟度",
            "alternative_coping": "可尝试更直接的应对方式",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
