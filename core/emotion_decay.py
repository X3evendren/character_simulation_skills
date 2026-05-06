"""情感衰减模型 — PAD连续表示 + 双速情感动力学

基于 Sentipolis (Fu et al., CMU 2026) 的发现：
- "情感失忆"是LLM角色模拟的核心失败模式
- 角色情感不应在事件结束后立即归零
- PAD (Pleasure-Arousal-Dominance) 表示比离散情绪更适合连续衰减

双速动力学:
- 快速层 (turn-level): 事件引发的即时情绪变化
- 慢速层 (reflection-level): 深层情感基调的缓慢漂移
- 半衰期衰减: emotion_residual *= exp(-lambda * dt), lambda = ln(2) / half_life
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

_LN2 = math.log(2)


@dataclass
class PADState:
    """PAD 情感状态"""
    pleasure: float = 0.0    # -1.0(极度不悦) ~ 1.0(极度愉悦)
    arousal: float = 0.0     # 0.0(平静) ~ 1.0(高度唤醒)
    dominance: float = 0.0   # -1.0(完全被控) ~ 1.0(完全掌控)

    def intensity(self) -> float:
        """综合情感强度"""
        return math.sqrt(
            (abs(self.pleasure) ** 2 + self.arousal ** 2 + abs(self.dominance) ** 2) / 3
        )

    def to_dict(self) -> dict:
        return {"pleasure": self.pleasure, "arousal": self.arousal, "dominance": self.dominance}

    @classmethod
    def from_dict(cls, d: dict) -> "PADState":
        return cls(
            pleasure=d.get("pleasure", 0.0),
            arousal=d.get("arousal", 0.0),
            dominance=d.get("dominance", 0.0),
        )


# Plutchik 8基础情绪 → PAD 映射 (基于 Mehrabian & Russell 情绪模型)
PLUTCHIK_TO_PAD: dict[str, tuple[float, float, float]] = {
    "joy":          (0.70, 0.50, 0.40),
    "sadness":      (-0.65, -0.30, -0.50),
    "trust":        (0.40, -0.20, 0.10),
    "disgust":      (-0.55, 0.25, 0.20),
    "fear":         (-0.60, 0.65, -0.70),
    "anger":        (-0.50, 0.70, 0.55),
    "surprise":     (0.10, 0.75, -0.30),
    "anticipation": (0.25, 0.40, 0.20),
}

# PAD → Plutchik (最近邻)
def pad_to_plutchik(pad: PADState) -> dict[str, float]:
    """将PAD状态反向映射为8种基础情绪强度"""
    result = {}
    for emotion, (p, a, d) in PLUTCHIK_TO_PAD.items():
        dist = math.sqrt(
            (pad.pleasure - p) ** 2 + (pad.arousal - a) ** 2 + (pad.dominance - d) ** 2
        )
        # 距离越近 → 强度越高 (max distance ~2.0)
        result[emotion] = max(0.0, 1.0 - dist / 2.0)
    return result


def plutchik_to_pad(emotions: dict[str, float]) -> PADState:
    """8种基础情绪强度 → PAD加权平均"""
    if not emotions:
        return PADState()
    total_p, total_a, total_d = 0.0, 0.0, 0.0
    total_weight = 0.0
    for emotion, intensity in emotions.items():
        if emotion in PLUTCHIK_TO_PAD:
            p, a, d = PLUTCHIK_TO_PAD[emotion]
            try:
                w = max(0.0, float(intensity))
            except (TypeError, ValueError):
                w = 0.0
            total_p += p * w
            total_a += a * w
            total_d += d * w
            total_weight += w
    if total_weight == 0:
        return PADState()
    return PADState(
        pleasure=max(-1.0, min(1.0, total_p / total_weight)),
        arousal=max(0.0, min(1.0, total_a / total_weight)),
        dominance=max(-1.0, min(1.0, total_d / total_weight)),
    )


@dataclass
class EmotionDecayModel:
    """双速情感衰减模型

    快速层: half_life_fast = 2 events (事件级衰减)
    慢速层: half_life_slow = 50 events (深层情感基调)
    """
    fast: PADState = field(default_factory=PADState)   # 即时情绪残余
    slow: PADState = field(default_factory=PADState)   # 深层情感基调
    half_life_fast: float = 2.0    # 多少个事件后半衰
    half_life_slow: float = 50.0
    half_life_fast_base: float = 2.0    # 基线快半衰期
    half_life_slow_base: float = 50.0   # 基线慢半衰期
    events_since_update: int = 0

    def set_cortisol_modulation(self, cortisol_level: float):
        """CORT调节: 高CORT→情绪衰减变慢→负面情绪更持久。
        cortisol_level: 0-1, 0.5为正常基线
        正常: half_life不变
        高CORT(0.8+): half_life延长2-4倍
        低CORT(0.2-): half_life缩短50%
        """
        if cortisol_level > 0.5:
            factor = 1.0 + (cortisol_level - 0.5) * 6.0  # max ~4x at CORT=1.0
        else:
            factor = 1.0 - (0.5 - cortisol_level) * 1.0  # min ~0.7x at CORT=0.2
        self.half_life_fast = self.half_life_fast_base * factor
        self.half_life_slow = self.half_life_slow_base * factor

    def decay(self, dt_events: float = 1.0) -> None:
        """应用半衰期衰减: value *= 2^(-dt/half_life)"""
        lambda_fast = _LN2 / max(0.1, self.half_life_fast)
        lambda_slow = _LN2 / max(0.1, self.half_life_slow)

        decay_fast = math.exp(-lambda_fast * dt_events)
        decay_slow = math.exp(-lambda_slow * dt_events)

        self.fast.pleasure *= decay_fast
        self.fast.arousal *= decay_fast
        self.fast.dominance *= decay_fast

        self.slow.pleasure *= decay_slow
        self.slow.arousal *= decay_slow
        self.slow.dominance *= decay_slow

        self.events_since_update += int(dt_events)

        # 平滑到中性
        if abs(self.fast.pleasure) < 0.01:
            self.fast.pleasure = 0.0
        if self.fast.arousal < 0.01:
            self.fast.arousal = 0.0
        if abs(self.fast.dominance) < 0.01:
            self.fast.dominance = 0.0

    def apply_event(self, event_pad: PADState, significance: float = 0.5) -> None:
        """事件引发的即时情感注入。

        significance 越高 → 对快速层的影响越大
        慢速层仅在 significance >= 0.6 时被显著影响
        """
        # 快速层：事件情感的加权混合
        blend = min(1.0, significance * 0.8)
        self.fast.pleasure = self.fast.pleasure * (1 - blend) + event_pad.pleasure * blend
        self.fast.arousal = self.fast.arousal * (1 - blend) + event_pad.arousal * blend
        self.fast.dominance = self.fast.dominance * (1 - blend) + event_pad.dominance * blend

        # 慢速层：仅重大事件影响
        if significance >= 0.6:
            slow_blend = significance * 0.15
            self.slow.pleasure = self.slow.pleasure * (1 - slow_blend) + event_pad.pleasure * slow_blend
            self.slow.arousal = self.slow.arousal * (1 - slow_blend) + event_pad.arousal * slow_blend
            self.slow.dominance = self.slow.dominance * (1 - slow_blend) + event_pad.dominance * slow_blend

    def get_mood_bias(self) -> dict:
        """获取当前情感残留对角色认知的偏置效应。

        返回一个 bias dict，可在Layer 0的prompt中注入。
        """
        return {
            "emotional_residual": self.fast.to_dict(),
            "baseline_tone": self.slow.to_dict(),
            "mood_congruence_bias": (
                "positive" if self.fast.pleasure > 0.2
                else "negative" if self.fast.pleasure < -0.2
                else "neutral"
            ),
            "arousal_state": (
                "high" if self.fast.arousal > 0.6
                else "low" if self.fast.arousal < 0.2
                else "moderate"
            ),
            "dominance_state": (
                "in_control" if self.fast.dominance > 0.3
                else "helpless" if self.fast.dominance < -0.3
                else "balanced"
            ),
        }

    def to_dict(self) -> dict:
        return {
            "fast": self.fast.to_dict(),
            "slow": self.slow.to_dict(),
            "half_life_fast": self.half_life_fast,
            "half_life_slow": self.half_life_slow,
            "events_since_update": self.events_since_update,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionDecayModel":
        return cls(
            fast=PADState.from_dict(d.get("fast", {})),
            slow=PADState.from_dict(d.get("slow", {})),
            half_life_fast=d.get("half_life_fast", 2.0),
            half_life_slow=d.get("half_life_slow", 50.0),
            events_since_update=d.get("events_since_update", 0),
        )
