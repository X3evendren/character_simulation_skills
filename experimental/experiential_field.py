"""Experiential Field — 时间意识结构 (Precuneus 整合角色)。

每个"现在"包含三重结构:
- Retention (滞留): 刚刚过去的体验仍在场, 衰减但不消失
- Primal Impression (原初印象): 当前涌入意识的内容 (workspace)
- Protention (前摄): 即将到来的可能性范围, 不是点预测而是敞开感

对应大脑 Precuneus — 将 DMN 三模块 (vmPFC/amPFC/dmPFC) 的并行输出整合
为统一的主观体验。
"""
from __future__ import annotations

import time
import math
import random
from dataclasses import dataclass, field


@dataclass
class RetentionItem:
    """滞留中的单条体验片段。"""
    content: str                     # 体验描述
    weight: float                    # 当前权重 (随时间衰减)
    initial_weight: float            # 初始权重
    timestamp: float                 # 发生时间
    source: str = ""                 # workspace / inner_stream / memory
    emotional_tone: str = "neutral"  # 情感调性

    def decay(self, half_life: float = 5.0):
        """指数衰减: weight *= 2^(-dt/half_life)"""
        dt = time.time() - self.timestamp
        lam = math.log(2) / half_life
        self.weight = self.initial_weight * math.exp(-lam * dt)


@dataclass
class RetentionBuffer:
    """滞留缓冲区 — 刚刚过去的体验衰减在场。

    不是情绪衰减 (PAD 值变化), 而是体验内容本身仍在"回响"。
    """

    items: list[RetentionItem] = field(default_factory=list)
    max_items: int = 10
    half_life: float = 5.0           # 5秒后半衰

    def push(self, content: str, weight: float = 1.0, source: str = "",
             emotional_tone: str = "neutral"):
        item = RetentionItem(
            content=content, weight=weight, initial_weight=weight,
            timestamp=time.time(), source=source, emotional_tone=emotional_tone,
        )
        self.items.append(item)
        self._trim()

    def tick(self):
        """每 tick: 衰减 + 淘汰过低权重项。"""
        for item in self.items:
            item.decay(self.half_life)
        self.items = [it for it in self.items if it.weight > 0.05]
        self._trim()

    def get_active(self, min_weight: float = 0.1) -> list[RetentionItem]:
        """获取仍然活跃的滞留项 (加权重)。"""
        return sorted(
            [it for it in self.items if it.weight >= min_weight],
            key=lambda it: it.weight, reverse=True,
        )

    def format_for_context(self) -> str:
        """格式化为可注入上下文的文本。"""
        active = self.get_active(0.15)[:5]
        if not active:
            return ""
        lines = ["[刚刚过去的还在回响]"]
        for it in active:
            intensity = "强烈" if it.weight > 0.5 else "隐约"
            lines.append(f"- ({intensity}) {it.content[:100]}")
        return "\n".join(lines)

    def _trim(self):
        if len(self.items) > self.max_items * 2:
            self.items.sort(key=lambda it: it.weight, reverse=True)
            self.items = self.items[:self.max_items * 2]


@dataclass
class ProtentionSpread:
    """前摄散布 — 即将到来的可能性范围。

    不是 "下一个值是多少" (预测), 而是 "可能性的敞开范围"。
    基于当前趋势生成 N 个可能未来状态样本, 加入随机扰动。
    """

    current_trend: dict = field(default_factory=dict)  # {field: delta_per_tick}
    spread: float = 0.2                                  # 扰动幅度
    num_samples: int = 5                                 # 采样数
    horizon_ticks: int = 3                               # 向前看几个 tick

    def update_trend(self, current: dict, previous: dict):
        """从当前值和上一个值计算趋势方向。"""
        for key in set(current) | set(previous):
            curr_val = current.get(key, 0)
            prev_val = previous.get(key, 0)
            if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                self.current_trend[key] = curr_val - prev_val

    def sample_futures(self, current: dict) -> list[dict]:
        """生成 N 个可能未来状态样本。"""
        samples = []
        for _ in range(self.num_samples):
            future = dict(current)
            for key, trend in self.current_trend.items():
                if isinstance(future.get(key), (int, float)):
                    # 每个 tick 加上趋势 + 随机扰动
                    base = future[key]
                    for step in range(1, self.horizon_ticks + 1):
                        noise = random.uniform(-self.spread, self.spread) * step
                        future[key] = base + trend * step + noise
            samples.append(future)
        return samples

    def openness_score(self) -> float:
        """前摄的"敞开感"度量 — 趋势越不确定 → 越敞开。"""
        if not self.current_trend:
            return 0.5
        abs_trends = [abs(v) for v in self.current_trend.values()]
        mean_trend = sum(abs_trends) / len(abs_trends)
        # 趋势小 → 世界稳定 → 敞开感低; 趋势大 → 多变 → 敞开感高
        return min(1.0, mean_trend * 2.0)


@dataclass
class ExperientialField:
    """体验场 — 整合滞留/原初印象/前摄的统一时间意识结构。

    对应大脑 Precuneus。
    """

    retention: RetentionBuffer = field(default_factory=RetentionBuffer)
    protention: ProtentionSpread = field(default_factory=ProtentionSpread)
    current_impression: dict = field(default_factory=dict)  # 当前 workspace 内容
    previous_impression: dict = field(default_factory=dict) # 上一 tick 的内容

    def tick(self, workspace: list[dict]):
        """每个 tick 更新体验场。

        1. 将当前 workspace 存入滞留 (旧的印象进入 retention)
        2. 更新前摄趋势
        3. 设置新的原初印象
        """
        # 将上一帧的内容推入滞留
        if self.current_impression:
            content_summary = self._summarize_impression(self.current_impression)
            if content_summary:
                dominant_emo = self.current_impression.get("dominant_emotion", "neutral")
                self.retention.push(
                    content=content_summary,
                    weight=0.8,
                    source="workspace",
                    emotional_tone=dominant_emo,
                )

        # 更新前摄趋势
        self.protention.update_trend(workspace_to_dict(workspace),
                                      workspace_to_dict(self.previous_impression.get("content", {})))

        # 衰减滞留
        self.retention.tick()

        # 设置新的原初印象
        self.previous_impression = dict(self.current_impression)
        self.current_impression = {
            "t": time.time(),
            "content": workspace,
            "dominant_emotion": self._extract_dominant_emotion(workspace),
        }

    def _summarize_impression(self, impression: dict) -> str:
        """从印象中提取文本摘要。"""
        workspace = impression.get("content", [])
        if not workspace:
            return ""
        parts = []
        for item in workspace[:3]:
            kind = item.get("kind", "")
            content = item.get("content", "")
            if content:
                parts.append(f"[{kind}]{content[:80]}")
        return " ".join(parts)

    def _extract_dominant_emotion(self, workspace: list[dict]) -> str:
        for item in workspace:
            if item.get("kind") == "emotion":
                return item.get("content", "neutral")
        return "neutral"

    def get_protention_samples(self) -> list[dict]:
        return self.protention.sample_futures({
            "pleasure": 0.0,  # 从 Blackboard 读取更准确
            "arousal": 0.5,
        })

    def to_dict(self) -> dict:
        return {
            "retention_items": [
                {"content": it.content, "weight": it.weight, "t": it.timestamp}
                for it in self.retention.items
            ],
            "current_impression": self.current_impression,
            "protention_trend": self.protention.current_trend,
        }


def workspace_to_dict(workspace: list[dict]) -> dict:
    """将 workspace 列表转换为可比较的 dict。"""
    result = {}
    for item in workspace:
        kind = item.get("kind", "unknown")
        result[f"{kind}_salience"] = item.get("salience", 0.0)
    return result
