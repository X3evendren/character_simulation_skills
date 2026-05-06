"""Sternberg 爱情三角 Skill — Layer 3"""
from ...core.base import BaseSkill, SkillMeta

class SternbergSkill(BaseSkill):
    meta = SkillMeta(
        name="sternberg_triangle", domain="psychology", layer=3,
        description="分析关系的亲密/激情/承诺三维平衡",
        scientific_basis="Sternberg (1986) — Triangular Theory of Love",
        scientific_rating=4, trigger_conditions=["romantic"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""Sternberg爱情三角。互动: {event.get('description','')}
三维: intimacy(亲密) passion(激情) commitment(承诺) 类型: liking/infatuation/empty/romantic/companionate/fatuous/consummate
JSON: {{"intimacy":0.5,"passion":0.5,"commitment":0.5,"love_type":"","strongest_dimension":"","weakest_dimension":"","trend":"","triangle_description":""}}"""

    def parse_output(self, raw_output: str) -> dict:
        from ...core.base import extract_json
        result = extract_json(raw_output)
        defaults = {
            "love_type": "未定义",
            "intimacy": 0.5,
            "passion": 0.5,
            "commitment": 0.5,
            "strongest_dimension": "unknown",
            "weakest_dimension": "unknown",
            "trend": "stable",
            "triangle_description": "关系特征待确定",
        }
        if not result:
            return defaults
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
