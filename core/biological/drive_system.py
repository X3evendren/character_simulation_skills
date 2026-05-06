"""
驱力系统 — 15维度内稳态模型

基于 Tyrrell (1993) 驱力分层 + Panksepp (1998) 情感神经科学 +
Keramati & Gutkin (2014) Hierarchical Reinforcement Learning (HRRL):

- 15 个驱力按 4 层组织: Survival Core -> Mammalian Core -> Richness -> Panksepp Meta-Drives
- W-Learning (Humphrys 1995) 行动选择: 最"迫切"的驱力赢得选择权
- Crisis Mode (drive > 0.8): Winner-Take-All 紧急响应
- Normal Mode: Softmax 分布式投票
- SEEKING 探索偏置: "explore/wander/try_new" 类行动获得额外权重
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


# ──────────────────────────────────────────
# DriveState — 15 驱力状态容器
# ──────────────────────────────────────────

@dataclass
class DriveState:
    """15 驱力当前值，范围 [0, 1]。

    0 = 完全满足，1 = 危急 / 紧急。
    """

    # ── Tier 1 — Survival Core ──
    drive_energy: float = 0.0
    drive_safety: float = 0.0
    drive_rest: float = 0.0

    # ── Tier 2 — Mammalian Core ──
    drive_social: float = 0.0
    drive_novelty: float = 0.0
    drive_competence: float = 0.0
    drive_autonomy: float = 0.0

    # ── Tier 3 — Richness ──
    drive_comfort: float = 0.0
    drive_mating: float = 0.0
    drive_care: float = 0.0
    drive_status: float = 0.0
    drive_justice: float = 0.0

    # ── Tier 4 — Panksepp Meta-Drives ──
    drive_seeking: float = 0.5  # baseline 0.5 (exploratory push, not a deficit drive)
    drive_play: float = 0.0
    drive_panic: float = 0.0

    # ── 快捷访问 ──

    def get_drive_vector(self) -> dict[str, float]:
        """返回 {驱力名称: 当前值} 映射"""
        return {
            "energy": self.drive_energy,
            "safety": self.drive_safety,
            "rest": self.drive_rest,
            "social": self.drive_social,
            "novelty": self.drive_novelty,
            "competence": self.drive_competence,
            "autonomy": self.drive_autonomy,
            "comfort": self.drive_comfort,
            "mating": self.drive_mating,
            "care": self.drive_care,
            "status": self.drive_status,
            "justice": self.drive_justice,
            "seeking": self.drive_seeking,
            "play": self.drive_play,
            "panic": self.drive_panic,
        }

    @staticmethod
    def get_tier(drive_name: str) -> int:
        """返回驱力所在层级 (1-4)"""
        tier_map: dict[str, int] = {
            "energy": 1, "safety": 1, "rest": 1,
            "social": 2, "novelty": 2, "competence": 2, "autonomy": 2,
            "comfort": 3, "mating": 3, "care": 3, "status": 3, "justice": 3,
            "seeking": 4, "play": 4, "panic": 4,
        }
        return tier_map.get(drive_name, 0)

    def highest_drive(self) -> tuple[str, float]:
        """返回 (最高驱力名称, 值)"""
        vec = self.get_drive_vector()
        name = max(vec, key=vec.get)
        return name, vec[name]

    def crisis_drives(self) -> list[tuple[str, float]]:
        """返回所有高于危急阈值 (0.8) 的驱力"""
        return [(n, v) for n, v in self.get_drive_vector().items() if v > 0.8]

    def is_in_crisis(self) -> bool:
        """是否有任一驱力处于危急状态"""
        return any(v > 0.8 for v in self.get_drive_vector().values())

    # ── 持久化 ──

    def to_dict(self) -> dict[str, float]:
        return self.get_drive_vector()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DriveState":
        return cls(
            drive_energy=d.get("energy", 0.0),
            drive_safety=d.get("safety", 0.0),
            drive_rest=d.get("rest", 0.0),
            drive_social=d.get("social", 0.0),
            drive_novelty=d.get("novelty", 0.0),
            drive_competence=d.get("competence", 0.0),
            drive_autonomy=d.get("autonomy", 0.0),
            drive_comfort=d.get("comfort", 0.0),
            drive_mating=d.get("mating", 0.0),
            drive_care=d.get("care", 0.0),
            drive_status=d.get("status", 0.0),
            drive_justice=d.get("justice", 0.0),
            drive_seeking=d.get("seeking", 0.5),
            drive_play=d.get("play", 0.0),
            drive_panic=d.get("panic", 0.0),
        )


# ──────────────────────────────────────────
# DriveSystem — 核心控制器
# ──────────────────────────────────────────

class DriveSystem:
    """15 驱力内稳态系统。

    工作流程:
        update(dt_minutes, events, actions)
            -> 1. 自然衰减 (驱力随时间上升)
            -> 2. 事件冲击
            -> 3. 行动消费
            -> 4. 自我调节 (缓慢回归设定点)

    行动选择:
        select_action(available_actions)
            -> Crisis Mode (任一 >0.8): Winner-Take-All
            -> Normal Mode: 驱力平方紧迫度 -> Softmax
            -> SEEKING bonus: 探索类行动获得额外权重
    """

    # ── 静态常量 ──

    DRIVE_NAMES: list[str] = [
        "energy", "safety", "rest",
        "social", "novelty", "competence", "autonomy",
        "comfort", "mating", "care", "status", "justice",
        "seeking", "play", "panic",
    ]

    # 每小时自然增长率（驱力值上升 = 需求积累）
    # 事件驱动型驱力 decay=0.0，仅通过事件改变
    DECAY_RATES: dict[str, float] = {
        # Tier 1
        "energy": 0.02,
        "safety": 3.0,       # 0.05/min -> 3.0/hr（安全时快速回落）
        "rest": 0.03,
        # Tier 2
        "social": 0.04,
        "novelty": 0.08,     # 最快自然衰减（好奇心消退快）
        "competence": 0.0,   # 纯事件驱动
        "autonomy": 0.0,     # 纯事件驱动
        # Tier 3
        "comfort": 0.01,     # 最慢的非事件驱动衰减
        "mating": 0.02,
        "care": 0.02,
        "status": 0.0,       # 纯事件驱动
        "justice": 0.0,      # 纯事件驱动
        # Tier 4
        "seeking": 0.0,      # 元驱力——维持 baseline 0.5
        "play": 0.05,
        "panic": 0.0,        # 纯事件驱动
    }

    # 内稳态设定点（自我调节缓慢回归此值）
    SETPOINTS: dict[str, float] = {
        "energy": 0.2,
        "safety": 0.1,       # 安全期望很低（快速回归安全状态）
        "rest": 0.2,
        "social": 0.3,
        "novelty": 0.4,      # 适度好奇
        "competence": 0.3,
        "autonomy": 0.2,
        "comfort": 0.2,
        "mating": 0.3,
        "care": 0.2,
        "status": 0.3,
        "justice": 0.3,
        "seeking": 0.5,      # Panksepp SEEKING 基线
        "play": 0.3,
        "panic": 0.0,        # 正常应为 0
    }

    # ── 事件类型 -> 驱力冲击量 ──
    # 正值 = 驱力上升（需求/威胁），负值 = 驱力下降（满足）
    EVENT_IMPACTS: dict[str, dict[str, float]] = {
        # 社交/浪漫
        "romantic":          {"mating": -0.20, "social": -0.15, "comfort": -0.10},
        "social":            {"social": -0.15},
        "intimate":          {"mating": -0.25, "social": -0.10, "comfort": -0.10},
        "daily_chat":        {"social": -0.05},
        "routine":           {"social": -0.05},

        # 威胁/冲突
        "conflict":          {"safety": 0.30, "comfort": 0.15, "status": 0.05},
        "threat":            {"safety": 0.30, "panic": 0.10},
        "betrayal":          {"safety": 0.50, "panic": 0.40, "comfort": 0.20},
        "trauma":            {"safety": 0.50, "panic": 0.40, "comfort": 0.30},

        # 成就/失败
        "triumph":           {"competence": -0.30, "status": -0.20, "social": -0.05},
        "breakthrough":      {"competence": -0.30, "status": -0.20, "novelty": -0.15},
        "failure":           {"competence": 0.20, "status": 0.10, "comfort": 0.05},

        # 道德/正义
        "moral_choice":      {"justice": 0.20, "autonomy": 0.05},
        "moral_dilemma":     {"justice": 0.30, "autonomy": 0.10},
        "injustice":         {"justice": 0.30, "autonomy": 0.10, "status": 0.05},

        # 丧失/分离
        "loss":              {"panic": 0.50, "safety": 0.20, "comfort": 0.20},
        "death":             {"panic": 0.50, "safety": 0.20, "comfort": 0.30},

        # 探索/玩耍
        "exploration":       {"novelty": -0.20, "seeking": -0.10},
        "play_event":        {"play": -0.20, "social": -0.05},

        # 照料
        "caregiving":        {"care": -0.20, "social": -0.05},

        # 自主性
        "autonomy_granted":  {"autonomy": -0.20},
        "controlled":        {"autonomy": 0.20, "status": 0.05},

        # 认可
        "recognition":       {"status": -0.20, "competence": -0.10},

        # 生理
        "eating":            {"energy": -0.30},
        "rest_event":        {"rest": -0.30, "energy": -0.05},

        # 环境不适（可由外部环境检测模块触发）
        "uncomfortable_env": {"comfort": 0.20},
        "comfortable_env":   {"comfort": -0.15},
    }

    # ── 行动 -> 驱力满足效果 ──
    # 负值 = 驱力下降（需求被满足）
    ACTION_SATISFACTION: dict[str, dict[str, float]] = {
        # 能量
        "eat":               {"energy": -0.30},
        "rest":              {"energy": -0.10, "rest": -0.30},
        "sleep":             {"energy": -0.20, "rest": -0.40},

        # 安全
        "hide":              {"safety": -0.20},
        "defend":            {"safety": -0.10},
        "seek_shelter":      {"safety": -0.30},

        # 社交
        "approach":          {"social": -0.15},
        "talk":              {"social": -0.10},
        "share":             {"social": -0.15, "care": -0.05},

        # 探索/好奇
        "explore":           {"novelty": -0.25, "seeking": -0.05},
        "investigate":       {"novelty": -0.20},
        "learn":             {"novelty": -0.20, "competence": -0.10},
        "wander":            {"seeking": -0.05, "novelty": -0.05},
        "try_new":           {"seeking": -0.10, "novelty": -0.10},

        # 能力
        "practice":          {"competence": -0.15},
        "challenge":         {"competence": -0.20, "novelty": -0.05},
        "achieve":           {"competence": -0.30, "status": -0.10},

        # 自主
        "choose":            {"autonomy": -0.20},
        "resist":            {"autonomy": -0.15},
        "assert":            {"autonomy": -0.15, "status": -0.05},

        # 求偶
        "flirt":             {"mating": -0.15, "social": -0.05},
        "court":             {"mating": -0.20, "social": -0.10},
        "intimate_action":   {"mating": -0.30, "social": -0.10, "comfort": -0.10},

        # 地位
        "compete":           {"status": -0.15, "competence": -0.05},
        "display":           {"status": -0.10},
        "lead":              {"status": -0.15, "autonomy": -0.05},

        # 正义
        "confront":          {"justice": -0.15},
        "protest":           {"justice": -0.10, "autonomy": -0.05},
        "report":            {"justice": -0.20},

        # 玩耍
        "joke":              {"play": -0.15, "social": -0.05},
        "play":              {"play": -0.25},
        "have_fun":          {"play": -0.20, "social": -0.05},

        # 恐慌/悲伤
        "cry":               {"panic": -0.20},
        "seek_comfort":      {"panic": -0.20, "social": -0.10, "safety": -0.05},

        # 照料
        "nurture":           {"care": -0.20, "social": -0.05},
        "protect":           {"care": -0.15, "safety": 0.05},
        "soothe":            {"care": -0.15, "panic": -0.10},

        # 撤退（社交回避提高社交需求）
        "withdraw":          {"safety": -0.10, "social": 0.10},

        # 空操作
        "idle":              {},
    }

    # ── 驱力 -> 首选行动（按优先级排序） ──
    DRIVE_ACTION_PREFS: dict[str, list[str]] = {
        "energy":     ["eat", "rest", "sleep"],
        "safety":     ["hide", "defend", "seek_shelter"],
        "rest":       ["rest", "sleep"],
        "social":     ["approach", "talk", "share"],
        "novelty":    ["explore", "investigate", "learn"],
        "competence": ["practice", "challenge", "achieve"],
        "autonomy":   ["choose", "resist", "assert"],
        "mating":     ["flirt", "court", "intimate_action"],
        "care":       ["nurture", "protect", "soothe"],
        "status":     ["compete", "display", "lead"],
        "justice":    ["confront", "protest", "report"],
        "seeking":    ["explore", "wander", "try_new"],
        "play":       ["joke", "play", "have_fun"],
        "panic":      ["cry", "seek_comfort", "withdraw"],
        "comfort":    ["seek_comfort", "rest"],
    }

    # ── 构造 ──

    def __init__(self, state: DriveState | None = None):
        self.state = state if state is not None else DriveState()

    # ── 核心更新 ──

    def update(
        self,
        dt_minutes: float,
        events: list[dict] | None = None,
        actions: list[str] | None = None,
    ) -> None:
        """更新所有驱力一个时间步。

        Args:
            dt_minutes: 时间步长（分钟）。每步最小 1 分钟以避免浮点不稳定。
            events: 该时间步内发生的事件列表，每项含 ``{"type": str, ...}``。
            actions: 该时间步内角色执行的行动列表。
        """
        dt_minutes = max(1.0, dt_minutes)

        # ─── 1. 自然衰减（驱力随未满足时间自然上升） ───
        for drive_name in self.DRIVE_NAMES:
            decay_rate = self.DECAY_RATES.get(drive_name, 0.0)
            old = _get_drive(self.state, drive_name)
            increase = decay_rate * dt_minutes / 60.0
            new = old + increase
            _set_drive(self.state, drive_name, min(1.0, max(0.0, new)))

        # ─── 2. 事件冲击 ───
        if events:
            for evt in events:
                self._apply_event(evt)

        # ─── 3. 行动消费 ───
        if actions:
            for action in actions:
                self._apply_action(action)

        # ─── 4. 自我调节（缓慢回归设定点） ───
        for drive_name in self.DRIVE_NAMES:
            current = _get_drive(self.state, drive_name)
            setpoint = self.SETPOINTS.get(drive_name, 0.2)
            deviation = current - setpoint
            regulation = deviation * 0.001 * dt_minutes  # 0.1%/min 回归速率
            new = current - regulation
            _set_drive(self.state, drive_name, min(1.0, max(0.0, new)))

    # ── 内部：事件/行动处理器 ──

    def _apply_event(self, event: dict) -> None:
        """应用单个事件对驱力的冲击。

        事件字典至少含 ``{"type": str}``。
        可能含 ``{"partner": ...}`` 上下文信息——影响浪漫事件的社交满足量。
        """
        event_type = event.get("type", "")
        impacts = self.EVENT_IMPACTS.get(event_type, {})

        if not impacts:
            return

        # 无伴侣的浪漫/亲密事件——社交满足折半
        has_partner = event.get("partner") is not None
        if event_type in ("romantic", "intimate") and not has_partner:
            impacts = impacts.copy()
            if "social" in impacts:
                impacts["social"] *= 0.3

        # 应用冲击
        for drive_name, delta in impacts.items():
            old = _get_drive(self.state, drive_name)
            new = old + delta
            _set_drive(self.state, drive_name, min(1.0, max(0.0, new)))

    def _apply_action(self, action: str) -> None:
        """应用单个行动对驱力的满足效果。"""
        satisfaction = self.ACTION_SATISFACTION.get(action, {})
        for drive_name, delta in satisfaction.items():
            old = _get_drive(self.state, drive_name)
            new = old + delta  # delta 为负值（满足）
            _set_drive(self.state, drive_name, min(1.0, max(0.0, new)))

    # ── W-Learning 行动选择 ──

    def select_action(self, available_actions: list[str]) -> str:
        """W-Learning 行动选择 (Humphrys 1995)。

        策略:
        1. **Crisis Mode**: 任一驱力 > 0.8 -> Winner-Take-All（最高紧迫度胜出）。
        2. **Normal Mode**: 各驱力按 ``驱力值^2`` 紧迫度投票 -> Softmax 选择。
        3. **SEEKING bonus**: 探索类行动额外获得 ``seeking_drive x 0.3`` 权重。
        4. **回退**: 无匹配行动时返回 ``"idle"``。

        Args:
            available_actions: 当前可用的行动名称列表。

        Returns:
            选中的行动名称。
        """
        drives = self.state.get_drive_vector()

        # ── 各驱力提案首选行动 ──
        proposals: dict[str, dict] = {}
        for drive_name, drive_level in drives.items():
            best_action = self._drive_preferred_action(drive_name, available_actions)
            if best_action is not None:
                proposals[drive_name] = {
                    "action": best_action,
                    "urgency": drive_level * drive_level,  # 二次紧迫度
                }

        if not proposals:
            return "idle"

        # ── Crisis Mode: Winner-Take-All ──
        crisis_drives = {k: v for k, v in proposals.items() if drives.get(k, 0) > 0.8}
        if crisis_drives:
            winner = max(crisis_drives.items(), key=lambda x: x[1]["urgency"])
            return winner[1]["action"]

        # ── Normal Mode: 分布式投票 + Softmax ──
        urgencies: dict[str, float] = {}
        for drive_name, prop in proposals.items():
            action = prop["action"]
            urgencies[action] = urgencies.get(action, 0.0) + prop["urgency"]

        # SEEKING 探索偏置
        seeking_level = drives.get("seeking", 0.5)
        for action in list(urgencies.keys()):
            if any(kw in action for kw in ("explore", "wander", "try_new", "investigate", "learn")):
                urgencies[action] += seeking_level * 0.3

        total = sum(urgencies.values())
        if total <= 0:
            return "idle"

        # Softmax 轮盘选择
        rand = random.random() * total
        cumulative = 0.0
        for action, urgency in sorted(urgencies.items(), key=lambda x: -x[1]):
            cumulative += urgency
            if rand <= cumulative:
                return action

        # Fallback（浮点舍入保护）
        return list(urgencies.keys())[0]

    def _drive_preferred_action(self, drive_name: str, available_actions: list[str]) -> str | None:
        """返回指定驱力在可用行动中的最优匹配。

        匹配策略:
        1. 精确匹配 ``DRIVE_ACTION_PREFS`` 中的行动。
        2. 前缀匹配：偏好行动在可用行动列表中有前缀匹配。
        3. 无匹配返回 ``None``。
        """
        prefs = self.DRIVE_ACTION_PREFS.get(drive_name, [])
        # 精确匹配
        for pref in prefs:
            if pref in available_actions:
                return pref
        # 前缀/模糊匹配
        for pref in prefs:
            for action in available_actions:
                if action.startswith(pref) or pref.startswith(action):
                    return action
        return None

    # ── 工具方法 ──

    def get_summary(self) -> dict[str, Any]:
        """返回驱力状态摘要（含层级分组 + 危急标记）。"""
        drives = self.state.get_drive_vector()
        tiers: dict[int, dict[str, float]] = {1: {}, 2: {}, 3: {}, 4: {}}
        for name, value in drives.items():
            t = DriveState.get_tier(name)
            tiers[t][name] = round(value, 3)

        return {
            "tiers": {
                1: {"label": "Survival Core", "drives": tiers[1]},
                2: {"label": "Mammalian Core", "drives": tiers[2]},
                3: {"label": "Richness", "drives": tiers[3]},
                4: {"label": "Panksepp Meta-Drives", "drives": tiers[4]},
            },
            "highest": {
                "drive": self.state.highest_drive()[0],
                "value": round(self.state.highest_drive()[1], 3),
            },
            "in_crisis": self.state.is_in_crisis(),
            "crisis_drives": [
                {"drive": n, "value": round(v, 3)}
                for n, v in self.state.crisis_drives()
            ],
        }

    # ── 持久化 ──

    def to_dict(self) -> dict[str, Any]:
        return self.state.to_dict()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DriveSystem":
        return cls(state=DriveState.from_dict(d))

    def __repr__(self) -> str:
        crisis = " [CRISIS]" if self.state.is_in_crisis() else ""
        high_name, high_val = self.state.highest_drive()
        return (
            f"DriveSystem(highest={high_name}={high_val:.2f}"
            f"{crisis}, "
            f"n_drives={len(self.DRIVE_NAMES)})"
        )


# ──────────────────────────────────────────
# 内部辅助（规避 getattr/setattr 字符串拼接噪声）
# ──────────────────────────────────────────

_DRIVE_ATTR_MAP: dict[str, str] = {
    "energy": "drive_energy",
    "safety": "drive_safety",
    "rest": "drive_rest",
    "social": "drive_social",
    "novelty": "drive_novelty",
    "competence": "drive_competence",
    "autonomy": "drive_autonomy",
    "comfort": "drive_comfort",
    "mating": "drive_mating",
    "care": "drive_care",
    "status": "drive_status",
    "justice": "drive_justice",
    "seeking": "drive_seeking",
    "play": "drive_play",
    "panic": "drive_panic",
}


def _get_drive(state: DriveState, name: str) -> float:
    return getattr(state, _DRIVE_ATTR_MAP[name])


def _set_drive(state: DriveState, name: str, value: float) -> None:
    setattr(state, _DRIVE_ATTR_MAP[name], value)
