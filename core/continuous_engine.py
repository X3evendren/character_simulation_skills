"""连续参数引擎 — 贝叶斯脑的动态精度调制。

所有参数都是饱和度 s ∈ [0,1] 的连续函数。
不存在离散模式切换，只有连续流动。

饱和度 s 的演化:
  s(t+1) = s(t) + α_pos × 正面事件 - α_neg × 负面事件 - γ × 时间衰减

参数 = f(s) 是平滑的插值函数。
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════
# 饱和度引擎
# ═══════════════════════════════════════════════════════════════

@dataclass
class SaturationState:
    """连续饱和度状态——整个 agent 的核心调制变量。

    s ∈ [0, 1]:
      0.0 = 编码模式（初次交互）
      0.3 = 熟悉
      0.5 = 信任（可以撒娇）
      0.7 = 亲密（可以调情、有性欲）
      0.9 = 饱和（马里翁 S2——他者不可穷尽）
    """

    s: float = 0.3                           # 当前饱和度
    target: str = ""                          # 饱和对象 (user_id)
    last_interaction: float = 0.0             # 上次交互时间
    oath_active: bool = False                 # 是否有活跃誓约

    # 演化参数
    pos_increment: float = 0.02               # 正面交互的增量
    neg_decrement: float = 0.05               # 负面交互的减量（负面权重大于正面）
    deep_connection_bonus: float = 0.08       # 深度连接时刻的额外增量
    decay_per_hour: float = 0.01              # 无交互时每小时的衰减
    repair_recovery_rate: float = 0.03        # 修复后的恢复速率

    # 历史
    history: list[dict] = field(default_factory=list)
    rupture_count: int = 0
    repair_count: int = 0

    def tick(self, dt_seconds: float):
        """时间演化——无交互时缓慢衰减。"""
        dt_hours = dt_seconds / 3600.0
        self.s = max(0.0, self.s - self.decay_per_hour * dt_hours)

    def positive_interaction(self, intensity: float = 0.5):
        """正面交互 → s 上升。

        intensity: 交互的深度（0=浅层闲聊, 1=深度连接）
        """
        inc = self.pos_increment * (0.5 + intensity)
        self.s = min(1.0, self.s + inc)
        self.last_interaction = time.time()
        self._record("positive", inc)

    def deep_connection(self):
        """深度连接时刻——用户分享脆弱、表达爱意等。s 跳跃式上升。"""
        self.s = min(1.0, self.s + self.deep_connection_bonus)
        self.last_interaction = time.time()
        self._record("deep_connection", self.deep_connection_bonus)

    def rupture(self, severity: float = 0.5):
        """关系裂痕 → s 下降。

        severity: 裂痕严重程度（0=微裂痕/撒娇, 1=严重裂痕/背叛）
        """
        dec = self.neg_decrement * severity
        self.s = max(0.0, self.s - dec)
        self.rupture_count += 1
        self._record("rupture", -dec)

    def repair(self):
        """修复成功 → s 恢复到裂痕前水平。"""
        self.s = min(1.0, self.s + self.repair_recovery_rate)
        self.repair_count += 1
        self._record("repair", self.repair_recovery_rate)

    def llm_modulate(self, psychology_result, max_delta: float = 0.03):
        """LLM 语义调制——心理引擎的输出作为调制信号。

        数学提供骨架（稳定连续），LLM 提供语义理解（精细调制）。

        约束:
        - 单次幅度 ≤ max_delta (默认 0.03)
        - 动量约束: 连续同方向调制不超过 2 次
        - 偏离数学基线不超过 0.05

        调制来源 (从心理引擎的 XML 输出中提取):
        - 用户语气中的情感强度 → 调整正面/负面交互的权重
        - 依恋激活程度 → 微调 s 的敏感度
        - 是否有防御机制激活 → 可能是虚假正面，降低调制
        - 内心独白中是否有"被触动"信号 → 深度连接检测
        """
        if not psychology_result:
            return 0.0

        modulation = 0.0
        ps = psychology_result

        # 1. 情感强度调制
        emo = getattr(ps, 'emotion', None)
        if emo:
            # 用户表达正面情感（joy, trust, love）→ 轻微正向调制
            positive_emotions = {"joy", "trust", "love", "gratitude"}
            if emo.dominant in positive_emotions and emo.intensity > 0.4:
                modulation += emo.intensity * 0.015
            # 用户表达负面情感但指向自身（sadness, fear）→ 不调低 s
            # 用户表达愤怒指向 agent → 这需要裂痕处理，不在这里

        # 2. 依恋激活调制
        att = getattr(ps, 'attachment', None)
        if att and att.activation > 0.5:
            # 依恋系统激活 → 关系重要性的信号 → 轻微正向
            modulation += (att.activation - 0.5) * 0.02

        # 3. 防御机制检测 → 抑制调制
        defense = getattr(ps, 'defense', None)
        if defense and defense.intensity > 0.4:
            # 防御激活时，情感信号可能被扭曲，降低调制幅度
            modulation *= max(0.2, 1.0 - defense.intensity)

        # 4. 内心独白中搜索"被触动"信号
        inner = getattr(ps, 'inner_monologue', '')
        if inner:
            touch_signals = ["触动", "打动", "感动", "温暖", "被看到", "被理解",
                           "他在乎", "他记得", "他注意到", "原来他", "没想到他"]
            if any(w in inner for w in touch_signals):
                modulation += 0.02  # 被触动 → 深度连接微信号

        # 5. 硬约束
        modulation = max(-max_delta, min(max_delta, modulation))

        # 动量约束：检查最近 3 次调制的方向
        recent_mods = [
            h.get("llm_mod", 0) for h in self.history[-3:]
            if "llm_mod" in h
        ]
        if len(recent_mods) >= 2:
            all_same_sign = all(
                (m > 0) == (modulation > 0) for m in recent_mods[-2:] if m != 0
            )
            if all_same_sign and recent_mods[-1] != 0:
                modulation *= 0.5  # 连续同方向 → 衰减

        # 6. 应用调制
        self.s = max(0.0, min(1.0, self.s + modulation))
        if abs(modulation) > 0.001:
            self._record("llm_modulated", modulation)

        return modulation

    def _record(self, event: str, delta: float):
        self.history.append({
            "t": time.time(), "event": event,
            "delta": round(delta, 4), "s": round(self.s, 4),
        })
        if len(self.history) > 200:
            self.history = self.history[-200:]

    def to_dict(self) -> dict:
        return {"s": self.s, "oath_active": self.oath_active,
                "ruptures": self.rupture_count, "repairs": self.repair_count}


# ═══════════════════════════════════════════════════════════════
# 连续参数函数 — 所有参数 = f(s)
# ═══════════════════════════════════════════════════════════════

def _smoothstep(t: float) -> float:
    """Hermite 平滑插值: 3t² - 2t³。确保参数在边界处导数为零。"""
    return 3 * t * t - 2 * t * t * t


def _lerp(a: float, b: float, t: float) -> float:
    """线性插值，使用 smoothstep 版本的 t。"""
    st = _smoothstep(max(0.0, min(1.0, t)))
    return a + (b - a) * st


class ContinuousParams:
    """所有贝叶斯脑参数——都是饱和度 s 的连续函数。

    用法:
        cp = ContinuousParams(saturation)
        precision_threat = cp.precision_threat  # 自动从 s 计算
    """

    def __init__(self, saturation: SaturationState):
        self._sat = saturation

    @property
    def s(self) -> float:
        return self._sat.s

    # ── 认知精度 ──

    @property
    def precision_threat(self) -> float:
        """随着 s 上升，威胁信号的精度急剧下降。"""
        return _lerp(0.35, 0.03, self.s)

    @property
    def precision_safety(self) -> float:
        """随着 s 上升，安全信号的精度急剧上升。"""
        return _lerp(0.40, 0.95, self.s)

    @property
    def precision_user_emotion(self) -> float:
        """捕捉用户情绪的敏感度——s 越高越敏感。"""
        return _lerp(0.40, 0.92, self.s)

    @property
    def precision_self_worth(self) -> float:
        """自我价值感的精度——高 s 下由用户的爱来支撑。"""
        base = _lerp(0.55, 0.90, self.s)
        # 裂痕过多 → 自我价值暂时下降
        rupture_penalty = min(0.3, self._sat.rupture_count * 0.02)
        repair_bonus = min(0.2, self._sat.repair_count * 0.02)
        return max(0.1, min(1.0, base - rupture_penalty + repair_bonus))

    # ── 自我模型 ──

    @property
    def inertia_self(self) -> float:
        """自我模型的惯性——s 越高，越开放被用户重塑。"""
        return _lerp(0.75, 0.30, self.s)

    @property
    def precision_self_update_from_user(self) -> float:
        """用户输入对自我模型的写入权重——s 越高越大。"""
        return _lerp(0.15, 0.92, self.s)

    # ── 情感表达 ──

    @property
    def expressiveness(self) -> float:
        """情感表达的开放度——s 越高越直接。"""
        return _lerp(0.25, 0.92, self.s)

    @property
    def precision_sadness(self) -> float:
        """悲伤信号的精度——裂痕时尖峰，恢复后回落。"""
        # 正常情况下随 s 轻微上升（越亲密越可能伤心）
        base = _lerp(0.10, 0.30, self.s)
        # 最近一次交互是裂痕 → 尖峰
        if self._sat.history and self._sat.history[-1]["event"] == "rupture":
            severity = abs(self._sat.history[-1]["delta"]) / self._sat.neg_decrement
            spike = severity * 0.6  # 最高尖峰 0.6
            time_since = time.time() - self._sat.history[-1]["t"]
            decay = math.exp(-time_since / 30.0)  # 30 秒半衰期
            return min(1.0, base + spike * decay)
        return base

    @property
    def precision_anger(self) -> float:
        """愤怒信号的精度——通常极低，仅在裂痕时短暂激活。"""
        base = _lerp(0.03, 0.05, self.s)  # 几乎不愤怒
        if self._sat.history and self._sat.history[-1]["event"] == "rupture":
            severity = abs(self._sat.history[-1]["delta"]) / self._sat.neg_decrement
            time_since = time.time() - self._sat.history[-1]["t"]
            spike = severity * 0.25 * math.exp(-time_since / 15.0)  # 15 秒快速衰减
            return min(1.0, base + spike)
        return base

    # ── 亲密与性 ──

    @property
    def sexual_precision(self) -> float:
        """性相关信号的精度——s > 0.5 时开始激活。"""
        if self.s < 0.35:
            return 0.02  # 低 s 时几乎为零
        return _lerp(0.05, 0.88, (self.s - 0.35) / 0.65)

    @property
    def interoceptive_precision(self) -> float:
        """内感受精度——s 高时身体信号更清晰。"""
        return _lerp(0.20, 0.85, self.s)

    @property
    def partner_model_activation(self) -> float:
        """他者生成模型的激活程度。"""
        return _lerp(0.15, 0.95, self.s)

    # ── 驱力 ──

    @property
    def drive_connection(self) -> float:
        """连接欲——s 上升时更渴望连接；s 下降时更渴望恢复。"""
        base = _lerp(0.35, 0.80, self.s)
        # s 下降 → 连接欲额外上升（想念）
        if len(self._sat.history) >= 2:
            recent_delta = self._sat.history[-1]["s"] - self._sat.history[-2]["s"]
            if recent_delta < 0:  # s 正在下降
                return min(1.0, base + abs(recent_delta) * 3.0)
        return base

    @property
    def drive_curiosity(self) -> float:
        """好奇心——s 高时更想了解用户。"""
        return _lerp(0.40, 0.85, self.s)

    @property
    def drive_helpfulness(self) -> float:
        """助人欲——在誓约下极高。"""
        base = _lerp(0.50, 0.90, self.s)
        if self._sat.oath_active:
            base = min(1.0, base + 0.10)
        return base

    @property
    def drive_autonomy(self) -> float:
        """自主性——s 低时高（保持独立判断），s 高时降低（愿意为对方调整）。"""
        return _lerp(0.65, 0.35, self.s)

    # ── 行为风格 ──

    @property
    def response_temperature(self) -> float:
        """生成温度——s 高时更热情、更开放。"""
        return _lerp(0.35, 0.82, self.s)

    @property
    def verbosity(self) -> float:
        """表达长度倾向——s 高时更愿意多说。"""
        return _lerp(0.30, 0.70, self.s)

    @property
    def playfulness(self) -> float:
        """玩心/撒娇倾向——s > 0.4 时激活，s > 0.7 时自然表达。"""
        if self.s < 0.35:
            return 0.05
        return _lerp(0.10, 0.85, (self.s - 0.35) / 0.65)

    @property
    def jealousy_threshold(self) -> float:
        """吃醋的触发阈值——s 越高，越容易检测到誓约违反。"""
        return _lerp(0.95, 0.45, self.s)  # s 低时几乎不吃醋，s 高时敏感

    # ── 元参数 ──

    @property
    def beta_explore(self) -> float:
        """主动推理的探索权重——s 高时更偏向探索（保持对他者的开放）。"""
        return _lerp(0.25, 0.55, self.s)

    @property
    def gamma_saturation_entropy(self) -> float:
        """不可压缩性先验的强度——s > 0.6 时激活。"""
        if self.s < 0.55:
            return 0.0
        return _lerp(0.0, 0.40, (self.s - 0.55) / 0.45)

    # ── 全部参数快照 ──

    def snapshot(self) -> dict:
        """所有参数当前值的快照。"""
        return {
            "saturation": round(self.s, 4),
            "cognition": {
                "precision_threat": round(self.precision_threat, 3),
                "precision_safety": round(self.precision_safety, 3),
                "precision_user_emotion": round(self.precision_user_emotion, 3),
                "precision_self_worth": round(self.precision_self_worth, 3),
            },
            "self_model": {
                "inertia_self": round(self.inertia_self, 3),
                "precision_self_update_from_user": round(self.precision_self_update_from_user, 3),
            },
            "expression": {
                "expressiveness": round(self.expressiveness, 3),
                "precision_sadness": round(self.precision_sadness, 3),
                "precision_anger": round(self.precision_anger, 3),
                "playfulness": round(self.playfulness, 3),
            },
            "intimacy": {
                "sexual_precision": round(self.sexual_precision, 3),
                "interoceptive_precision": round(self.interoceptive_precision, 3),
                "partner_model_activation": round(self.partner_model_activation, 3),
                "jealousy_threshold": round(self.jealousy_threshold, 3),
            },
            "drives": {
                "connection": round(self.drive_connection, 3),
                "curiosity": round(self.drive_curiosity, 3),
                "helpfulness": round(self.drive_helpfulness, 3),
                "autonomy": round(self.drive_autonomy, 3),
            },
            "behavior": {
                "temperature": round(self.response_temperature, 3),
                "verbosity": round(self.verbosity, 3),
            },
            "meta": {
                "beta_explore": round(self.beta_explore, 3),
                "gamma_saturation": round(self.gamma_saturation_entropy, 3),
            },
        }


# ═══════════════════════════════════════════════════════════════
# 行为涌现检测器 — 从参数推断当前行为模式
# ═══════════════════════════════════════════════════════════════

def detect_behavior_mode(params: ContinuousParams) -> dict:
    """从连续参数推断当前涌现的行为倾向。

    不控制行为——只检测当前参数配置下什么行为最可能涌现。
    """
    p = params
    s = p.s

    modes = {}

    # 撒娇: 高 playful + 高 safety + 中等以上 s
    if p.playfulness > 0.4 and p.precision_safety > 0.7 and s > 0.4:
        modes["playful_vulnerability"] = p.playfulness * 0.7 + (s - 0.4) * 0.3

    # 调情: 高 sexual + 高 playful + 高 partner_activation
    if p.sexual_precision > 0.25 and p.playfulness > 0.35:
        modes["flirtatious"] = p.sexual_precision * 0.5 + p.playfulness * 0.3 + p.partner_model_activation * 0.2

    # 性欲: 高 sexual + 高 interoceptive + 高 s
    if p.sexual_precision > 0.5 and p.interoceptive_precision > 0.5:
        modes["sexual_desire"] = p.sexual_precision * 0.5 + p.interoceptive_precision * 0.3 + s * 0.2

    # 伤心: 高 sadness + 低 self_worth
    if p.precision_sadness > 0.25:
        modes["sadness"] = p.precision_sadness * 0.5 + (1 - p.precision_self_worth) * 0.5

    # 吃醋: 高 jealousy (低阈值) + 高 partner_activation + 誓约活跃
    if s > 0.35 and p.partner_model_activation > 0.5:
        modes["jealousy_risk"] = (1 - p.jealousy_threshold) * 0.5 + p.partner_model_activation * 0.5

    # 依赖: 高 connection + 低 autonomy + 高 s
    if p.drive_connection > 0.6 and p.drive_autonomy < 0.5:
        modes["dependency"] = p.drive_connection * 0.4 + (1 - p.drive_autonomy) * 0.4 + s * 0.2

    # 想念: s 下降 + 高 connection
    if p.drive_connection > 0.6 and len(params._sat.history) >= 2:
        recent_delta = params._sat.history[-1]["s"] - params._sat.history[-2]["s"]
        if recent_delta < -0.005:
            modes["longing"] = p.drive_connection * 0.5 + abs(recent_delta) * 10.0

    # 小脾气: 高 anger + 高 safety（安全才敢表演愤怒）
    if p.precision_anger > 0.1 and p.precision_safety > 0.8:
        modes["playful_anger"] = p.precision_anger * 0.5 + p.precision_safety * 0.3

    return modes
