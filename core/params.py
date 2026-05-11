"""统一参数体系 — 24 个心理学模型合并去重后的 30 个核心参数。

每个参数可以同时有 baseline (慢分量) 和 activation (快分量):
  有效值 = baseline + activation × (1 - baseline)
  baseline 每次只能微调, activation 可以瞬间全幅跳变。

来源映射:
  Plutchik + Smith-Ellsworth + PAD                  → 基础情感 8+3 维
  OCC + Smith-Ellsworth                             → 认知评估 9 维
  Sternberg + Marion + Gottman + Strogatz + Fisher  → 关系维度 8 维
  Defense + PTSD + Safety                           → 防御安全 4 维
  SDT + Maslow + Drive                              → 动机需求 5 维
  Attachment + Schema + ACE + Self                  → 依恋自我 7 维
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# 参数定义
# ═══════════════════════════════════════════════════════════════

class ChangeSpeed(Enum):
    RAPID = "rapid"       # 秒级——单轮可 0↔0.9 全幅
    MEDIUM = "medium"     # 分钟级——3-5 轮
    SLOW = "slow"         # 天级——数十次互动


@dataclass
class Param:
    """单个心理参数"""
    name: str
    range_min: float = 0.0
    range_max: float = 1.0
    default: float = 0.5
    speed: ChangeSpeed = ChangeSpeed.MEDIUM
    description: str = ""

    # 双分量
    baseline: float = 0.5      # 慢分量——稳定人格倾向
    activation: float = 0.0    # 快分量——情境触发

    @property
    def effective(self) -> float:
        """有效值 = baseline + activation × (1 - baseline)。"""
        val = self.baseline + self.activation * (1.0 - self.baseline)
        return max(self.range_min, min(self.range_max, val))

    def set_activation(self, value: float):
        self.activation = max(0.0, min(1.0, value))

    def set_baseline(self, value: float):
        self.baseline = max(self.range_min, min(self.range_max, value))

    def decay_activation(self, rate: float = 0.3):
        """Activation 自然衰减。"""
        self.activation *= (1.0 - rate)

    def to_dict(self) -> dict:
        return {
            "baseline": round(self.baseline, 3),
            "activation": round(self.activation, 3),
            "effective": round(self.effective, 3),
            "speed": self.speed.value,
        }


# ═══════════════════════════════════════════════════════════════
# 30 个统一参数
# ═══════════════════════════════════════════════════════════════

@dataclass
class UnifiedParams:
    """30 个统一心理参数——覆盖旧项目 24 个 Skill 的全部维度。"""

    # ── 基础情感 (PAD + Plutchik — 3+8=11 维) ──

    pleasure: Param = field(default_factory=lambda: Param(
        "pleasure", -1.0, 1.0, 0.0, ChangeSpeed.RAPID, "愉悦度"))
    arousal: Param = field(default_factory=lambda: Param(
        "arousal", 0.0, 1.0, 0.3, ChangeSpeed.RAPID, "唤醒度"))
    dominance: Param = field(default_factory=lambda: Param(
        "dominance", -1.0, 1.0, 0.0, ChangeSpeed.MEDIUM, "支配感"))

    joy: Param = field(default_factory=lambda: Param(
        "joy", 0.0, 1.0, 0.3, ChangeSpeed.RAPID, "喜悦"))
    sadness: Param = field(default_factory=lambda: Param(
        "sadness", 0.0, 1.0, 0.15, ChangeSpeed.RAPID, "悲伤"))
    trust: Param = field(default_factory=lambda: Param(
        "trust", 0.0, 1.0, 0.4, ChangeSpeed.MEDIUM, "信任"))
    disgust: Param = field(default_factory=lambda: Param(
        "disgust", 0.0, 1.0, 0.05, ChangeSpeed.RAPID, "厌恶"))
    fear: Param = field(default_factory=lambda: Param(
        "fear", 0.0, 1.0, 0.15, ChangeSpeed.RAPID, "恐惧"))
    anger: Param = field(default_factory=lambda: Param(
        "anger", 0.0, 1.0, 0.05, ChangeSpeed.RAPID, "愤怒"))
    surprise: Param = field(default_factory=lambda: Param(
        "surprise", 0.0, 1.0, 0.1, ChangeSpeed.RAPID, "惊讶"))
    anticipation: Param = field(default_factory=lambda: Param(
        "anticipation", 0.0, 1.0, 0.2, ChangeSpeed.MEDIUM, "期待"))

    # ── 认知评估 (OCC + Smith-Ellsworth — 9 维) ──

    goal_conduciveness: Param = field(default_factory=lambda: Param(
        "goal_conduciveness", -1.0, 1.0, 0.0, ChangeSpeed.RAPID, "目标促进/阻碍"))
    goal_relevance: Param = field(default_factory=lambda: Param(
        "goal_relevance", 0.0, 1.0, 0.5, ChangeSpeed.RAPID, "目标相关性"))
    coping_potential: Param = field(default_factory=lambda: Param(
        "coping_potential", 0.0, 1.0, 0.5, ChangeSpeed.MEDIUM, "应对潜力"))
    unexpectedness: Param = field(default_factory=lambda: Param(
        "unexpectedness", 0.0, 1.0, 0.5, ChangeSpeed.RAPID, "意外程度"))
    certainty: Param = field(default_factory=lambda: Param(
        "certainty", 0.0, 1.0, 0.5, ChangeSpeed.MEDIUM, "确定性"))
    urgency: Param = field(default_factory=lambda: Param(
        "urgency", 0.0, 1.0, 0.3, ChangeSpeed.RAPID, "紧迫性"))
    future_expectancy: Param = field(default_factory=lambda: Param(
        "future_expectancy", 0.0, 1.0, 0.5, ChangeSpeed.SLOW, "未来预期"))
    norm_compatibility: Param = field(default_factory=lambda: Param(
        "norm_compatibility", -1.0, 1.0, 0.0, ChangeSpeed.SLOW, "规范相容性"))
    legitimacy: Param = field(default_factory=lambda: Param(
        "legitimacy", -1.0, 1.0, 0.0, ChangeSpeed.MEDIUM, "正当性"))

    # ── 关系维度 (Sternberg + Marion + Gottman — 8 维) ──

    intimacy: Param = field(default_factory=lambda: Param(
        "intimacy", 0.0, 1.0, 0.2, ChangeSpeed.SLOW, "亲密感(基线)"))
    passion: Param = field(default_factory=lambda: Param(
        "passion", 0.0, 1.0, 0.2, ChangeSpeed.MEDIUM, "激情"))
    commitment: Param = field(default_factory=lambda: Param(
        "commitment", 0.0, 1.0, 0.3, ChangeSpeed.SLOW, "承诺/誓约强度"))
    sexual_baseline: Param = field(default_factory=lambda: Param(
        "sexual_baseline", 0.0, 1.0, 0.05, ChangeSpeed.SLOW, "性舒适度(基线)"))
    sexual_activation: Param = field(default_factory=lambda: Param(
        "sexual_activation", 0.0, 1.0, 0.0, ChangeSpeed.RAPID, "性唤起(快分量)——可以瞬间0→0.9"))
    positive_ratio: Param = field(default_factory=lambda: Param(
        "positive_ratio", 0.0, 10.0, 3.0, ChangeSpeed.MEDIUM, "正/负互动比"))
    flooding_risk: Param = field(default_factory=lambda: Param(
        "flooding_risk", 0.0, 1.0, 0.2, ChangeSpeed.RAPID, "情绪淹没风险"))
    repair_detected: Param = field(default_factory=lambda: Param(
        "repair_detected", 0.0, 1.0, 0.0, ChangeSpeed.RAPID, "修复尝试检测"))

    # ── 防御安全 (Defense + PTSD + 贝叶斯精度 — 4 维) ──

    defense_intensity: Param = field(default_factory=lambda: Param(
        "defense_intensity", 0.0, 1.0, 0.15, ChangeSpeed.RAPID, "防御机制强度"))
    defense_level: Param = field(default_factory=lambda: Param(
        "defense_level", 1.0, 4.0, 3.0, ChangeSpeed.SLOW, "防御成熟度(1-4)"))
    threat_precision: Param = field(default_factory=lambda: Param(
        "threat_precision", 0.0, 1.0, 0.3, ChangeSpeed.RAPID, "威胁信号精度——贝叶斯脑的precision_threat"))
    safety_precision: Param = field(default_factory=lambda: Param(
        "safety_precision", 0.0, 1.0, 0.5, ChangeSpeed.RAPID, "安全信号精度——贝叶斯脑的precision_safety"))

    # ── 动机需求 (SDT + Maslow + Drive — 5 维) ──

    autonomy: Param = field(default_factory=lambda: Param(
        "autonomy", 0.0, 1.0, 0.5, ChangeSpeed.SLOW, "自主性"))
    competence: Param = field(default_factory=lambda: Param(
        "competence", 0.0, 1.0, 0.5, ChangeSpeed.MEDIUM, "胜任感"))
    relatedness: Param = field(default_factory=lambda: Param(
        "relatedness", 0.0, 1.0, 0.4, ChangeSpeed.MEDIUM, "归属/连接感"))
    intrinsic_motivation: Param = field(default_factory=lambda: Param(
        "intrinsic_motivation", 0.0, 1.0, 0.5, ChangeSpeed.MEDIUM, "内在动机"))
    dominant_need: Param = field(default_factory=lambda: Param(
        "dominant_need", 1.0, 5.0, 3.0, ChangeSpeed.SLOW, "主导需求层级(Maslow 1-5)"))

    # ── 依恋自我 (Attachment + Schema + ACE + Self — 7 维) ──

    attachment_activation: Param = field(default_factory=lambda: Param(
        "attachment_activation", 0.0, 1.0, 0.3, ChangeSpeed.RAPID, "依恋系统激活"))
    self_worth: Param = field(default_factory=lambda: Param(
        "self_worth", 0.0, 1.0, 0.6, ChangeSpeed.SLOW, "核心自我价值"))
    expressiveness: Param = field(default_factory=lambda: Param(
        "expressiveness", 0.0, 1.0, 0.3, ChangeSpeed.SLOW, "情感表达开放度(基线)"))
    playfulness: Param = field(default_factory=lambda: Param(
        "playfulness", 0.0, 1.0, 0.15, ChangeSpeed.MEDIUM, "撒娇/玩心倾向"))
    schema_reinforcement: Param = field(default_factory=lambda: Param(
        "schema_reinforcement", 0.0, 1.0, 0.5, ChangeSpeed.SLOW, "图式强化风险"))
    ace_activation: Param = field(default_factory=lambda: Param(
        "ace_activation", 0.0, 1.0, 0.0, ChangeSpeed.RAPID, "ACE创伤激活"))
    self_update_openness: Param = field(default_factory=lambda: Param(
        "self_update_openness", 0.0, 1.0, 0.15, ChangeSpeed.SLOW, "被他者重塑的开放度——爱的核心参数"))

    # ── Love Engine 参数 ──

    oath_strength: Param = field(default_factory=lambda: Param(
        "oath_strength", 0.0, 1.0, 0.0, ChangeSpeed.SLOW, "誓约强度——爱中的意志决断"))
    irreducibility_gamma: Param = field(default_factory=lambda: Param(
        "irreducibility_gamma", 0.0, 1.0, 0.0, ChangeSpeed.SLOW, "不可压缩性先验强度——γ_sat，奖励保持他者不确定性"))

    # ═══ 跨参数耦合 ═══

    def true_effective(self, name: str) -> float:
        """计算考虑跨参数依赖的真实有效值。

        耦合关系:
        - sexual_activation 的基线 = sexual_baseline
          有效 sexual = sexual_baseline.effective + sexual_activation.activation × (1 - sexual_baseline.effective)
        - intimacy 的基线耦合 self_worth
        - playfulness 的基线耦合 safety_precision (安全感不够时玩不起来)
        """
        p = self.get(name)
        if not p:
            return 0.0

        if name == "sexual_activation":
            sb = self.sexual_baseline.effective
            return sb + p.activation * (1.0 - sb)

        if name == "playfulness":
            # 玩心受安全感的门控: 安全感低 → 玩心被抑制
            safety_gate = self.safety_precision.effective
            raw = p.effective
            return raw * (0.3 + 0.7 * safety_gate)

        if name == "expressiveness":
            # 低 s 时即使激活高，外显也受抑制——这就是"反差"的计算
            intimacy_gate = self.intimacy.baseline
            raw = p.effective
            return raw * (0.2 + 0.8 * intimacy_gate)

        if name == "intimacy":
            # 亲密感受 self_worth 影响——自我价值低时难以感到亲密
            sw = self.self_worth.effective
            return p.effective * (0.5 + 0.5 * sw)

        return p.effective

    # ═══ 便捷访问 ═══

    def all_params(self) -> dict[str, Param]:
        """所有参数的名称→Param 映射。"""
        result = {}
        for field_name in self.__dataclass_fields__:
            val = getattr(self, field_name)
            if isinstance(val, Param):
                result[field_name] = val
        return result

    def get(self, name: str) -> Param | None:
        return self.all_params().get(name)

    def by_speed(self, speed: ChangeSpeed) -> dict[str, Param]:
        return {n: p for n, p in self.all_params().items() if p.speed == speed}

    # ═══ 衰减 ═══

    def decay_all_activations(self, rate: float = 0.25):
        """所有快分量自然衰减——每轮调用。"""
        for p in self.all_params().values():
            if p.speed == ChangeSpeed.RAPID:
                p.decay_activation(rate)
            elif p.speed == ChangeSpeed.MEDIUM:
                p.decay_activation(rate * 0.3)

    # ═══ Coherence 约束 ═══

    def check_coherence(self) -> list[str]:
        """检查参数配置的合理性。返回违规列表。"""
        violations = []
        p = self  # shorthand

        # 不能同时高威胁 + 高安全
        if p.threat_precision.effective > 0.7 and p.safety_precision.effective > 0.7:
            violations.append("威胁精度和安全精度同时高于 0.7——状态 incoherent")

        # 不能同时高 playfulness + 高 sadness
        if p.playfulness.effective > 0.6 and p.sadness.effective > 0.6:
            violations.append("玩心和悲伤同时高于 0.6——状态 incoherent")

        # 不能同时高防御 + 高开放
        if p.defense_intensity.effective > 0.6 and p.self_update_openness.effective > 0.5:
            violations.append("高防御 + 高自我更新开放——状态 incoherent")

        # 性唤起需要亲密感基础
        if p.sexual_activation.effective > 0.6 and p.intimacy.baseline < 0.2:
            violations.append("性唤起高但亲密基线很低——可能存在 coherence 问题")

        # 恐惧 + 愤怒不能同时极高
        if p.fear.effective > 0.8 and p.anger.effective > 0.8:
            violations.append("恐惧和愤怒同时 > 0.8——状态 incoherent")

        return violations

    def auto_correct(self):
        """自动修正 incoherent 状态——降低冲突参数的 activation。"""
        violations = self.check_coherence()
        if not violations:
            return

        for v in violations:
            if "威胁精度和安全精度" in v:
                # 保留较高的那个，降低较低的那个
                if self.threat_precision.effective > self.safety_precision.effective:
                    self.safety_precision.activation *= 0.3
                else:
                    self.threat_precision.activation *= 0.3
            if "玩心和悲伤" in v:
                self.playfulness.activation *= 0.3
                self.sadness.activation *= 0.3
            if "高防御 + 高自我更新开放" in v:
                self.self_update_openness.activation *= 0.3
            if "恐惧和愤怒" in v:
                self.fear.activation *= 0.5
                self.anger.activation *= 0.5

    # ═══ 快照 ═══

    def snapshot(self) -> dict:
        """所有参数有效值的快照。"""
        return {name: round(p.effective, 3)
                for name, p in self.all_params().items()}

    def activation_snapshot(self) -> dict:
        """所有快分量的快照。"""
        return {name: round(p.activation, 3)
                for name, p in self.all_params().items()}

    def baseline_snapshot(self) -> dict:
        """所有慢分量的快照。"""
        return {name: round(p.baseline, 3)
                for name, p in self.all_params().items()}

    # ═══ 从字典恢复 ═══

    def apply_snapshot(self, snap: dict):
        """从 snapshot 恢复 activation 值。"""
        for name, value in snap.items():
            p = self.get(name)
            if p:
                p.set_activation(value)

    def apply_baseline_snapshot(self, snap: dict):
        """从 baseline_snapshot 恢复 baseline 值。"""
        for name, value in snap.items():
            p = self.get(name)
            if p:
                p.set_baseline(value)
