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
    """从 runtime profile 注册所有内置 Skill。"""
    from character_mind.core.runtime_profile import DEFAULT_PROFILE
    from character_mind import __dict__ as exports

    for entry in DEFAULT_PROFILE:
        if not entry.auto_register:
            continue
        skill_cls = exports.get(entry.class_name)
        if skill_cls is None:
            # 尝试从子模块导入
            try:
                skill_cls = _import_skill(entry.class_name)
            except ImportError:
                continue
        if skill_cls is not None:
            registry.register(skill_cls())


def _import_skill(class_name: str):
    """按类名推断模块路径并导入。"""
    # 类名 → skill 名: BigFiveSkill → big_five_analysis
    skill_name = _class_to_skill_name(class_name)
    # 从 profile 查找层
    from character_mind.core.runtime_profile import DEFAULT_PROFILE
    for entry in DEFAULT_PROFILE:
        if entry.class_name == class_name:
            layer = entry.layer
            break
    else:
        return None

    import importlib
    module_path = f"character_mind.skills.l{layer}_" + {
        0: "personality",
        1: "preconscious",
        2: "conscious",
        3: "social",
        4: "reflective",
        5: "state_update",
    }[layer]
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name, None)


def _class_to_skill_name(class_name: str) -> str:
    """BigFiveSkill → big_five_analysis"""
    # 简单映射表
    name_map = {
        "BigFiveSkill": "big_five_analysis",
        "AttachmentSkill": "attachment_style_analysis",
        "PlutchikEmotionSkill": "plutchik_emotion",
        "PTSDTriggerSkill": "ptsd_trigger_check",
        "EmotionProbeSkill": "emotion_probe",
        "OCCEmotionSkill": "occ_emotion_appraisal",
        "CognitiveBiasSkill": "cognitive_bias_detect",
        "DefenseMechanismSkill": "defense_mechanism_analysis",
        "SmithEllsworthSkill": "smith_ellsworth_appraisal",
        "TheoryOfMindSkill": "theory_of_mind",
        "GottmanSkill": "gottman_interaction",
        "FoucaultSkill": "foucauldian_power_analysis",
        "MarionSkill": "marion_erotic_phenomenology",
        "SternbergSkill": "sternberg_triangle",
        "StrogatzSkill": "strogatz_love_dynamics",
        "FisherLoveSkill": "fisher_love_stages",
        "DiriGentSkill": "dirigent_world_tension",
        "GrossRegulationSkill": "gross_emotion_regulation",
        "KohlbergSkill": "kohlberg_moral_reasoning",
        "MaslowSkill": "maslow_need_stack",
        "SDTSkill": "sdt_motivation_analysis",
        "ResponseGeneratorSkill": "response_generator",
        "YoungSchemaSkill": "young_schema_update",
        "ACETraumaSkill": "ace_trauma_processing",
    }
    return name_map.get(class_name, class_name.lower())
