"""Sternberg 爱情三角 Skill — Layer 3"""
from .base import BaseSkill, SkillMeta

class SternbergSkill(BaseSkill):
    meta = SkillMeta(
        name="sternberg_triangle", domain="psychology", layer=3,
        description="分析关系的亲密/激情/承诺三维平衡",
        scientific_basis="Sternberg (1986) — Triangular Theory of Love",
        scientific_rating=4, trigger_conditions=["romantic"], estimated_tokens=400, can_parallel=True,
    )

    def build_prompt(self, character_state: dict, event: dict, context: dict) -> str:
        return f"""你是Sternberg爱情三角理论专家。当前互动: {event.get('description', '')}

三维度:
- 亲密(Intimacy): 情感连接、分享、理解
- 激情(Passion): 身体吸引、浪漫渴望
- 承诺(Commitment): 维持关系的决定

组合:
- 只有激情=迷恋 / 只有亲密=喜欢 / 只有承诺=空洞的爱
- 亲密+激情=浪漫的爱 / 亲密+承诺=伴侣的爱 / 激情+承诺=愚蠢的爱
- 三者皆有=完整的爱

输出 JSON:
{{"intimacy": "0.0-1.0",
 "passion": "0.0-1.0",
 "commitment": "0.0-1.0",
 "love_type": "当前爱情类型",
 "strongest_dimension": "最强维度",
 "weakest_dimension": "最弱维度",
 "trend": "维度变化趋势",
 "triangle_description": "三角形状描述（一句话）"}}"""

    def parse_output(self, raw_output: str) -> dict:
        from .base import extract_json
        result = extract_json(raw_output)
        return result if result else {"love_type": "未定义"}
