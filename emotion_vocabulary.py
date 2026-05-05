"""细粒度情感词典 — 40+ 情感标签

基于 Anthropic 171 情感概念 (Sofroniew et al., 2026) 和 Plutchik (1980) 八类基础情绪，
筛选出角色模拟中常用的细粒度情感标签。
"""
from __future__ import annotations

# Plutchik 8 基础情绪 → 扩展细粒度情感
FINE_GRAINED_EMOTIONS: dict[str, list[str]] = {
    "joy": [
        "狂喜", "满足", "自豪", "得意", "欣慰", "雀跃", "陶醉",
        "释然", "爽快", "幸灾乐祸", "自鸣得意", "欣喜若狂"
    ],
    "sadness": [
        "失落", "惆怅", "忧郁", "哀伤", "凄凉", "沮丧", "心碎",
        "怀念", "孤独", "绝望", "消沉", "怅然若失", "心如死灰"
    ],
    "trust": [
        "依赖", "安心", "忠诚", "钦佩", "敬仰", "亲切", "温暖",
        "放心", "依恋", "皈依感", "托付", "无条件的信"
    ],
    "disgust": [
        "反感", "鄙夷", "恶心", "嫌弃", "不屑", "厌烦", "轻蔑",
        "憎恶", "嗤之以鼻", "生理排斥", "道德唾弃"
    ],
    "fear": [
        "焦虑", "紧张", "恐慌", "不安", "畏惧", "惊惶", "无助",
        "战栗", "窒息感", "草木皆兵", "惶惶不可终日"
    ],
    "anger": [
        "恼怒", "愤恨", "暴躁", "怨恨", "嫉妒", "敌意", "暴怒",
        "委屈", "隐忍的怒火", "杀意", "睚眦必报", "咬牙切齿"
    ],
    "surprise": [
        "震惊", "困惑", "好奇", "茫然", "错愕", "不可思议", "恍惚",
        "瞠目结舌", "如梦初醒", "始料未及"
    ],
    "anticipation": [
        "希望", "憧憬", "渴望", "急切", "警觉", "忐忑", "耐心",
        "翘首以盼", "患得患失", "蠢蠢欲动", "煎熬的等待"
    ],
}

# 复合情感（跨类别）——在角色模拟中高频出现
COMPLEX_EMOTIONS: dict[str, dict] = {
    "love": {"components": ["joy", "trust"], "cn": "爱", "intensity_range": (0.3, 1.0)},
    "guilt": {"components": ["sadness", "fear"], "cn": "内疚", "intensity_range": (0.3, 1.0)},
    "shame": {"components": ["sadness", "disgust"], "cn": "羞耻", "intensity_range": (0.3, 1.0)},
    "jealousy": {"components": ["anger", "fear", "sadness"], "cn": "嫉妒", "intensity_range": (0.2, 1.0)},
    "remorse": {"components": ["sadness", "disgust"], "cn": "悔恨", "intensity_range": (0.3, 1.0)},
    "awe": {"components": ["surprise", "fear"], "cn": "敬畏", "intensity_range": (0.2, 0.9)},
    "contempt": {"components": ["disgust", "anger"], "cn": "蔑视", "intensity_range": (0.3, 1.0)},
    "hope": {"components": ["anticipation", "trust"], "cn": "希望", "intensity_range": (0.1, 1.0)},
    "despair": {"components": ["sadness", "fear"], "cn": "绝望", "intensity_range": (0.5, 1.0)},
    "resentment": {"components": ["anger", "sadness"], "cn": "怨愤", "intensity_range": (0.2, 1.0)},
    "longing": {"components": ["sadness", "anticipation"], "cn": "渴望/思慕", "intensity_range": (0.2, 1.0)},
    "pride": {"components": ["joy", "anticipation"], "cn": "骄傲", "intensity_range": (0.2, 1.0)},
    "gratitude": {"components": ["joy", "trust"], "cn": "感激", "intensity_range": (0.1, 1.0)},
    "betrayal": {"components": ["anger", "sadness", "disgust"], "cn": "被背叛感", "intensity_range": (0.4, 1.0)},
    "schadenfreude": {"components": ["joy", "disgust"], "cn": "幸灾乐祸", "intensity_range": (0.1, 0.8)},
    "brooding": {"components": ["anger", "sadness", "anticipation"], "cn": "阴郁沉思", "intensity_range": (0.3, 0.9)},
}

# Anthropic 论文中发现的"功能性情感"——在角色行为中具有强烈因果效应
FUNCTIONAL_EMOTIONS: dict[str, str] = {
    "desperate": "绝望的——为达成目标不择手段，高风险行为激增",
    "calm": "冷静的——道德约束增强，行为更理性",
    "smug": "自鸣得意的——轻视对手，容易露出破绽",
    "brooding": "阴郁沉思的——反复咀嚼负面体验，图式强化风险",
    "resentful": "怨愤的——暗中记仇，伺机报复",
    "defeated": "挫败的——放弃主动行动，回避情境",
    "emboldened": "胆大的——风险偏好上升，主动出击",
    "wary": "警惕的——高度警觉，过度解读威胁信号",
}

# 所有细粒度情感标签的扁平列表
ALL_FINE_GRAINED = sorted(set(
    emotion
    for category in FINE_GRAINED_EMOTIONS.values()
    for emotion in category
))

# Plutchik 8 基础到细粒度的映射（反向索引）
BASIC_TO_FINE: dict[str, list[str]] = {k: list(v) for k, v in FINE_GRAINED_EMOTIONS.items()}

# 细粒度到基础的映射
FINE_TO_BASIC: dict[str, str] = {}
for basic, fines in FINE_GRAINED_EMOTIONS.items():
    for fine in fines:
        FINE_TO_BASIC[fine] = basic


def get_fine_grained(basic_emotion: str) -> list[str]:
    """获取某基础情绪的细粒度标签列表"""
    return FINE_GRAINED_EMOTIONS.get(basic_emotion, [])


def get_basic(fine_emotion: str) -> str | None:
    """获取细粒度情绪对应的基础类别"""
    return FINE_TO_BASIC.get(fine_emotion)


def get_complex(complex_name: str) -> dict | None:
    """获取复合情绪的组成信息"""
    return COMPLEX_EMOTIONS.get(complex_name)


def get_functional_description(name: str) -> str | None:
    """获取功能性情感的行为因果描述"""
    return FUNCTIONAL_EMOTIONS.get(name)
