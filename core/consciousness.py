"""Consciousness Layer — 让连续状态流更接近真实意识。

三个神经科学启发的机制:
1. 选择性广播 (GWT) — 不是所有心理内容都"进入意识"
2. 元认知自监控 (HOT) — 系统知道自己正在感受什么
3. 预测加工 — 惊讶驱动注意力，预测误差越大越显著

核心原则: 预测和评分纯数学，零额外 Token。自感知可选 LLM。
"""
from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsciousnessState:
    """意识层的运行时状态"""
    predictions: dict = field(default_factory=dict)   # 上帧预测值
    errors: dict = field(default_factory=dict)        # 预测误差
    salience: dict = field(default_factory=dict)      # 各字段显著性
    self_perception: str = ""                          # 当前自我感知
    last_self_perceive: float = 0.0                    # 上次自感知时间
    broadcast_count: int = 0                           # 广播次数
    suppressed_count: int = 0                          # 抑制次数


class ConsciousnessLayer:
    """意识层 — GWT + HOT + 预测加工的统一实现。"""

    def __init__(self, blackboard):
        self.bb = blackboard
        self.state = ConsciousnessState()
        self.salience_threshold = 0.3          # 显著性阈值
        self.self_perceive_interval = 30.0       # 自感知间隔(秒)
        self.alpha = 0.3                         # 预测平滑系数

    # ═══ 1. 预测加工 (Predictive Processing) ═══

    def predict_next(self) -> dict:
        """基于当前 Blackboard 状态预测下一帧。
        线性外推: next = current + alpha * (current - last)。
        纯数学，零 Token。"""
        current = self.bb.read(["pad", "dominant_emotion"])
        predictions = {}

        pad = current.get("pad", {})
        if pad and "pleasure" in pad:
            last_pad = self.state.predictions.get("pad", {})
            predictions["pad"] = {
                "pleasure": self._extrapolate(pad.get("pleasure", 0),
                                              last_pad.get("pleasure", pad.get("pleasure", 0))),
                "arousal": self._extrapolate(pad.get("arousal", 0.5),
                                             last_pad.get("arousal", pad.get("arousal", 0.5))),
            }

        self.state.predictions = predictions
        return predictions

    def _extrapolate(self, current: float, last: float) -> float:
        """线性外推: estimate = current + alpha * delta。"""
        delta = current - last
        val = current + self.alpha * delta
        return max(-1.0, min(1.0, val))

    def compute_prediction_error(self) -> dict:
        """计算当前实际值 vs 预测值的误差。返回各字段的误差大小(0-1)。"""
        actual = self.bb.read(["pad"])
        errors = {}

        pad = actual.get("pad", {})
        pred_pad = self.state.predictions.get("pad", {})
        if pad and pred_pad:
            p_err = abs(pad.get("pleasure", 0) - pred_pad.get("pleasure", 0))
            a_err = abs(pad.get("arousal", 0.5) - pred_pad.get("arousal", 0.5))
            errors["pad_pleasure"] = min(1.0, p_err)
            errors["pad_arousal"] = min(1.0, a_err)

        self.state.errors = errors
        return errors

    # ═══ 2. 选择性广播 (GWT) ═══

    def score_salience(self, changes: dict | None = None) -> dict:
        """计算每个心理内容的显著性分数(0-1)。

        显著性 = 变化幅度(0.4) + 情感唤醒(0.3) + 预测误差(0.2) + 新颖性(0.1)
        """
        current = self.bb.read(["pad", "dominant_emotion", "ptsd_triggered",
                                 "active_defense", "pending_response"])
        errors = self.state.errors
        salience = {}

        pad = current.get("pad", {})
        arousal = pad.get("arousal", 0.5)

        # 情绪变化显著性
        emotion_sal = 0.0
        if "dominant_emotion" in current and current["dominant_emotion"]:
            emotion_sal = arousal * 0.6  # 高唤醒情绪更显著
        # 预测误差贡献
        emotion_sal += (errors.get("pad_pleasure", 0) + errors.get("pad_arousal", 0)) * 0.2
        salience["emotion"] = min(1.0, emotion_sal)

        # 威胁显著性
        if current.get("ptsd_triggered"):
            salience["threat"] = 0.85
        else:
            salience["threat"] = 0.15

        # 防御机制显著性（防御激活通常不被意识到，但强烈时会）
        defense = current.get("active_defense", {})
        if defense and isinstance(defense, dict) and defense.get("intensity", 0) > 0.6:
            salience["defense"] = 0.5
        else:
            salience["defense"] = 0.1

        # 回应显著性（有内容要表达时）
        resp = current.get("pending_response", {})
        if resp and resp.get("text", "").strip():
            salience["response"] = 0.7
        else:
            salience["response"] = 0.0

        self.state.salience = salience
        return salience

    def should_broadcast(self, field: str) -> bool:
        """该心理内容是否应该被广播到全局空间（进入意识/L5）？"""
        return self.state.salience.get(field, 0.0) >= self.salience_threshold

    def filter_broadcast(self) -> dict[str, bool]:
        """对所有字段做广播决策。返回 {field: should_broadcast}。"""
        self.score_salience()
        decisions = {}
        for field in ["emotion", "threat", "defense", "response"]:
            should = self.should_broadcast(field)
            decisions[field] = should
            if should:
                self.state.broadcast_count += 1
            else:
                self.state.suppressed_count += 1
        return decisions

    # ═══ 3. 元认知自监控 (HOT) ═══

    def self_perceive(self, force: bool = False) -> str:
        """生成当前心理状态的自我感知描述。

        默认使用模板生成（零Token）。在特定条件下（force=True 或达到间隔）
        可以调用 LLM 生成更丰富的自我感知。
        """
        now = time.time()
        if not force and now - self.state.last_self_perceive < self.self_perceive_interval:
            return self.state.self_perception

        current = self.bb.read(["dominant_emotion", "pad", "active_defense",
                                 "active_biases", "ptsd_triggered"])

        emotion = current.get("dominant_emotion", "neutral")
        pad = current.get("pad", {})
        pleasure = pad.get("pleasure", 0)
        arousal = pad.get("arousal", 0.5)
        defense = current.get("active_defense", {})
        triggered = current.get("ptsd_triggered", False)

        # 模板生成自我感知
        parts = []

        # 情绪状态
        if arousal > 0.7:
            intensity = "非常强烈的"
        elif arousal > 0.5:
            intensity = "明显的"
        elif arousal > 0.3:
            intensity = "淡淡的"
        else:
            intensity = "微弱的"

        valence = "正面" if pleasure > 0.15 else ("负面" if pleasure < -0.15 else "中性")
        parts.append(f"我正感受到{intensity}{valence}情绪")

        # 防御机制（通常不被意识察觉，但可以感知到其效果）
        if defense and isinstance(defense, dict):
            dname = defense.get("name", "")
            if dname and defense.get("intensity", 0) > 0.5:
                parts.append(f"我注意到自己在用{dname}来应对")

        # 创伤触发
        if triggered:
            parts.append("我感到一种说不清的紧张，像是旧伤被触碰了")

        # 显著性感知
        high_salience = [k for k, v in self.state.salience.items() if v > 0.6]
        if high_salience:
            parts.append(f"此刻我的注意力被{'、'.join(high_salience)}占据")

        perception = "。".join(parts) + "。"

        self.state.self_perception = perception
        self.state.last_self_perceive = now

        # 写回 Blackboard
        self.bb.write("self_perception", perception)

        return perception

    async def self_perceive_llm(self, provider) -> str:
        """使用 LLM 生成更细腻的自我感知。低频调用(~30s间隔)。"""
        current = self.bb.read(["dominant_emotion", "pad", "active_defense",
                                 "active_biases", "ptsd_triggered", "self_perception"])
        errors = self.state.errors

        prompt = f"""你正在观察自己的心理状态。用第一人称描述你此刻的感受。

情绪: {current.get('dominant_emotion','neutral')}
愉悦度: {current.get('pad',{}).get('pleasure',0):.1f} 唤醒度: {current.get('pad',{}).get('arousal',0.5):.1f}
预测误差: {errors}
防御: {current.get('active_defense',{}).get('name','无')}

用1-2句话描述你的内心状态。不要分析，不要解释为什么——只是感受。"""

        try:
            result = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=100,
            )
            content = result["choices"][0]["message"]["content"]
            perception = content.strip()[:200]
            self.state.self_perception = perception
            self.state.last_self_perceive = time.time()
            self.bb.write("self_perception", perception)
            return perception
        except Exception:
            # LLM 失败时退回模板
            return self.self_perceive(force=True)

    # ═══ 统计 ═══

    def stats(self) -> dict:
        return {
            "broadcast_count": self.state.broadcast_count,
            "suppressed_count": self.state.suppressed_count,
            "broadcast_ratio": (
                self.state.broadcast_count /
                max(self.state.broadcast_count + self.state.suppressed_count, 1)
            ),
            "avg_prediction_error": (
                sum(self.state.errors.values()) / max(len(self.state.errors), 1)
            ),
            "self_perception": self.state.self_perception[:100],
        }
