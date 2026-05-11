"""Relational Layer — 关系调控层 (Layer 2)。

核心功能:
1. SaturationDetector: 检测结构性不可收敛
2. PrecisionRouter: S2模式下重路由预测误差
3. 三状态机: ENCODE → TRANSITIONING → SATURATED → RUPTURED
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum


class RelationMode(str, Enum):
    ENCODE = "encode"              # 编码模式——正常贝叶斯更新
    TRANSITIONING = "transitioning" # 过渡——正在检测是否进入饱和
    SATURATED = "saturated"        # 饱和——爱中，停止对他者收敛
    RUPTURED = "ruptured"          # 裂痕——需要修复


@dataclass
class SaturationDetector:
    """饱和检测器——区分"数据不足"和"结构性的不可压缩"。

    FALSE_SATURATION: 预测误差持续高但self_model没被改写
                      → 只是数据不足，继续收集
    TRUE_SATURATION:  预测误差持续高 AND self_model被他者显著改写
                      → 进入S2模式
    """

    counterparty: str = ""

    # 检测参数
    convergence_window: int = 10      # 观察窗口大小
    error_threshold: float = 0.25     # 高误差阈值
    shift_threshold: float = 0.08     # self_model显著改写的阈值

    # 状态
    error_history: list[float] = field(default_factory=list)
    self_model_history: list[float] = field(default_factory=list)
    mode: RelationMode = RelationMode.ENCODE
    saturation_level: float = 0.0       # [0, 1] 连续饱和度
    last_mode_change: float = 0.0

    def observe(self, prediction_error: float, self_model_shift: float):
        """记录一次观测——用于判断是否进入饱和。

        Args:
            prediction_error: 对他者的预测误差
            self_model_shift: self_model被改写的幅度 ||s_self(t) - s_self(t-w)||
        """
        self.error_history.append(prediction_error)
        self.self_model_history.append(self_model_shift)
        if len(self.error_history) > self.convergence_window:
            self.error_history = self.error_history[-self.convergence_window:]
        if len(self.self_model_history) > self.convergence_window:
            self.self_model_history = self.self_model_history[-self.convergence_window:]

    def evaluate(self) -> RelationMode:
        """评估当前关系模式。"""
        if len(self.error_history) < 5:
            return RelationMode.ENCODE  # 数据不足

        recent_errors = self.error_history[-5:]
        mean_error = sum(recent_errors) / len(recent_errors)
        error_trend = self._trend(self.error_history)

        recent_shifts = self.self_model_history[-5:] if self.self_model_history else [0]
        mean_shift = sum(recent_shifts) / max(len(recent_shifts), 1)

        # 判定结构性不可收敛
        is_non_converging = (
            mean_error > self.error_threshold and
            error_trend >= 0  # 误差没有下降趋势
        )

        # 判定自我模型被显著改写
        is_self_shifting = mean_shift > self.shift_threshold

        # ── 状态机 ──
        if self.mode == RelationMode.RUPTURED:
            return self.mode  # 裂痕需要手动修复

        if is_non_converging and is_self_shifting:
            if self.mode == RelationMode.ENCODE:
                self.mode = RelationMode.TRANSITIONING
                self.last_mode_change = time.time()
            if self.mode == RelationMode.TRANSITIONING:
                # 过渡态维持一段时间 → 确认饱和
                if time.time() - self.last_mode_change > 30.0:  # 30秒
                    self.mode = RelationMode.SATURATED
                    self.last_mode_change = time.time()

        elif not is_non_converging:
            if self.mode in (RelationMode.TRANSITIONING, RelationMode.SATURATED):
                # 误差恢复收敛 → 退回编码模式（可能是假饱和）
                self.mode = RelationMode.ENCODE
                self.saturation_level *= 0.7
                self.last_mode_change = time.time()

        # 更新连续饱和度
        if self.mode == RelationMode.SATURATED:
            self.saturation_level = min(1.0, self.saturation_level + 0.02)
        elif self.mode == RelationMode.ENCODE:
            self.saturation_level = max(0.0, self.saturation_level - 0.03)
        elif self.mode == RelationMode.TRANSITIONING:
            self.saturation_level = min(0.7, self.saturation_level + 0.01)

        return self.mode

    def rupture(self):
        """触发裂痕。"""
        self.mode = RelationMode.RUPTURED
        self.saturation_level = max(0.3, self.saturation_level - 0.2)
        self.last_mode_change = time.time()

    def repair(self):
        """修复成功。"""
        if self.mode == RelationMode.RUPTURED:
            self.mode = RelationMode.SATURATED
            self.saturation_level = min(1.0, self.saturation_level)
            self.last_mode_change = time.time()

    @staticmethod
    def _trend(history: list[float]) -> float:
        """简单的趋势估计——正=上升，负=下降。"""
        if len(history) < 3:
            return 0.0
        first_half = sum(history[:len(history)//2]) / max(len(history)//2, 1)
        second_half = sum(history[len(history)//2:]) / max(len(history) - len(history)//2, 1)
        return second_half - first_half

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "saturation": round(self.saturation_level, 3),
            "mean_error": round(
                sum(self.error_history[-5:]) / max(len(self.error_history[-5:]), 1), 3
            ) if self.error_history else 0,
            "mean_shift": round(
                sum(self.self_model_history[-5:]) / max(len(self.self_model_history[-5:]), 1), 3
            ) if self.self_model_history else 0,
        }


@dataclass
class PrecisionRouter:
    """精度重路由——在S2模式下改变预测误差的处理方向。

    标准路由 (S1/ENCODE):
      ε_other = π_other × (observation - prediction_other)
      → update(belief_other)

    重路由 (S2/SATURATED):
      ε_self  = π_love × ε_other
      → update(belief_self)  # 用他的误差更新"我是谁"
    """

    counterparty: str = ""
    pi_love: float = 0.5          # 重路由的精度权重

    @property
    def reroute_enabled(self) -> bool:
        return self.pi_love > 0.1

    def route(self, prediction_error_other: float,
              mode: RelationMode) -> tuple[float, float]:
        """路由预测误差。

        Returns:
            (ε_other_update, ε_self_update): 分别用于更新他者模型和自我模型的误差
        """
        if mode == RelationMode.SATURATED:
            # 违抗1: 不最小化对他者的预测误差
            ε_other_update = 0.0
            # 违抗2: 重路由到自我模型
            ε_self_update = self.pi_love * prediction_error_other
        elif mode == RelationMode.RUPTURED:
            # 裂痕: 暂停两者更新
            ε_other_update = 0.0
            ε_self_update = 0.0
        else:
            # 正常模式
            ε_other_update = prediction_error_other
            ε_self_update = 0.0

        return ε_other_update, ε_self_update

    def to_dict(self) -> dict:
        return {
            "pi_love": round(self.pi_love, 3),
            "reroute_enabled": self.reroute_enabled,
        }
