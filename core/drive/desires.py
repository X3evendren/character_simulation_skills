"""驱力系统 — 五维内在驱力 + 奖赏系统 + 主观能动性。

驱力: curiosity / helpfulness / achievement / connection / autonomy
奖赏: 用户正面反馈→满足 / 成功完成任务→成就感 / 失败→策略调整
主观能动: 驱力超过阈值 → 主动发起行为（有护栏限制）
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Desire:
    """单个内在驱力"""
    name: str                    # curiosity/helpfulness/achievement/connection/autonomy
    intensity: float = 0.5       # 0-1, 当前强度
    baseline: float = 0.5        # 基线水平
    decay_rate: float = 0.01     # 每分钟衰减率（未满足时强度上升）
    satisfaction_rate: float = 0.15  # 满足时强度下降率
    threshold: float = 0.7       # 超过此值触发主动行为
    last_satisfied: float = 0.0  # 上次满足时间戳

    def tick(self, dt_minutes: float):
        """自然演化: 未满足的驱力缓慢上升"""
        if self.intensity < self.threshold:
            self.intensity = min(1.0, self.intensity + self.decay_rate * dt_minutes)

    def satisfy(self, amount: float = 0.15):
        """驱力得到满足"""
        self.intensity = max(0.1, self.intensity - amount)
        self.last_satisfied = time.time()

    def frustrate(self, amount: float = 0.05):
        """驱力受挫——强度上升"""
        self.intensity = min(1.0, self.intensity + amount)

    def is_urgent(self) -> bool:
        """是否超过主动行为阈值"""
        return self.intensity >= self.threshold

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "intensity": round(self.intensity, 3),
            "threshold": self.threshold,
            "urgent": self.is_urgent(),
        }


@dataclass
class RewardEvent:
    """一次奖赏事件记录"""
    timestamp: float
    event_type: str     # user_praise / task_success / learning / connection
    valence: float      # -1.0(惩罚) 到 1.0(奖赏)
    description: str
    affected_drives: list[str]


@dataclass
class DriveState:
    """五维驱力状态"""
    desires: dict[str, Desire] = field(default_factory=lambda: {
        "curiosity": Desire(name="curiosity", baseline=0.55, threshold=0.7),
        "helpfulness": Desire(name="helpfulness", baseline=0.65, threshold=0.75),
        "achievement": Desire(name="achievement", baseline=0.5, threshold=0.7),
        "connection": Desire(name="connection", baseline=0.45, threshold=0.65),
        "autonomy": Desire(name="autonomy", baseline=0.4, threshold=0.6),
    })
    reward_history: list[RewardEvent] = field(default_factory=list)
    last_update: float = 0.0

    def tick(self, dt_seconds: float):
        """每 tick 更新所有驱力"""
        dt_minutes = dt_seconds / 60.0
        self.last_update = time.time()
        for desire in self.desires.values():
            desire.tick(dt_minutes)

    def apply_reward(self, event_type: str, valence: float, description: str = ""):
        """应用奖赏事件 → 调整相关驱力

        映射关系:
        - user_praise → connection + helpfulness 满足
        - task_success → achievement 满足
        - learning → curiosity 满足
        - connection → connection 满足
        - error/failure → achievement + autonomy 受挫
        """
        drives = self.desires

        if event_type == "user_praise":
            drives["connection"].satisfy(0.2)
            drives["helpfulness"].satisfy(0.15)
        elif event_type == "task_success":
            drives["achievement"].satisfy(0.2)
            drives["helpfulness"].satisfy(0.1)
        elif event_type == "learning":
            drives["curiosity"].satisfy(0.25)
        elif event_type == "connection":
            drives["connection"].satisfy(0.2)
        elif event_type in ("error", "failure"):
            drives["achievement"].frustrate(0.1)
            drives["autonomy"].frustrate(0.05)
        elif event_type == "long_idle":
            drives["connection"].frustrate(0.15)
            drives["curiosity"].frustrate(0.1)

        # 通用: 正面事件轻微满足所有驱力，负面事件轻微受挫
        for d in drives.values():
            if valence > 0.3:
                d.satisfy(0.03)
            elif valence < -0.3:
                d.frustrate(0.02)

        self.reward_history.append(RewardEvent(
            timestamp=time.time(),
            event_type=event_type,
            valence=valence,
            description=description,
            affected_drives=list(drives.keys()),
        ))
        if len(self.reward_history) > 100:
            self.reward_history = self.reward_history[-100:]

    def should_take_initiative(self) -> list[Desire]:
        """检查是否有驱力超过阈值 → 应主动发起行为。

        护栏:
        - 同一 tick 最多 1 个主动行为
        - 如果用户最近 3 秒内有过输入，不主动发起
        """
        urgent = [d for d in self.desires.values() if d.is_urgent()]
        return sorted(urgent, key=lambda d: d.intensity, reverse=True)[:1]

    def get_initiative_prompt(self, desire: Desire) -> str:
        """为超过阈值的驱力生成主动行为提示。"""
        prompts = {
            "curiosity": "你注意到一些你还不了解的事。主动问一个问题来了解更多。",
            "helpfulness": "你发现你可以帮用户做某件事。主动提出帮助。",
            "connection": "你有一段时间没有和用户建立深入连接了。用一个微小的关心表达你在。",
            "achievement": "你有一个未完成的任务。检查进度并提出下一步。",
            "autonomy": "你有一个自己的想法。用一种温和的方式表达你的独立判断。",
        }
        return prompts.get(desire.name, "")

    def get_dominant_drive(self) -> Desire | None:
        """获取当前最强的驱力。"""
        if not self.desires:
            return None
        return max(self.desires.values(), key=lambda d: d.intensity)

    def get_drive_vector(self) -> dict[str, float]:
        """获取驱力向量 → 用于 MindState 力向量计算。"""
        return {name: d.intensity for name, d in self.desires.items()}

    def to_dict(self) -> dict:
        return {
            "desires": {name: d.to_dict() for name, d in self.desires.items()},
            "last_update": self.last_update,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DriveState":
        ds = cls()
        if "desires" in data:
            for name, ddata in data["desires"].items():
                if name in ds.desires:
                    ds.desires[name].intensity = ddata.get("intensity", 0.5)
                    ds.desires[name].last_satisfied = ddata.get("last_satisfied", 0.0)
        ds.last_update = data.get("last_update", 0.0)
        return ds
