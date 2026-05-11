"""预测加工 — 预测误差计算。

实际 vs 预期的偏差 → 惊讶程度 → 驱动注意力重定向。
纯数学计算，零额外 Token。
"""
from __future__ import annotations

import math
from collections import deque

from ..mind_state import MindState


class PredictionTracker:
    """预测误差追踪器。

    维护最近的状态序列，计算实际值与 EWMA 预测值的差距。
    高惊讶 → 触发深度分析 / 信念更新。
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._history: deque[MindState] = deque(maxlen=window_size)
        self._ewma: dict[str, float] = {}  # {field: ewma_value}
        self._alpha: float = 0.3  # EWMA 平滑系数
        self._last_error: float = 0.0

    def predict(self) -> MindState:
        """基于 EWMA 预测下一个 MindState。"""
        if not self._history:
            return MindState()

        latest = self._history[-1]
        predicted = MindState()

        for field in ["pleasure", "arousal", "dominance", "control",
                       "attachment_activation", "defense_strength"]:
            current = getattr(latest, field)
            ewma = self._ewma.get(field, current)
            trend = current - ewma
            pred = ewma + trend * 0.3  # 趋势外推，阻尼 0.3
            setattr(predicted, field, max(-1.0, min(1.0, pred)))

        return predicted

    def observe(self, actual: MindState) -> float:
        """观察实际状态，计算预测误差，更新 EWMA。"""
        # 更新 EWMA
        for field in ["pleasure", "arousal", "dominance", "control",
                       "attachment_activation", "defense_strength"]:
            value = getattr(actual, field)
            prev = self._ewma.get(field, value)
            self._ewma[field] = self._alpha * value + (1 - self._alpha) * prev

        self._history.append(actual.snapshot())

        # 如果有足够历史，计算预测误差
        if len(self._history) < 2:
            return 0.0

        predicted = self.predict()
        self._last_error = predicted.distance_to(actual)
        return self._last_error

    def compute_prediction_error(self, expected: MindState, actual: MindState) -> float:
        """计算预期与实际 MindState 之间的预测误差。

        误差越大 → 越"惊讶" → 触发注意力重定向。
        """
        return expected.distance_to(actual)

    @property
    def surprise_level(self) -> float:
        """当前惊讶程度 (0-1)。"""
        return min(1.0, self._last_error)

    @property
    def is_surprised(self) -> bool:
        """是否足够惊讶以触发深度处理。"""
        return self._last_error > 0.3
