"""统一心理状态向量 — 所有心理学 Skill 输出的统一空间。

解决"多坐标系"问题：情感/动机/依恋/防御各自独立，无法互算一致性。
MindState 是单一真理源——所有模块必须读写这个空间。
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class MindState:
    """统一心理状态向量。

    所有心理学分析最终映射到这个统一空间。
    FSM 和双轨系统基于此空间做行为决策。
    """

    # PAD 情感
    pleasure: float = 0.0       # -1.0 到 1.0
    arousal: float = 0.5        # 0.0 到 1.0
    dominance: float = 0.0      # -1.0 到 1.0

    # 控制感
    control: float = 0.5        # 0.0 到 1.0

    # 依恋激活
    attachment_activation: float = 0.0  # 0.0 到 1.0
    attachment_style: str = "secure"

    # 图式激活
    schema_activation: dict[str, float] = field(default_factory=dict)

    # 动机/目标
    goal_tension: float = 0.5   # 0.0 到 1.0
    goal_text: str = ""

    # 防御
    defense_strength: float = 0.0  # 0.0 到 1.0
    defense_type: str = ""

    # 稳定性与时间
    stability: float = 1.0      # 1.0 = 人格稳定, < 0.5 = 漂移警告
    timestamp: float = 0.0

    # OCEAN 基线（用于稳定性约束）
    ocean_baseline: dict[str, float] = field(default_factory=lambda: {
        "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5,
    })

    # ── 写入接口 ──

    def set_affect(self, pleasure: float, arousal: float, dominance: float = 0.0):
        self.pleasure = max(-1.0, min(1.0, pleasure))
        self.arousal = max(0.0, min(1.0, arousal))
        self.dominance = max(-1.0, min(1.0, dominance))
        self.timestamp = time.time()

    def set_attachment(self, activation: float, style: str = ""):
        self.attachment_activation = max(0.0, min(1.0, activation))
        if style:
            self.attachment_style = style
        self.timestamp = time.time()

    def set_defense(self, strength: float, dtype: str = ""):
        self.defense_strength = max(0.0, min(1.0, strength))
        if dtype:
            self.defense_type = dtype
        self.timestamp = time.time()

    def activate_schema(self, name: str, intensity: float):
        self.schema_activation[name] = max(0.0, min(1.0, intensity))
        self.timestamp = time.time()

    def set_goal(self, tension: float, text: str = ""):
        self.goal_tension = max(0.0, min(1.0, tension))
        if text:
            self.goal_text = text
        self.timestamp = time.time()

    def set_control(self, value: float):
        self.control = max(0.0, min(1.0, value))
        self.timestamp = time.time()

    # ── 一致性计算 ──

    def compute_coherence(self) -> float:
        """计算当前状态的内部一致性。"""
        coherence = 1.0
        if self.pleasure > 0.3 and self.defense_strength > 0.6:
            coherence -= 0.2
        if self.arousal > 0.7 and self.control > 0.7:
            coherence -= 0.1
        if self.attachment_activation > 0.7 and self.defense_strength > 0.7:
            coherence -= 0.3
        if self.pleasure < -0.5 and self.arousal < 0.2:
            coherence -= 0.1
        return max(0.0, coherence)

    def distance_to(self, other: "MindState") -> float:
        """计算与另一个 MindState 的归一化距离。"""
        return math.sqrt(
            ((self.pleasure - other.pleasure) / 2) ** 2 +
            (self.arousal - other.arousal) ** 2 +
            ((self.dominance - other.dominance) / 2) ** 2 +
            (self.control - other.control) ** 2 +
            (self.attachment_activation - other.attachment_activation) ** 2 +
            (self.defense_strength - other.defense_strength) ** 2 +
            (self.goal_tension - other.goal_tension) ** 2
        ) / math.sqrt(7)

    def check_stability(self) -> dict:
        """检查人格稳定性——相对于 OCEAN 基线的偏移。"""
        issues = []
        self.stability = 1.0
        if self.defense_strength > 0.8:
            issues.append("防御机制过度激活")
            self.stability -= 0.1
        if self.attachment_activation > 0.9 and self.attachment_style == "avoidant":
            issues.append("回避型依恋高度激活——内在矛盾")
            self.stability -= 0.15
        if self.pleasure < -0.6:
            issues.append("情感状态持续负面")
            self.stability -= 0.1
        return {"stable": self.stability >= 0.5, "index": self.stability, "issues": issues}

    def snapshot(self) -> "MindState":
        """创建当前状态的副本。"""
        return MindState(
            pleasure=self.pleasure, arousal=self.arousal, dominance=self.dominance,
            control=self.control,
            attachment_activation=self.attachment_activation, attachment_style=self.attachment_style,
            schema_activation=dict(self.schema_activation),
            goal_tension=self.goal_tension, goal_text=self.goal_text,
            defense_strength=self.defense_strength, defense_type=self.defense_type,
            stability=self.stability,
            timestamp=time.time(),
            ocean_baseline=dict(self.ocean_baseline),
        )

    def to_dict(self) -> dict:
        return {
            "affect": {"pleasure": self.pleasure, "arousal": self.arousal, "dominance": self.dominance},
            "control": self.control,
            "attachment": {"activation": self.attachment_activation, "style": self.attachment_style},
            "schemas": dict(self.schema_activation),
            "goal": {"tension": self.goal_tension, "text": self.goal_text},
            "defense": {"strength": self.defense_strength, "type": self.defense_type},
            "stability": self.stability,
            "coherence": self.compute_coherence(),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MindState":
        affect = d.get("affect", {})
        attachment = d.get("attachment", {})
        goal = d.get("goal", {})
        defense = d.get("defense", {})
        return cls(
            pleasure=affect.get("pleasure", 0.0),
            arousal=affect.get("arousal", 0.5),
            dominance=affect.get("dominance", 0.0),
            control=d.get("control", 0.5),
            attachment_activation=attachment.get("activation", 0.0),
            attachment_style=attachment.get("style", "secure"),
            schema_activation=d.get("schemas", {}),
            goal_tension=goal.get("tension", 0.5),
            goal_text=goal.get("text", ""),
            defense_strength=defense.get("strength", 0.0),
            defense_type=defense.get("type", ""),
            stability=d.get("stability", 1.0),
            timestamp=d.get("timestamp", 0.0),
        )
