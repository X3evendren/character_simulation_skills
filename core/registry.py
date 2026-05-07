"""
Skill 注册表 — 管理 37 个模型的注册、发现和触发条件匹配
"""
from __future__ import annotations

from typing import Optional
from .base import BaseSkill, SkillMeta


class SkillRegistry:
    """Skill 注册表"""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._by_layer: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
        self._by_domain: dict[str, list[str]] = {
            "psychology": [], "social_science": [], "world_science": [], "narrative": []
        }
        self._by_trigger: dict[str, list[str]] = {}

    def register(self, skill: BaseSkill) -> None:
        name = skill.meta.name
        self._skills[name] = skill
        self._by_layer[skill.meta.layer].append(name)
        self._by_domain[skill.meta.domain].append(name)
        for trigger in skill.meta.trigger_conditions:
            self._by_trigger.setdefault(trigger, []).append(name)

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def list_all(self) -> list[str]:
        return list(self._skills.keys())

    def list_by_layer(self, layer: int) -> list[str]:
        return self._by_layer.get(layer, [])

    def list_by_domain(self, domain: str) -> list[str]:
        return self._by_domain.get(domain, [])

    def select_by_triggers(self, triggers: list[str]) -> list[str]:
        """根据触发条件匹配 Skill"""
        selected: set[str] = set()
        for t in triggers:
            selected.update(self._by_trigger.get(t, []))
        return list(selected)

    @property
    def skill_count(self) -> int:
        return len(self._skills)


# 全局单例
_registry: Optional[SkillRegistry] = None
_builtins_registered: bool = False


def get_registry() -> SkillRegistry:
    global _registry, _builtins_registered
    if _registry is None:
        _registry = SkillRegistry()
        # 首次获取时自动注册内置 Skill
        _register_builtin_skills(_registry)
        _builtins_registered = True
    return _registry


def _register_builtin_skills(registry: SkillRegistry):
    """注册所有内置 Skill——与 orchestrator 活跃图一致的默认集。"""
    from character_mind import (
        BigFiveSkill, AttachmentSkill,
        PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
        OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
        GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
        StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
        GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
        YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
    )
    skills = [
        BigFiveSkill(), AttachmentSkill(),
        PlutchikEmotionSkill(), PTSDTriggerSkill(), EmotionProbeSkill(),
        OCCEmotionSkill(), CognitiveBiasSkill(), DefenseMechanismSkill(), SmithEllsworthSkill(),
        GottmanSkill(), MarionSkill(), FoucaultSkill(), SternbergSkill(),
        StrogatzSkill(), FisherLoveSkill(), DiriGentSkill(), TheoryOfMindSkill(),
        GrossRegulationSkill(), KohlbergSkill(), MaslowSkill(), SDTSkill(),
        YoungSchemaSkill(), ACETraumaSkill(), ResponseGeneratorSkill(),
    ]
    for skill in skills:
        registry.register(skill)
