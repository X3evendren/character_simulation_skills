"""Runtime profile — 声明式运行图配置。

单点真理：orchestrator、benchmark、validation、README 全部从这份配置读取。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class SkillEntry:
    """单个 Skill 的运行图条目。"""
    class_name: str          # 类名（用于延迟导入和序列化）
    layer: int               # 0-5
    trigger_conditions: list[str] = field(default_factory=list)
    experimental: bool = False  # True = 不在默认图里
    auto_register: bool = True  # True = 启动时自动注册
    auto_evolve: bool = False    # True = 允许自进化（仅非 human 生成的技能）
    manifest_version: str = "v2"
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── 默认运行图（最优 11-skill + 生物层） ──
DEFAULT_PROFILE: list[SkillEntry] = [
    # L0 — 人格滤镜 (始终在线)
    SkillEntry("BigFiveSkill",            layer=0, trigger_conditions=["always"]),
    SkillEntry("AttachmentSkill",         layer=0, trigger_conditions=["social", "romantic"]),

    # L1 — 快速前意识
    SkillEntry("PlutchikEmotionSkill",    layer=1, trigger_conditions=["always"]),
    SkillEntry("PTSDTriggerSkill",        layer=1, trigger_conditions=["trauma", "conflict"]),
    SkillEntry("EmotionProbeSkill",       layer=1, trigger_conditions=["always"], experimental=True),

    # L2 — 意识层评估
    SkillEntry("OCCEmotionSkill",         layer=2, trigger_conditions=["always"]),
    SkillEntry("DefenseMechanismSkill",   layer=2, trigger_conditions=["always"]),
    SkillEntry("CognitiveBiasSkill",      layer=2, trigger_conditions=["always"], experimental=True),
    SkillEntry("SmithEllsworthSkill",     layer=2, trigger_conditions=["always"], experimental=True),

    # L3 — 关系/社会处理
    SkillEntry("TheoryOfMindSkill",       layer=3, trigger_conditions=["social", "romantic", "conflict", "authority"]),
    SkillEntry("GottmanSkill",            layer=3, trigger_conditions=["romantic"]),
    SkillEntry("FoucaultSkill",           layer=3, trigger_conditions=["authority", "conflict"]),
    SkillEntry("MarionSkill",             layer=3, trigger_conditions=["romantic"], experimental=True),
    SkillEntry("SternbergSkill",          layer=3, trigger_conditions=["romantic"], experimental=True),
    SkillEntry("StrogatzSkill",           layer=3, trigger_conditions=["romantic"], experimental=True),
    SkillEntry("FisherLoveSkill",         layer=3, trigger_conditions=["romantic"], experimental=True),
    SkillEntry("DiriGentSkill",           layer=3, trigger_conditions=["reflective", "conflict", "romantic"], experimental=True),

    # L4 — 反思处理
    SkillEntry("GrossRegulationSkill",    layer=4, trigger_conditions=["reflective", "conflict"]),
    SkillEntry("SDTSkill",                layer=4, trigger_conditions=["reflective"]),
    SkillEntry("KohlbergSkill",           layer=4, trigger_conditions=["moral", "reflective"], experimental=True),
    SkillEntry("MaslowSkill",             layer=4, trigger_conditions=["reflective"], experimental=True),

    # L5 — 状态更新与回应
    SkillEntry("ResponseGeneratorSkill",  layer=5, trigger_conditions=["always"]),
    SkillEntry("YoungSchemaSkill",        layer=5, trigger_conditions=["trauma", "reflective"]),
    SkillEntry("ACETraumaSkill",          layer=5, trigger_conditions=["trauma"]),
]


def get_default_profile() -> list[SkillEntry]:
    return list(DEFAULT_PROFILE)


def get_active_skills(experimental: bool = False) -> list[SkillEntry]:
    """返回当前启用的 Skill（排除实验性 Skill）。"""
    return [s for s in DEFAULT_PROFILE if not s.experimental or experimental]


def get_active_layer(layer: int, experimental: bool = False) -> list[str]:
    """返回指定层启用的 Skill 名称列表。"""
    return [s.class_name for s in get_active_skills(experimental) if s.layer == layer]


def get_skill_map() -> dict[str, SkillEntry]:
    """返回 {class_name: SkillEntry} 映射。"""
    return {s.class_name: s for s in DEFAULT_PROFILE}
