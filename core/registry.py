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

    def clone(self) -> "SkillRegistry":
        """创建独立副本——用于测试隔离。"""
        copied = SkillRegistry()
        for name in self.list_all():
            copied.register(self._skills[name])
        return copied

    def clear(self) -> None:
        """清空所有注册（测试用）。"""
        self._skills.clear()
        for layer in self._by_layer:
            self._by_layer[layer].clear()
        for domain in self._by_domain:
            self._by_domain[domain].clear()
        self._by_trigger.clear()


# ── 类名→类映射（profile 消费） ──

_SKILL_CLASS_MAP = None


def _get_skill_class_map() -> dict:
    """延迟加载 Skill 类映射。"""
    global _SKILL_CLASS_MAP
    if _SKILL_CLASS_MAP is not None:
        return _SKILL_CLASS_MAP
    from character_mind import (
        BigFiveSkill, AttachmentSkill,
        PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
        OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
        GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
        StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
        GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
        YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
    )
    _SKILL_CLASS_MAP = {
        "BigFiveSkill": BigFiveSkill,
        "AttachmentSkill": AttachmentSkill,
        "PlutchikEmotionSkill": PlutchikEmotionSkill,
        "PTSDTriggerSkill": PTSDTriggerSkill,
        "EmotionProbeSkill": EmotionProbeSkill,
        "OCCEmotionSkill": OCCEmotionSkill,
        "CognitiveBiasSkill": CognitiveBiasSkill,
        "DefenseMechanismSkill": DefenseMechanismSkill,
        "SmithEllsworthSkill": SmithEllsworthSkill,
        "TheoryOfMindSkill": TheoryOfMindSkill,
        "GottmanSkill": GottmanSkill,
        "FoucaultSkill": FoucaultSkill,
        "MarionSkill": MarionSkill,
        "SternbergSkill": SternbergSkill,
        "StrogatzSkill": StrogatzSkill,
        "FisherLoveSkill": FisherLoveSkill,
        "DiriGentSkill": DiriGentSkill,
        "GrossRegulationSkill": GrossRegulationSkill,
        "KohlbergSkill": KohlbergSkill,
        "MaslowSkill": MaslowSkill,
        "SDTSkill": SDTSkill,
        "YoungSchemaSkill": YoungSchemaSkill,
        "ACETraumaSkill": ACETraumaSkill,
        "ResponseGeneratorSkill": ResponseGeneratorSkill,
    }
    return _SKILL_CLASS_MAP


def build_registry_from_profile(*, include_experimental: bool = False) -> SkillRegistry:
    """从运行时 profile 构建注册表。"""
    from character_mind.core.runtime_profile import get_active_skills
    class_map = _get_skill_class_map()
    registry = SkillRegistry()
    for entry in get_active_skills(experimental=include_experimental):
        cls = class_map.get(entry.class_name)
        if cls is not None:
            registry.register(cls())
    return registry


# ── 全局只读目录（introspection only，不持有 session state） ──

_builtin_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """返回内置 Skill 目录的独立副本。

    每次调用返回 clone，避免调用方意外污染共享状态。
    需要 session-scoped registry 请用 create_runtime()。
    """
    global _builtin_registry
    if _builtin_registry is None:
        _builtin_registry = build_registry_from_profile(include_experimental=True)
    return _builtin_registry.clone()
