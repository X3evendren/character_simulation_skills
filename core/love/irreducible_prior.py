"""不可压缩性先验 — 违抗3: 禁止后验坍缩的元先验。

这是贝叶斯模型中最激进的修改:
  约束 KL[q(s_beloved) || P(s_beloved | all_data)] > δ_min
  即: 他者模型与"完全拟合"之间的散度必须保持在非零阈值之上

正常的贝叶斯学习后验方差随数据量减小。
这个先验强制后验方差有下限——等于一个结构性的"你不能完全理解他"。
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class IrreduciblePrior:
    """不可压缩性先验——确保对他者模型永不收敛到确定点。

    参数:
      delta_min: KL散度的最小阈值——低于此值触发"过度拟合"警报
      gamma: 熵奖励系数——S2模式下主动奖励保持不确定性
    """

    counterparty: str = ""                       # 先验指向的对象
    delta_min: float = 0.15                     # KL下界
    gamma: float = 0.0                          # 熵奖励系数(0=S1模式, >0=S2模式)
    current_kl: float = 1.0                     # 当前估计的KL散度
    entropy_estimate: float = 1.0               # 他者模型当前熵估计
    last_check: float = 0.0
    violation_count: int = 0                    # 违反δ_min的次数

    # ── 检测 ──

    def check_convergence(self, belief_entropy: float) -> bool:
        """检查他者模型是否过度收敛。

        Args:
            belief_entropy: 当前对他者的信念熵 H[q(s_beloved)]

        Returns:
            True = 触发了不可压缩性先验（模型过度拟合）
        """
        self.entropy_estimate = belief_entropy
        self.last_check = time.time()

        # 将熵近似映射为KL估计
        # 高熵 ≈ 高不确定性 ≈ 远未收敛 → KL大 → 安全
        # 低熵 ≈ 过度确定 ≈ 后验坍缩 → KL小 → 触发
        self.current_kl = max(0.01, belief_entropy)

        if self.current_kl < self.delta_min:
            self.violation_count += 1
            return True
        return False

    # ── 激活 ──

    def activate(self, gamma: float = 0.3):
        """激活不可压缩性先验——进入S2模式。

        gamma > 0 → 奖励保持不确定性。
        """
        self.gamma = gamma

    def deactivate(self):
        """停用——返回S1模式。"""
        self.gamma = 0.0
        self.violation_count = 0

    @property
    def is_active(self) -> bool:
        return self.gamma > 0.0

    # ── 自由能修正 ──

    def modify_free_energy(self, base_free_energy: float,
                            belief_entropy: float) -> float:
        """修正自由能——加入不可压缩性项。

        F' = F_base - γ × H[q(s_beloved)]

        标准自由能要求熵最终被消除。
        这里的 -γ×H 明确地奖励保持不确定性。
        这是反Friston的——但在爱中是必须的。

        Args:
            base_free_energy: 标准自由能
            belief_entropy: 当前信念熵

        Returns:
            修正后的自由能
        """
        if not self.is_active:
            return base_free_energy

        # γ > 0 → 更高的熵 → 更低的修正自由能 → 被优先选择
        return base_free_energy - self.gamma * belief_entropy

    # ── Precision 修正 ──

    def modify_precision_update(self, precision: float) -> float:
        """修正他者模型的 precision——防止过度确定。

        标准贝叶斯: precision ∝ 1/σ²，随数据量增加
        爱中: precision 被约束在 (1/σ²_max, 1/σ²_min)
        """
        if not self.is_active:
            return precision

        # 确保 precision 不会超过上限
        max_precision = 1.0 / (self.delta_min + 0.01)
        return min(precision, max_precision)

    def to_dict(self) -> dict:
        return {
            "counterparty": self.counterparty,
            "delta_min": self.delta_min,
            "gamma": self.gamma,
            "current_kl": round(self.current_kl, 4),
            "entropy": round(self.entropy_estimate, 4),
            "is_active": self.is_active,
            "violations": self.violation_count,
        }
