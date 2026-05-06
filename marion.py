"""马里翁情爱现象学 Skill — Layer 3"""
from .base import BaseSkill, SkillMeta

class MarionSkill(BaseSkill):
    meta = SkillMeta(
        name="marion_erotic_phenomenology", domain="psychology", layer=3,
        description="从内部体验分析爱 — 爱的先行、爱欲还原、他人爱欲化、誓言",
        scientific_basis="Marion, Le phenomene erotique (2003); L'individuation par l'amour (2006)",
        scientific_rating=4, trigger_conditions=["romantic"], estimated_tokens=600, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是马里翁情爱现象学专家。当前互动: {event.get('description', '')}

核心概念:
- 爱的先行(l'avance): 谁先迈出那一步？不等回报地先去爱？
- 爱欲还原: 三个问题 — "有人爱我吗?"→"我的存在对谁有好处?"→"我能先去爱吗?"
- 他人爱欲化: 在被对方凝视时，身体如何变得爱欲化（脸红/心跳/呼吸急促）
- 誓言: 爱需要时间上的承诺——"我的爱不依赖当下的感觉而持续"
- 礼物逻辑 vs 交换逻辑: 爱是gift（不计算回报）还是bargain（讨价还价）?

输出 JSON:
{{"who_is_advancing": "A/B/neither/both",
 "erotic_reduction_stage": {{"stage": "1/2/3", "description": "当前阶段描述"}},
 "body_under_gaze": "被凝视时的身体反应",
 "oath_status": "active/threatened/broken/never_formed",
 "logic_type": "gift/exchange/bargain",
 "what_is_unsaid": "双方都在想但没有说出口的东西",
 "erotic_tension": "当前的爱欲张力描述（一句话）"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "who_is_advancing": "neither",
            "erotic_reduction_stage": "undefined",
            "body_under_gaze": "none",
            "oath_status": "unspoken",
            "logic_type": "undefined",
            "what_is_unsaid": "情感未完全外显",
            "erotic_tension": 0.3,
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
