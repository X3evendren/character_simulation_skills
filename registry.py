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

    def select_layer3(self, event_type: str, has_partner: bool = False, has_authority: bool = False,
                      has_conflict: bool = False, has_resources: bool = False, has_group: bool = False) -> list[str]:
        """Layer 3 按触发条件选择性激活"""
        selected: set[str] = set()
        if has_partner:
            selected.update(self._by_trigger.get("romantic", []))
        if has_authority:
            selected.update(self._by_trigger.get("authority", []))
        if has_conflict:
            selected.update(self._by_trigger.get("conflict", []))
        if has_resources:
            selected.update(self._by_trigger.get("economic", []))
        if has_group:
            selected.update(self._by_trigger.get("group", []))
        return [s for s in selected if s in self._by_layer.get(3, [])]

    @property
    def skill_count(self) -> int:
        return len(self._skills)


# 全局单例
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
