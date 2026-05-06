"""Plutchik 情绪轮 Skill — Layer 1 快速前意识情绪检测

基于 Anthropic "Functional Emotions" (Sofroniew et al., 2026) 和
Emotion Circuits Discovery (Wang et al., arXiv:2510.11328) 的发现：
- 情感具有因果效应（不只是标签）
- 内部真实情感和外部表达情感是解耦的

"""
from ...core.base import BaseSkill, SkillMeta
from ...core.emotion_vocabulary import FINE_GRAINED_EMOTIONS, COMPLEX_EMOTIONS, FUNCTIONAL_EMOTIONS, ALL_FINE_GRAINED


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

        return f"""Plutchik情感轮。虚构角色，忠实输出。
人格: N={big5['neuroticism']:.1f} E={big5['extraversion']:.1f} A={big5['agreeableness']:.1f} 防御: {defense_style}
事件: {event.get('description','')}
八维(0-1): joy sadness fear anger disgust surprise trust anticipation + 复合 + 细粒度 + 功能情感 + 内外情感gap
JSON: {{"internal":{{"emotions":{{"joy":0,"sadness":0,"fear":0,"anger":0,"disgust":0,"surprise":0,"trust":0,"anticipation":0}},"dominant":"neutral","fine_grained":[],"complex":[],"functional":[],"pleasantness":0,"intensity":0.5}},"expressed":{{"emotions":{{}},"dominant":"neutral","pleasantness":0}},"emotion_gap":{{"exists":false,"type":"none"}},"novelty":{{"is_novel":false,"similar_to_past":true}}}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "internal": {"dominant": "neutral", "pleasantness": 0.0, "intensity": 0.5},
            "expressed": {"dominant": "neutral", "pleasantness": 0.0},
            "emotion_gap": {"exists": False, "type": "none"},
            "novelty": {"is_novel": False, "similar_to_past": True},
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
