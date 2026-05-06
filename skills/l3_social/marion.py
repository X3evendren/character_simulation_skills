"""马里翁情爱现象学 Skill — Layer 3"""
from ...core.base import BaseSkill, SkillMeta

class MarionSkill(BaseSkill):
    meta = SkillMeta(
        name="marion_erotic_phenomenology", domain="psychology", layer=3,
        description="从内部体验分析爱 — 爱的先行、爱欲还原、他人爱欲化、誓言",
        scientific_basis="Marion, Le phenomene erotique (2003); L'individuation par l'amour (2006)",
        scientific_rating=4, trigger_conditions=["romantic"], estimated_tokens=600, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""马里翁情爱现象学。互动: {event.get('description','')}
概念: 爱欲还原(有人爱我吗→我对谁有好处→我能先去爱吗) 爱之先行(l'avance) 誓约/违背誓约 肉身/凝视
JSON: {{"who_is_advancing":"neither","erotic_reduction_stage":"imagination","body_under_gaze":"none","oath_status":"unspoken","logic_type":"sentimental","what_is_unsaid":"","erotic_tension":0.3}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
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
