"""Love Metrics — assurance vs confidence。

Confidence = P(belief | evidence)，基于证据的贝叶斯后验。
  证据越多 → confidence 越高 → 分布越窄。
  这是一个认知度量。

Assurance = 非概率性的、基于决断的确定性。
  不依赖证据。不被新证据推翻。
  誓约被确认的频率越高 → assurance 越高。
  这是一个意志度量。
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class LoveMetrics:
    """爱度量——assurance + 关系健康指标。"""

    counterparty: str = ""

    # assurance 分量
    oath_renewal_frequency: float = 0.5    # 誓约确认频率 [0, 1]
    repair_success_rate: float = 0.5       # 修复成功率 [0, 1]
    relationship_duration_days: float = 0  # 关系持续时间
    presence_quality: float = 0.5          # 临在质量 [0, 1]

    # 关系健康
    positive_ratio: float = 3.0            # 正/负互动比 (Gottman)
    rupture_count: int = 0
    repair_count: int = 0
    depth_sessions: int = 0                # 深度连接次数

    # ── assurance ──

    @property
    def assurance(self) -> float:
        """计算 assurance。

        assurance = f(誓约确认频率, 修复成功率, 关系时长, 临在质量)

        不同于 confidence:
        - confidence 需要证据积累
        - assurance 只需要持续确认
        - confidence 可以被推翻
        - assurance 不依赖证据
        """
        # 誓约确认频率: 越高越稳定
        renewal_score = self.oath_renewal_frequency

        # 修复成功率: 修复过的裂痕增强 assurance
        if self.rupture_count > 0:
            repair_score = self.repair_count / self.rupture_count
        else:
            repair_score = 0.5  # 没经历过裂痕 = 中性

        # 关系时长: 对数增长——第一年最关键
        duration_score = min(1.0, math.log(1 + self.relationship_duration_days) / math.log(366))

        # 临在质量
        presence_score = self.presence_quality

        # 加权合成
        assurance = (
            renewal_score * 0.35 +
            repair_score * 0.25 +
            duration_score * 0.15 +
            presence_score * 0.25
        )
        return round(min(1.0, max(0.0, assurance)), 4)

    # ── 关系健康 ──

    @property
    def is_healthy(self) -> bool:
        """关系是否健康。

        Gottman 标准: 正/负比 > 5:1 → 健康
                      正/负比 < 1:1 → 危险
        """
        return self.positive_ratio >= 3.0 and self.repair_success_rate >= 0.5

    @property
    def gottman_status(self) -> str:
        """Gottman 关系状态。"""
        if self.positive_ratio >= 5.0:
            return "thriving"       # 繁荣
        elif self.positive_ratio >= 3.0:
            return "stable"         # 稳定
        elif self.positive_ratio >= 1.0:
            return "at_risk"        # 风险中
        else:
            return "critical"       # 危险

    # ── 更新 ──

    def record_positive(self):
        self.positive_ratio = min(10.0, self.positive_ratio + 0.1)

    def record_negative(self):
        self.positive_ratio = max(0.1, self.positive_ratio - 0.3)

    def record_rupture(self):
        self.rupture_count += 1
        self.positive_ratio = max(0.1, self.positive_ratio - 1.0)

    def record_repair(self):
        self.repair_count += 1
        self.positive_ratio = min(10.0, self.positive_ratio + 0.5)

    def record_deep_connection(self):
        self.depth_sessions += 1
        self.presence_quality = min(1.0, self.presence_quality + 0.05)

    def record_oath_renewal(self):
        self.oath_renewal_frequency = min(1.0, self.oath_renewal_frequency + 0.1)

    def tick(self, dt_days: float):
        """时间流逝——自然衰减。"""
        # 长时间无誓约确认 → assurance 下降
        self.oath_renewal_frequency = max(0.0, self.oath_renewal_frequency - 0.02 * dt_days)
        # 长时间无连接 → 临在质量下降
        self.presence_quality = max(0.1, self.presence_quality - 0.01 * dt_days)
        # 关系时长增加
        self.relationship_duration_days += dt_days

    # ── 对比 ──

    def compare(self, confidence: float) -> dict:
        """对比 assurance 和 confidence。"""
        return {
            "assurance": self.assurance,
            "confidence": round(confidence, 4),
            "gap": round(self.assurance - confidence, 4),
            "interpretation": (
                "誓约坚定，即使证据不足" if self.assurance > confidence + 0.2
                else "证据充分，但誓约需要更新" if confidence > self.assurance + 0.2
                else "认知和意志一致"
            ),
        }

    def to_dict(self) -> dict:
        return {
            "assurance": self.assurance,
            "health": self.gottman_status,
            "positive_ratio": round(self.positive_ratio, 1),
            "ruptures": self.rupture_count,
            "repairs": self.repair_count,
            "depth_sessions": self.depth_sessions,
            "duration_days": round(self.relationship_duration_days, 1),
        }
