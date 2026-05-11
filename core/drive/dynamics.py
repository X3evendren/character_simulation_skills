"""驱力动力系统: 驱力 → 力向量 → MindState 演化。

融合旧架构的 DriveSystem + DynamicalSystem。
驱力产生力向量，心理学分析产生力向量，合力推动 MindState 更新。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..mind_state import MindState
from .desires import DriveState


@dataclass
class ForceVector:
    """MindState 空间中的力向量——方向+强度。"""

    pleasure_push: float = 0.0
    arousal_push: float = 0.0
    dominance_push: float = 0.0
    control_push: float = 0.0
    attachment_push: float = 0.0
    defense_push: float = 0.0
    goal_tension_push: float = 0.0

    source: str = ""
    weight: float = 1.0

    def magnitude(self) -> float:
        return (
            abs(self.pleasure_push) + abs(self.arousal_push) +
            abs(self.dominance_push) + abs(self.control_push) +
            abs(self.attachment_push) + abs(self.defense_push) +
            abs(self.goal_tension_push)
        )

    def scale(self, factor: float) -> "ForceVector":
        return ForceVector(
            pleasure_push=self.pleasure_push * factor,
            arousal_push=self.arousal_push * factor,
            dominance_push=self.dominance_push * factor,
            control_push=self.control_push * factor,
            attachment_push=self.attachment_push * factor,
            defense_push=self.defense_push * factor,
            goal_tension_push=self.goal_tension_push * factor,
            source=self.source,
            weight=self.weight,
        )


class DriveDynamics:
    """驱力动力系统: 驱力 → 力 → MindState 演化。

    用法:
        dynamics = DriveDynamics()
        dynamics.set_baseline(ocean_profile)
        new_ms = dynamics.step(current_ms, drive_state, psychology_result, dt)
    """

    def __init__(self):
        self.damping = 0.3          # 稳定性阻尼
        self.baseline_anchor = 0.1  # OCEAN 基线锚定强度
        self.max_step_drift = 0.3   # 单步最大漂移
        self._baseline_ms: MindState | None = None

    def set_baseline(self, ocean: dict):
        """设置 OCEAN 基线——系统锚定在此附近。"""
        self._baseline_ms = MindState(ocean_baseline=dict(ocean))

    def step(
        self,
        current: MindState,
        drive_state: DriveState,
        psychology_result: dict | None = None,
        dt: float = 1.0,
    ) -> MindState:
        """一步动力演化: state(t+1) = state(t) + Σforces × (1-damping)。

        Args:
            current: 当前 MindState
            drive_state: 当前驱力状态
            psychology_result: 心理引擎输出 (PsychologyResult.mindstate)
            dt: 时间步长 (秒)

        Returns:
            新的 MindState
        """
        forces = self._compute_forces(drive_state, psychology_result)
        resultant = self._compose(forces)
        damping = self._compute_damping(current)
        new = self._apply(current, resultant, damping, dt)

        # 稳定性约束: 单步漂移不超过 max_step_drift
        dist = current.distance_to(new)
        if dist > self.max_step_drift:
            scale = self.max_step_drift / dist
            new = self._interpolate(current, new, scale)

        # 基线锚定
        if self._baseline_ms:
            new = self._anchor(new)

        new.check_stability()
        return new

    def _compute_forces(
        self, drive_state: DriveState, psychology: dict | None
    ) -> list[ForceVector]:
        """从驱力和心理分析计算力向量列表"""
        forces: list[ForceVector] = []

        # 驱力 → 力向量
        dv = drive_state.get_drive_vector()
        f_drive = ForceVector(source="drive")
        f_drive.pleasure_push = (dv.get("helpfulness", 0.5) - 0.5) * 0.3
        f_drive.attachment_push = (dv.get("connection", 0.5) - 0.5) * 0.3
        f_drive.dominance_push = (dv.get("autonomy", 0.5) - 0.5) * 0.2
        f_drive.goal_tension_push = (dv.get("achievement", 0.5) - 0.5) * 0.15
        f_drive.arousal_push = (dv.get("curiosity", 0.5) - 0.5) * 0.2
        forces.append(f_drive)

        # 心理分析 → 力向量
        if psychology:
            affect = psychology.get("affect", {})
            f_psych = ForceVector(source="psychology")
            f_psych.pleasure_push = affect.get("pleasure", 0.0) * 0.4
            f_psych.arousal_push = (affect.get("arousal", 0.5) - 0.5) * 0.3
            f_psych.dominance_push = affect.get("dominance", 0.0) * 0.3
            f_psych.attachment_push = (psychology.get("attachment_activation", 0.0) - 0.3) * 0.2
            f_psych.defense_push = (psychology.get("defense_strength", 0.0) - 0.2) * 0.2
            f_psych.control_push = (psychology.get("control", 0.5) - 0.5) * 0.3
            forces.append(f_psych)

        return forces

    def _compose(self, forces: list[ForceVector]) -> ForceVector:
        """合成所有力向量——加权平均"""
        if not forces:
            return ForceVector()
        total_weight = sum(f.weight for f in forces) or 1.0
        return ForceVector(
            pleasure_push=sum(f.pleasure_push * f.weight for f in forces) / total_weight,
            arousal_push=sum(f.arousal_push * f.weight for f in forces) / total_weight,
            dominance_push=sum(f.dominance_push * f.weight for f in forces) / total_weight,
            control_push=sum(f.control_push * f.weight for f in forces) / total_weight,
            attachment_push=sum(f.attachment_push * f.weight for f in forces) / total_weight,
            defense_push=sum(f.defense_push * f.weight for f in forces) / total_weight,
            goal_tension_push=sum(f.goal_tension_push * f.weight for f in forces) / total_weight,
            source="resultant",
        )

    def _compute_damping(self, current: MindState) -> float:
        """计算稳定性阻尼——越远离基线，阻尼越强"""
        if self._baseline_ms is None:
            return self.damping
        distance = current.distance_to(self._baseline_ms)
        return self.damping * (1.0 + distance * 2.0)

    def _apply(self, current: MindState, force: ForceVector,
               damping: float, dt: float) -> MindState:
        """将力应用到 MindState"""
        new = current.snapshot()
        factor = max(0.0, 1.0 - damping) * min(dt, 5.0) / 5.0

        new.pleasure = max(-1.0, min(1.0, current.pleasure + force.pleasure_push * factor))
        new.arousal = max(0.0, min(1.0, current.arousal + force.arousal_push * factor))
        new.dominance = max(-1.0, min(1.0, current.dominance + force.dominance_push * factor))
        new.control = max(0.0, min(1.0, current.control + force.control_push * factor))
        new.attachment_activation = max(0.0, min(1.0,
            current.attachment_activation + force.attachment_push * factor))
        new.defense_strength = max(0.0, min(1.0,
            current.defense_strength + force.defense_push * factor))
        new.goal_tension = max(0.0, min(1.0,
            current.goal_tension + force.goal_tension_push * factor))

        return new

    def _anchor(self, state: MindState) -> MindState:
        """微弱拉回基线"""
        if self._baseline_ms is None:
            return state
        anchor = self.baseline_anchor
        dist = state.distance_to(self._baseline_ms)
        if dist < 0.15:
            return state
        state.pleasure += (self._baseline_ms.pleasure - state.pleasure) * anchor
        state.control += (self._baseline_ms.control - state.control) * anchor
        return state

    @staticmethod
    def _interpolate(a: MindState, b: MindState, t: float) -> MindState:
        """在 a 和 b 之间插值"""
        result = a.snapshot()
        result.pleasure = a.pleasure + (b.pleasure - a.pleasure) * t
        result.arousal = a.arousal + (b.arousal - a.arousal) * t
        result.dominance = a.dominance + (b.dominance - a.dominance) * t
        result.control = a.control + (b.control - a.control) * t
        result.attachment_activation = a.attachment_activation + (b.attachment_activation - a.attachment_activation) * t
        result.defense_strength = a.defense_strength + (b.defense_strength - a.defense_strength) * t
        result.goal_tension = a.goal_tension + (b.goal_tension - a.goal_tension) * t
        return result
