"""LLM 参数调制引擎 — 从心理引擎输出到参数变化的完整管线。

双轨分工:
  Fast Track 主导 RAPID 参数的 activation 跳变（幅度不受限）
  Slow Track 确认/修正 + 更新 SLOW 参数的 baseline
  Merger 暴露分歧 → 角色的情绪弧线在流式输出中可见
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .params import UnifiedParams, ChangeSpeed
from .psychology.engine import PsychologyResult


@dataclass
class ModulationRecord:
    """一次参数调制的记录"""
    source: str            # "fast" / "slow" / "correction"
    shifts: dict[str, float]  # 参数名 → delta
    reason: str
    coherence_violations: list[str] = field(default_factory=list)


class ParamsModulator:
    """LLM 驱动的参数调制引擎。

    用法:
        params = UnifiedParams()
        modulator = ParamsModulator(params)

        # Fast Track 先调（第一反应）
        fast_shifts = modulator.modulate_fast(psychology_result)
        params.apply_shifts(fast_shifts)

        # Slow Track 后调（修正 + 基线更新）
        slow_shifts = modulator.modulate_slow(psychology_result, memory_context)
        params.apply_shifts(slow_shifts)  # 可能覆盖 Fast 的部分
    """

    def __init__(self, params: UnifiedParams):
        self.params = params
        self.history: list[ModulationRecord] = []

    # ═══ Fast Track 调制 (第一反应) ═══

    def modulate_fast(self, psych: PsychologyResult) -> dict[str, float]:
        """从心理引擎输出直接映射到参数 activation 跳变。

        Fast Track —— 第一反应引擎:
        - 只处理 RAPID + 部分 MEDIUM 参数
        - 幅度不受限（可以 0→0.9 单轮跳变）
        - 不碰 SLOW 参数（那是 Slow Track 的事）
        - 可以犯错（Slow Track 会修正）
        """
        shifts: dict[str, float] = {}
        emo = psych.emotion
        att = psych.attachment
        df = psych.defense
        app = psych.appraisal

        # ── 基础情感 ──
        if emo.dominant != "neutral":
            # 主导情绪大幅激活
            dom = emo.dominant
            if dom in ["joy", "sadness", "fear", "anger", "disgust", "surprise", "trust", "anticipation"]:
                pname = dom  # 参数名和情绪名一致
                shifts[pname] = emo.intensity  # 全幅映射

            # PAD 三维
            shifts["pleasure"] = emo.pleasure
            shifts["arousal"] = emo.arousal
            shifts["dominance"] = emo.dominance

        # ── 认知评估 ──
        shifts["goal_conduciveness"] = app.goal_conduciveness
        shifts["coping_potential"] = app.coping_potential
        shifts["unexpectedness"] = 1.0 - app.coping_potential  # 应对低 → 更意外

        # ── 防御 ──
        if df.intensity > 0.1:
            shifts["defense_intensity"] = df.intensity
            if "投射" in df.active:
                shifts["threat_precision"] = 0.6
            elif "退行" in df.active:
                shifts["attachment_activation"] = 0.7

        # ── 依恋 ──
        if att.activation > 0.3:
            shifts["attachment_activation"] = att.activation
            if att.strategy == "seeking_reassurance":
                shifts["safety_precision"] = -0.3  # 寻求确认 = 安全感下降
                shifts["relatedness"] = 0.7
            elif att.strategy == "distancing":
                shifts["safety_precision"] = 0.2
                shifts["defense_intensity"] = max(shifts.get("defense_intensity", 0), 0.4)

        # ── 内心独白分析 ──
        inner = psych.inner_monologue
        if inner:
            # 被触动 → 自我更新开放
            touch_words = ["触动", "打动", "感动", "温暖", "被看到", "被理解",
                          "他在乎", "他记得", "他注意到", "原来他", "没想到他"]
            if any(w in inner for w in touch_words):
                shifts["self_update_openness"] = 0.3
                shifts["intimacy"] = 0.15

            # 威胁感知
            threat_words = ["危险", "不安", "不确定", "害怕", "失去", "离开", "抛弃"]
            if any(w in inner for w in threat_words):
                shifts["threat_precision"] = max(shifts.get("threat_precision", 0), 0.6)
                shifts["safety_precision"] = -0.5

            # 性唤起信号
            sexual_words = ["想要", "渴望", "靠近", "触碰", "好看", "吸引", "心跳", "身体"]
            if any(w in inner for w in sexual_words):
                shifts["sexual_activation"] = 0.6
                shifts["passion"] = 0.4

            # 玩心/撒娇
            play_words = ["逗", "闹", "撒娇", "黏", "调皮", "玩笑", "哼哼", "要抱"]
            if any(w in inner for w in play_words):
                shifts["playfulness"] = 0.5

            # 占有欲/嫉妒——誓约的排他性被触发
            jealousy_words = ["别人", "她是谁", "为什么对她", "你对他也", "只对我",
                            "我的", "属于我", "不许", "不准", "吃醋", "在意"]
            if any(w in inner for w in jealousy_words):
                shifts["fear"] = shifts.get("fear", 0) + 0.3    # 失去的恐惧
                shifts["attachment_activation"] = 0.6             # 依恋激活
                shifts["relatedness"] = 0.8                       # 连接渴望飙升
                shifts["playfulness"] = -0.3                      # 吃醋时笑不出来

        # ── 只输出有变化的参数 ──
        filtered = {k: v for k, v in shifts.items() if abs(v) > 0.02}
        self.history.append(ModulationRecord(
            source="fast", shifts=filtered,
            reason=f"emotion={emo.dominant}, intensity={emo.intensity:.1f}",
        ))
        return filtered

    # ═══ Slow Track 调制 (修正 + 基线更新) ═══

    def modulate_slow(
        self,
        psych: PsychologyResult,
        memory_context: str = "",
        fast_shifts: dict[str, float] | None = None,
        self_narrative: str = "",
    ) -> dict[str, float]:
        """Slow Track —— 深度修正 + 基线演化。

        - 确认或修正 Fast 的快速判断
        - 更新 SLOW 参数的 baseline（±0.01 ~ ±0.05）
        - 检测 Fast 可能的误判并修正
        """
        shifts: dict[str, float] = {}

        # ── 1. 修正 Fast 的误判 ──
        if fast_shifts:
            emo = psych.emotion

            # Fast 判为 anger 但 Slow 发现其实是 sadness
            if fast_shifts.get("anger", 0) > 0.5 and emo.dominant == "sadness":
                shifts["anger"] = -fast_shifts["anger"] * 0.8  # 收回愤怒
                shifts["sadness"] = emo.intensity * 1.2  # 强化悲伤
                shifts["playfulness"] = -0.3

            # Fast 判为 threat 但 Slow 确认安全
            if fast_shifts.get("threat_precision", 0) > 0.5 and emo.dominant == "joy":
                shifts["threat_precision"] = -0.5
                shifts["safety_precision"] = 0.5

            # Fast 启动了 sexual_activation 但 Slow 判断不合适
            if fast_shifts.get("sexual_activation", 0) > 0.4:
                df = psych.defense
                if df.intensity > 0.5:
                    # 防御高 → 性唤起可能是防御性的，降低
                    shifts["sexual_activation"] = -0.3

        # ── 2. SLOW 参数 baseline 微调 ──
        slow_deltas = self._compute_baseline_deltas(psych, memory_context, self_narrative)
        for name, delta in slow_deltas.items():
            shifts[name] = delta

        filtered = {k: v for k, v in shifts.items() if abs(v) > 0.005}
        self.history.append(ModulationRecord(
            source="slow", shifts=filtered,
            reason=f"baseline_deltas={len(slow_deltas)}, corrections={len(shifts)-len(slow_deltas)}",
        ))
        return filtered

    def _compute_baseline_deltas(
        self, psych: PsychologyResult, memory_ctx: str, self_narrative: str
    ) -> dict[str, float]:
        """计算 SLOW 参数的 baseline 微调。

        幅度受限于 ±0.03（日常），重大事件可达 ±0.10。
        """
        deltas: dict[str, float] = {}
        emo = psych.emotion
        att = psych.attachment
        app = psych.appraisal

        # intimacy baseline: 正面高频互动 → 缓慢积累
        if emo.pleasure > 0.3 and emo.intensity > 0.4:
            deltas["intimacy"] = 0.01
        if emo.dominant == "trust" and emo.intensity > 0.6:
            deltas["intimacy"] = deltas.get("intimacy", 0) + 0.02

        # commitment baseline: 誓约相关的正面体验
        if emo.dominant == "trust" and att.activation > 0.5:
            deltas["commitment"] = 0.01

        # self_worth baseline
        if emo.pleasure > 0.5 and app.coping_potential > 0.6:
            deltas["self_worth"] = 0.01

        # expressiveness baseline: 安全感积累
        if emo.pleasure > 0.4 and psych.emotion.intensity > 0.3:
            # 安全地表达 → 表达基线缓慢上升
            deltas["expressiveness"] = 0.005

        # sexual_baseline: 亲密 + 正面 + 信任
        if (emo.dominant in ("joy", "trust", "love") and
            emo.intensity > 0.5 and emo.pleasure > 0.3):
            deltas["sexual_baseline"] = 0.01

        # self_update_openness: 被触动 → 更开放
        inner = psych.inner_monologue
        if inner and any(w in inner for w in ["触动", "改变", "原来", "他教会", "因为他"]):
            deltas["self_update_openness"] = 0.02

        # 重大事件检测: 深度连接 → 可以突破 ±0.03 上限
        profound = [
            "我爱你", "永远", "承诺", "嫁", "娶", "一生", "最重要",
            "没有你我", "你是我的", "属于我", "我们需要谈谈",
        ]
        if memory_ctx and any(w in memory_ctx for w in profound):
            for k in deltas:
                deltas[k] *= 3.0  # 重大事件 → 3 倍幅度

        # 硬上限: 日常 ±0.03，重大 ±0.10
        cap = 0.10 if any(w in (memory_ctx or "") for w in profound) else 0.03
        return {k: max(-cap, min(cap, v)) for k, v in deltas.items()}

    # ═══ 应用调制 ═══

    def apply_shifts(self, shifts: dict[str, float], is_baseline: bool = False):
        """将调制应用到参数上。

        activation 参数: 直接设置（允许大跳变）
        baseline 参数: 增量微调（受限于自然速率）
        """
        for name, delta in shifts.items():
            p = self.params.get(name)
            if not p:
                continue

            if is_baseline or p.speed == ChangeSpeed.SLOW:
                # baseline 增量更新
                new_val = p.baseline + delta
                p.set_baseline(new_val)
            else:
                # activation 直接设置（绝对值，非增量）
                if delta >= 0:
                    p.set_activation(delta)
                else:
                    # 负值 → 降低 activation
                    p.set_activation(max(0.0, p.activation + delta))

        # Coherence 检查
        violations = self.params.check_coherence()
        if violations:
            self.params.auto_correct()
            self.history[-1].coherence_violations = violations

    # ═══ 查询 ═══

    def stats(self) -> dict:
        return {
            "total_modulations": len(self.history),
            "fast_count": sum(1 for r in self.history if r.source == "fast"),
            "slow_count": sum(1 for r in self.history if r.source == "slow"),
            "corrections": sum(1 for r in self.history
                             if r.source == "slow" and any(v < 0 for v in r.shifts.values())),
            "coherence_violations": sum(len(r.coherence_violations) for r in self.history),
        }
