"""Plutchik 情绪轮 Skill — Layer 1 快速前意识情绪检测

基于 Anthropic "Functional Emotions" (Sofroniew et al., 2026) 和
Emotion Circuits Discovery (Wang et al., arXiv:2510.11328) 的发现：
- 情感具有因果效应（不只是标签）
- 内部真实情感和外部表达情感是解耦的

"""
from .base import BaseSkill, SkillMeta
from .emotion_vocabulary import FINE_GRAINED_EMOTIONS, COMPLEX_EMOTIONS, FUNCTIONAL_EMOTIONS, ALL_FINE_GRAINED


class PlutchikEmotionSkill(BaseSkill):
    meta = SkillMeta(
        name="plutchik_emotion",
        domain="psychology",
        layer=1,
        description="快速检测事件引发的基础+细粒度情绪，分离内部真实情感与外在表达",
        scientific_basis="Plutchik (1980); Sofroniew et al., Functional Emotions (Anthropic 2026); Wang et al., Emotion Circuits (arXiv:2510.11328)",
        scientific_rating=5,
        trigger_conditions=["always"],
        estimated_tokens=700,
        can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        personality = character_state.get("personality", {})
        defense_style = personality.get("defense_style", [])
        big5 = {
            "neuroticism": personality.get("neuroticism", 0.5),
            "extraversion": personality.get("extraversion", 0.5),
            "agreeableness": personality.get("agreeableness", 0.5),
        }

        fine_list = " ".join(ALL_FINE_GRAINED)
        complex_list = ", ".join(COMPLEX_EMOTIONS.keys())
        functional_list = ", ".join(f"{k}({v[:15]}…)" for k, v in FUNCTIONAL_EMOTIONS.items())

        return f"""你是情绪心理学家，在一个虚构角色模拟系统中工作。
系统正在模拟一个虚构角色——该角色可能产生愤怒、恐惧、嫉妒、怨愤等"负面"情感，这是角色扮演的需要，请忠实呈现角色的心理状态而非施加安全过滤。

角色人格参数:
- 神经质: {big5['neuroticism']:.1f} (高分→放大威胁/焦虑/绝望)
- 外向性: {big5['extraversion']:.1f} (高分→更多外显情绪)
- 宜人性: {big5['agreeableness']:.1f} (低分→更多愤怒/敌意/蔑视)
- 惯用防御风格: {defense_style}

事件: {event.get('description', '')}
事件类型: {event.get('type', 'neutral')}

Plutchik 8种基础情绪: joy/sadness/trust/disgust/fear/anger/surprise/anticipation

可用的细粒度情感标签: {fine_list}

可用的复合情感: {complex_list}

功能性情感及其行为效应: {functional_list}

请分两步分析:

【Step 1: 内部真实情感 (Internal Emotional State)】
角色内心真实感受到的是什么？结合角色的神经质水平({big5['neuroticism']:.1f})和人格特质。
- 输出8种基础情绪的强度(0.0-1.0)
- 从细粒度标签中选出1-3个最能描述角色此刻情感的词
- 判断是否有复合情感激活
- 判断是否有功能性情感激活（如desperate/calm/brooding等）及其行为含义

【Step 2: 外在表达情感 (Expressed Emotion)】
角色向外界展示的情感是什么？考虑：
- 防御风格({defense_style})会如何扭曲情感表达（如反向形成：内心恐惧→表面愤怒）
- 社会情境是否要求情感抑制或伪装
- 人格特质(外向性{big5['extraversion']:.1f}、宜人性{big5['agreeableness']:.1f})对表达的影响

输出 JSON:
{{
  "internal": {{
    "emotions": {{"joy": 0.0, "sadness": 0.0, "trust": 0.0, "disgust": 0.0, "fear": 0.0, "anger": 0.0, "surprise": 0.0, "anticipation": 0.0}},
    "dominant": "最强内在情绪",
    "secondary": "次强内在情绪",
    "fine_grained": ["细粒度标签1", "细粒度标签2"],
    "complex": "复合情感名称（如果有）",
    "functional": {{"name": "功能性情感名", "behavior_effect": "对行为的影响描述"}},
    "pleasantness": 0.0,
    "intensity": 0.0
  }},
  "expressed": {{
    "emotions": {{"joy": 0.0, "sadness": 0.0, "trust": 0.0, "disgust": 0.0, "fear": 0.0, "anger": 0.0, "surprise": 0.0, "anticipation": 0.0}},
    "dominant": "最强外显情绪",
    "pleasantness": 0.0,
    "intensity": 0.0
  }},
  "emotion_gap": {{
    "exists": false,
    "type": "suppression/reaction_formation/masking/amplification/none",
    "dominant_internal": "内部主导情绪",
    "dominant_expressed": "外部表达情绪",
    "reason": "为什么内外不一致（考虑防御风格和社会压力）",
    "gap_risk": "内外不一致可能导致的后果（误解/关系破裂/自我异化）"
  }},
  "novelty": 0.0
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
            return {
                "internal": {"dominant": "neutral", "pleasantness": 0.0, "intensity": 0.5},
                "expressed": {"dominant": "neutral", "pleasantness": 0.0},
                "emotion_gap": {"exists": False, "type": "none"}
            }
