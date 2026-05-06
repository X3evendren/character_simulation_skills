"""Thalamic Gate — 丘脑门控感知过滤器。

不是所有感知都触发全量管道分析。低显著性感知累积在缓冲区，
累积效应超过阈值时才"打开闸门"进入完整管道。

零额外 Token——纯数学评分。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class GateState:
    """门控运行时状态"""
    buffer: list[dict] = field(default_factory=list)       # 累积的感知
    accumulated_intensity: float = 0.0
    accumulated_novelty: float = 0.0
    last_full_process: float = 0.0
    suppressed_count: int = 0
    passed_count: int = 0


class ThalamicGate:
    """感知门控过滤器。

    用法:
        gate = ThalamicGate()
        result = gate.evaluate(perception)
        if result.should_process:
            # 运行完整管道
            perceptions = gate.flush()
        else:
            # 感知被缓冲，累积等待
    """

    def __init__(self, threshold: float = 0.4, max_buffer_age: float = 8.0):
        self.threshold = threshold           # 累积强度触发阈值
        self.max_buffer_age = max_buffer_age  # 最大缓冲时间(秒)
        self.state = GateState()

    def evaluate(self, perception: dict) -> dict:
        """评估一条感知是否应该触发全量处理。
        返回 {should_process, score, reason}。"""
        intensity = perception.get("intensity", 0.3)
        modality = perception.get("modality", "internal")
        content = perception.get("content", "")

        # 评分维度
        emotional_weight = self._emotional_weight(content)
        novelty_score = self._novelty_score(content)
        urgency = 1.0 if modality == "dialogue" else 0.3  # 对话总是紧急的

        score = (intensity * 0.35 + emotional_weight * 0.25 +
                 novelty_score * 0.25 + urgency * 0.15)

        # 累积到缓冲区
        self.state.buffer.append(perception)
        self.state.accumulated_intensity += intensity
        self.state.accumulated_novelty += novelty_score

        # 检查触发条件
        buffer_age = time.time() - (self.state.buffer[0].get("t", time.time())
                                     if self.state.buffer else time.time())

        should_process = (
            score > 0.5 or                                          # 单条高显著
            self.state.accumulated_intensity > self.threshold * 2 or  # 累积强度够
            buffer_age > self.max_buffer_age or                       # 缓冲太久
            modality == "dialogue"                                     # 对话必过
        )

        if should_process:
            self.state.passed_count += 1
        else:
            self.state.suppressed_count += 1

        return {
            "should_process": should_process,
            "score": score,
            "buffered": len(self.state.buffer),
            "accumulated": self.state.accumulated_intensity,
        }

    def flush(self) -> list[dict]:
        """取出所有缓冲的感知并清空缓冲区。"""
        buffered = list(self.state.buffer)
        self.state.buffer.clear()
        self.state.accumulated_intensity = 0.0
        self.state.accumulated_novelty = 0.0
        self.state.last_full_process = time.time()
        return buffered

    def _emotional_weight(self, content: str) -> float:
        """基于关键词的快速情绪权重。"""
        high_emotion = ["害怕", "生气", "愤怒", "绝望", "恐惧", "恨",
                        "崩溃", "受不了", "救命", "死了"]
        medium_emotion = ["难过", "担心", "焦虑", "不安", "紧张",
                          "失望", "委屈", "烦"]
        content_lower = content.lower()
        for w in high_emotion:
            if w in content_lower:
                return 0.9
        for w in medium_emotion:
            if w in content_lower:
                return 0.5
        return 0.15

    def _novelty_score(self, content: str) -> float:
        """基于最近缓冲内容的简单新颖性检测。"""
        if len(self.state.buffer) < 2:
            return 0.5  # 刚开始，默认新颖
        recent_texts = " ".join(
            b.get("content", "") for b in self.state.buffer[-3:]
        )
        # 简单重复检测
        if content in recent_texts:
            return 0.0
        # 共享词汇比例
        words = set(content)
        recent_words = set(recent_texts)
        if words:
            overlap = len(words & recent_words) / len(words)
            novelty = 1.0 - overlap
            return max(0.1, novelty)
        return 0.5

    def stats(self) -> dict:
        return {
            "suppressed": self.state.suppressed_count,
            "passed": self.state.passed_count,
            "filter_ratio": (
                self.state.suppressed_count /
                max(self.state.suppressed_count + self.state.passed_count, 1)
            ),
            "buffer_size": len(self.state.buffer),
        }
