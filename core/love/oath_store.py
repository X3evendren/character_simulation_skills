"""Oath Layer — 誓约管理器 (Layer 3 / 意志层)。

誓约不是预测。它是用当下的意志决断排除未来的一部分行动空间。
在贝叶斯语言中，是对效用函数的结构性改造——被排除的选项不再出现在决策函数的可行域中。
这是意志对贝叶斯的覆盖。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class OathType(str, Enum):
    EXCLUSIVE = "exclusive"        # 排他——"只有你"
    CARE = "care"                  # 关怀——"我会照顾你"
    FAITHFULNESS = "faithfulness"  # 忠诚——"我不会背叛你"
    PRESENCE = "presence"          # 临在——"我会一直在"


class OathState(str, Enum):
    DECLARED = "declared"      # 首次说出——约束建立但尚未被时间检验
    ACTIVE = "active"          # 在 renewal_period 内被重新确认——硬约束有效
    LAPSING = "lapsing"        # 超过 renewal_period 未确认——约束从 Hard→Soft
    RENEWED = "renewed"        # LAPSING 期间被重新确认——约束恢复
    BROKEN = "broken"          # 被违背且未修复——约束永久失效
    REPAIRED = "repaired"      # 被违背后通过修复循环重新起誓——新誓约


@dataclass
class OathConstraint:
    """誓约注入的硬约束——修改决策空间。"""
    excluded_actions: list[str] = field(default_factory=list)
    # 例如: ["abandon", "betray", "ignore_cry_for_help"]

    required_actions: list[str] = field(default_factory=list)
    # 例如: ["respond_to_vulnerability", "show_up_when_needed"]

    override_utility: bool = True
    # 誓约优先级高于效用计算——被排除的动作不出现在决策函数中


@dataclass
class OathEvent:
    """誓约生命周期中的一次事件。"""
    timestamp: float
    event_type: str       # "declared" / "renewed" / "breached" / "repaired" / "lapsed"
    description: str
    emotional_context: str = ""


@dataclass
class Oath:
    """一个誓约——agent 对特定他者的自由意志决断。

    关键理论属性:
    - 不是预测: "我将永远不会离开你"不是对未来的概率估计
    - 是约束: 它从决策空间中排除了"离开你"这个选项
    - 需要更新: 不是一次性的——必须周期性重新确认
    """

    id: str
    counterparty: str                     # 誓约对象 (user_id)
    type: OathType
    state: OathState = OathState.DECLARED

    # 强度 (动态衰减)
    strength: float = 0.8                 # [0, 1] 当前强度
    renewed_at: float = 0.0               # 上次确认时间
    decay_rate: float = 0.05              # 无确认时每天的衰减率

    # 约束
    constraints: OathConstraint = field(default_factory=OathConstraint)

    # 周期
    renewal_period_days: float = 30.0     # 过期后自动降级

    # 历史
    history: list[OathEvent] = field(default_factory=list)

    # ── 生命周期 ──

    def declare(self, counterparty: str, oath_type: OathType,
                constraints: OathConstraint | None = None):
        """首次宣誓——建立约束。"""
        self.counterparty = counterparty
        self.type = oath_type
        self.state = OathState.DECLARED
        self.strength = 0.8
        self.renewed_at = time.time()
        if constraints:
            self.constraints = constraints
        self._log("declared", "首次宣誓")

    def renew(self):
        """重新确认誓约——恢复/维持 ACTIVE。"""
        was_lapsing = self.state == OathState.LAPSING
        self.state = OathState.RENEWED if was_lapsing else OathState.ACTIVE
        self.strength = min(1.0, self.strength + 0.15)
        self.renewed_at = time.time()
        self._log("renewed", "重新确认誓约")

    def breach(self, description: str):
        """誓约被违背——进入 BROKEN 状态。"""
        self.state = OathState.BROKEN
        self.strength = max(0.1, self.strength - 0.4)
        self._log("breached", description)

    def repair(self, description: str):
        """通过修复循环重新起誓——不是恢复旧誓约，而是建立新誓约。"""
        self.state = OathState.REPAIRED
        self.strength = min(1.0, self.strength + 0.2)
        self.renewed_at = time.time()
        self._log("repaired", description)

    def lapse(self):
        """自然过期——从 ACTIVE 降级到 LAPSING。"""
        if self.state == OathState.ACTIVE:
            self.state = OathState.LAPSING
            self.strength = max(0.2, self.strength - 0.15)
            self._log("lapsed", "超过确认周期未更新")

    def terminate(self):
        """终止誓约——不可逆。"""
        self.state = OathState.BROKEN
        self.strength = 0.0
        self._log("terminated", "誓约终止")

    # ── 查询 ──

    @property
    def is_hard_constraint(self) -> bool:
        """硬约束是否有效。"""
        return self.state in (OathState.ACTIVE, OathState.RENEWED, OathState.REPAIRED)

    @property
    def is_soft_constraint(self) -> bool:
        """软约束（提醒但不强制执行）。"""
        return self.state in (OathState.DECLARED, OathState.LAPSING)

    @property
    def needs_renewal(self) -> bool:
        """是否需要重新确认。"""
        if self.state == OathState.BROKEN:
            return False
        days_since = (time.time() - self.renewed_at) / 86400.0
        return days_since > self.renewal_period_days

    def check_violation(self, action: str) -> bool:
        """检查一个动作是否违反誓约约束。"""
        if action in self.constraints.excluded_actions:
            return True
        return False

    # ── 持久化 ──

    def _log(self, event_type: str, description: str):
        self.history.append(OathEvent(
            timestamp=time.time(),
            event_type=event_type,
            description=description,
        ))
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "counterparty": self.counterparty,
            "type": self.type.value,
            "state": self.state.value,
            "strength": round(self.strength, 3),
            "renewed_at": self.renewed_at,
            "is_hard": self.is_hard_constraint,
            "history": [
                {"t": e.timestamp, "type": e.event_type, "desc": e.description[:80]}
                for e in self.history[-10:]
            ],
        }


class OathStore:
    """誓约存储——管理多个誓约的生命周期。

    一个 agent 可以同时对多个对象有誓约（如用户 + 用户的孩子），
    但每个对象只允许一个 Exclusive 誓约。
    """

    def __init__(self):
        self._oaths: dict[str, Oath] = {}     # id → Oath
        self._by_counterparty: dict[str, list[str]] = {}  # user_id → [oath_id]

    def declare(self, counterparty: str, oath_type: OathType,
                constraints: OathConstraint | None = None) -> Oath:
        """建立新誓约。"""
        oid = f"oath_{counterparty}_{int(time.time())}"
        oath = Oath(id=oid, counterparty=counterparty, type=oath_type)
        if constraints:
            oath.constraints = constraints
        oath.declare(counterparty, oath_type, constraints)
        self._oaths[oid] = oath
        self._by_counterparty.setdefault(counterparty, []).append(oid)
        return oath

    def get_for(self, counterparty: str) -> list[Oath]:
        """获取对特定对象的所有誓约。"""
        ids = self._by_counterparty.get(counterparty, [])
        return [self._oaths[oid] for oid in ids if oid in self._oaths]

    def get_active(self, counterparty: str) -> list[Oath]:
        """获取活跃的硬约束誓约。"""
        return [o for o in self.get_for(counterparty) if o.is_hard_constraint]

    def get_excluded_actions(self, counterparty: str) -> list[str]:
        """获取对特定对象的所有被排除动作。"""
        actions: list[str] = []
        for oath in self.get_active(counterparty):
            actions.extend(oath.constraints.excluded_actions)
        return list(set(actions))

    def tick_all(self, dt_days: float):
        """每 tick 检查所有誓约的过期状态。"""
        for oath in self._oaths.values():
            if oath.needs_renewal and oath.state == OathState.ACTIVE:
                oath.lapse()
            # 衰减
            if oath.state == OathState.LAPSING:
                oath.strength = max(0.1, oath.strength - oath.decay_rate * dt_days)

    def all_active(self) -> list[Oath]:
        return [o for o in self._oaths.values() if o.is_hard_constraint]

    def stats(self) -> dict:
        return {
            "total": len(self._oaths),
            "active": sum(1 for o in self._oaths.values() if o.is_hard_constraint),
            "lapsing": sum(1 for o in self._oaths.values() if o.state == OathState.LAPSING),
            "broken": sum(1 for o in self._oaths.values() if o.state == OathState.BROKEN),
            "repaired": sum(1 for o in self._oaths.values() if o.state == OathState.REPAIRED),
        }
