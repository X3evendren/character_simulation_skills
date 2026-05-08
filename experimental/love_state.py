"""LoveState — 系统级爱情状态重构器。

爱情不是独立模块，而是一种持久的系统级状态调制，影响从神经递质到自我模型的全链路。
基于 Fisher 三系统 (Lust/Attraction/Attachment) + Li & Heintz 2025 Cell 发现。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class LoveState:
    """持久爱情状态，调制整个系统的运行方式。

    基于 Fisher (2004-2024) 三系统模型:
    - Lust: 雄/雌激素, 性驱力
    - Attraction: DA↑/NE↑/5-HT↓, VTA→尾状核激活
    - Attachment: 催产素/加压素, 腹侧苍白球

    基于 Li & Heintz (2025 Cell): mPFC Cacna1h+ 神经元 = "爱情开关"
    """

    active: bool = False
    onset_time: float = 0.0
    stage: str = "none"  # none / lust / attraction / attachment
    target_id: str = ""   # 爱情对象

    # 神经递质调制
    neurotransmitter_modulation: dict = field(default_factory=lambda: {
        "DA": 0.0,      # 多巴胺: 奖赏敏感性 (↑)
        "5HT": 0.0,     # 血清素: 强迫专注 (↓, 负值)
        "NE": 0.0,      # 去甲肾上腺素: 唤醒 (↑)
        "OXT": 0.0,     # 催产素: 信任/联结 (↑)
        "CORT": 0.0,    # 皮质醇: 早期↑后↓
    })

    # PFC 调制 (爱越深→抑制越强)
    pfc_inhibition: dict = field(default_factory=lambda: {
        "critical_judgment": 0.0,  # 玫瑰色眼镜
        "threat_detection": 0.0,   # 忽略对方缺点
        "social_filter": 0.0,      # 行为更开放
    })

    # 注意力偏置
    attention_modulation: dict = field(default_factory=lambda: {
        "partner_cues_salience": 0.0,   # 对方自动吸引注意
        "other_goals_priority": 0.0,    # 其他目标降级 (负值)
    })

    # 行为倾向
    behavioral_tendencies: dict = field(default_factory=lambda: {
        "pursuit": 0.5,           # 想靠近
        "risk_tolerance": 0.3,    # 敢冒险
        "self_disclosure": 0.5,   # 想被了解
        "jealousy": 0.3,          # 嫉妒基线
    })

    # 阶段转换追踪
    attraction_duration: float = 0.0    # 吸引阶段累计时间(天)
    attachment_transition: float = 0.0  # 向依恋过渡的进度 (0-1)
    stage_history: list[dict] = field(default_factory=list)

    def activate_love(self, target_id: str, stage: str = "attraction"):
        """激活爱情状态。"""
        self.active = True
        self.onset_time = time.time()
        self.stage = stage
        self.target_id = target_id
        self._apply_stage_modulation(stage)
        self.stage_history.append({
            "t": time.time(), "event": "activated", "target": target_id, "stage": stage,
        })

    def deactivate_love(self):
        """关闭爱情状态。"""
        self.active = False
        self.stage = "none"
        self.target_id = ""
        self._reset_modulation()
        self.stage_history.append({"t": time.time(), "event": "deactivated"})

    def tick(self, dt_seconds: float):
        """每个 tick 更新爱情状态。"""
        if not self.active:
            return

        # 阶段自然过渡
        if self.stage == "attraction":
            self.attraction_duration += dt_seconds / 86400.0  # 转换为天
            # 18个月 ≈ 540天 → 吸引→依恋
            if self.attraction_duration > 180:
                self.attachment_transition = min(1.0,
                    (self.attraction_duration - 180) / 360)
                self._blend_to_attachment()

        elif self.stage == "lust":
            # 性欲阶段通常较短: 数天到数周 → 吸引
            self.attraction_duration += dt_seconds / 86400.0
            if self.attraction_duration > 30:
                self._transition_stage("attraction")

    def _apply_stage_modulation(self, stage: str):
        if stage == "attraction":
            self.neurotransmitter_modulation = {
                "DA": 0.4, "5HT": -0.3, "NE": 0.3, "OXT": 0.1, "CORT": 0.2,
            }
            self.pfc_inhibition = {
                "critical_judgment": 0.5, "threat_detection": 0.4, "social_filter": 0.3,
            }
            self.attention_modulation = {
                "partner_cues_salience": 0.6, "other_goals_priority": -0.4,
            }
        elif stage == "attachment":
            self.neurotransmitter_modulation = {
                "DA": 0.15, "5HT": -0.05, "NE": 0.05, "OXT": 0.5, "CORT": -0.2,
            }
            self.pfc_inhibition = {
                "critical_judgment": 0.1, "threat_detection": 0.0, "social_filter": 0.1,
            }
            self.attention_modulation = {
                "partner_cues_salience": 0.3, "other_goals_priority": -0.1,
            }
        elif stage == "lust":
            self.neurotransmitter_modulation = {
                "DA": 0.2, "5HT": 0.0, "NE": 0.1, "OXT": 0.0, "CORT": 0.0,
            }

    def _blend_to_attachment(self):
        """在吸引和依恋之间做平滑过渡。"""
        p = self.attachment_transition  # 0→1
        # 线性插值
        for key in self.neurotransmitter_modulation:
            self.neurotransmitter_modulation[key] = (
                self.neurotransmitter_modulation[key] * (1-p)
            )
        # 逐渐增加 OXT
        self.neurotransmitter_modulation["OXT"] = 0.1 + 0.4 * p
        if p > 0.95:
            self._transition_stage("attachment")

    def _transition_stage(self, new_stage: str):
        old = self.stage
        self.stage = new_stage
        self._apply_stage_modulation(new_stage)
        self.stage_history.append({
            "t": time.time(), "event": "stage_transition",
            "from": old, "to": new_stage,
        })

    def _reset_modulation(self):
        for k in self.neurotransmitter_modulation:
            self.neurotransmitter_modulation[k] = 0.0
        for k in self.pfc_inhibition:
            self.pfc_inhibition[k] = 0.0
        for k in self.attention_modulation:
            self.attention_modulation[k] = 0.0
        self.attraction_duration = 0.0
        self.attachment_transition = 0.0

    def get_bio_context(self) -> dict:
        """获取可注入生物层的上下文。"""
        return {
            "love_active": self.active,
            "love_stage": self.stage,
            "neurotransmitter_modulation": dict(self.neurotransmitter_modulation),
            "pfc_inhibition": dict(self.pfc_inhibition),
            "attention_modulation": dict(self.attention_modulation),
        }

    def to_dict(self) -> dict:
        return {
            "active": self.active, "onset_time": self.onset_time,
            "stage": self.stage, "target_id": self.target_id,
            "neurotransmitter_modulation": self.neurotransmitter_modulation,
            "pfc_inhibition": self.pfc_inhibition,
            "attention_modulation": self.attention_modulation,
            "behavioral_tendencies": self.behavioral_tendencies,
            "attraction_duration": self.attraction_duration,
            "attachment_transition": self.attachment_transition,
            "stage_history": self.stage_history[-10:],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoveState":
        ls = cls()
        ls.active = data.get("active", False)
        ls.onset_time = data.get("onset_time", 0)
        ls.stage = data.get("stage", "none")
        ls.target_id = data.get("target_id", "")
        ls.neurotransmitter_modulation = data.get("neurotransmitter_modulation", {})
        ls.pfc_inhibition = data.get("pfc_inhibition", {})
        ls.attention_modulation = data.get("attention_modulation", {})
        ls.behavioral_tendencies = data.get("behavioral_tendencies", {})
        ls.attraction_duration = data.get("attraction_duration", 0)
        ls.attachment_transition = data.get("attachment_transition", 0)
        ls.stage_history = data.get("stage_history", [])
        return ls
