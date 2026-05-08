"""Feedback Loop — 现实世界反馈闭环。

外部世界 → WorldAdapter.feedback(action, result) → 模式提取 → 知识固化 → 自动成长日记。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class FeedbackPattern:
    """从重复反馈中提取的模式。"""
    trigger: str           # 触发条件 (角色做了什么)
    response: str          # 世界回应了什么
    valence: float         # 平均效价
    count: int = 0         # 出现次数
    confidence: float = 0.0 # 置信度
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_rule(self) -> dict:
        """转换为可用过程记忆的规则。"""
        return {
            "trigger": self.trigger,
            "prediction": self.response,
            "defense": "learned_adaptation",
            "response_style": self._suggest_adaptation(),
            "weight": min(1.0, self.confidence),
        }

    def _suggest_adaptation(self) -> str:
        if self.valence < -0.3:
            return "下次避免用同样的方式表达"
        elif self.valence > 0.3:
            return "可以继续用这个方式表达"
        return "效果不确定, 需要更多尝试"


@dataclass
class FeedbackLoop:
    """管理现实世界反馈的收集、模式提取和知识固化。"""

    patterns: dict[str, FeedbackPattern] = field(default_factory=dict)
    growth_diary_entries: list[dict] = field(default_factory=list)
    min_occurrences: int = 3  # 最少出现次数才提取为模式
    _feedback_buffer: list[dict] = field(default_factory=list)

    def record_feedback(self, action: dict, result: str, valence: float):
        """记录一条反馈。"""
        self._feedback_buffer.append({
            "t": time.time(),
            "action_content": action.get("content", ""),
            "action_type": action.get("type", "speech"),
            "result": result,
            "valence": valence,
        })
        if len(self._feedback_buffer) > 50:
            self._feedback_buffer = self._feedback_buffer[-50:]

    def extract_patterns(self) -> list[dict]:
        """从反馈缓冲区提取重复模式。"""
        if len(self._feedback_buffer) < self.min_occurrences:
            return []

        # 按 action_content 分组
        groups: dict[str, list[dict]] = {}
        for fb in self._feedback_buffer:
            key = fb["action_content"][:80]  # 用内容前80字做key
            groups.setdefault(key, []).append(fb)

        extracted = []
        for key, items in groups.items():
            if len(items) < self.min_occurrences:
                continue
            avg_valence = sum(it["valence"] for it in items) / len(items)
            result_summary = items[-1]["result"][:100] if items[-1].get("result") else ""

            pattern = FeedbackPattern(
                trigger=key,
                response=result_summary,
                valence=avg_valence,
                count=len(items),
                confidence=min(1.0, len(items) / 10),
                first_seen=items[0]["t"],
                last_seen=items[-1]["t"],
            )
            self.patterns[key] = pattern
            extracted.append(pattern.to_rule())

        return extracted

    def solidify_knowledge(self, memory_metabolism) -> int:
        """将高置信度模式固化到 fact_store / Core Memory。"""
        solidified = 0
        for key, pattern in self.patterns.items():
            if pattern.confidence >= 0.7 and pattern.count >= 5:
                # 固化为 fact
                if memory_metabolism is not None:
                    memory_metabolism.ingest(
                        f"[习得行为模式] 当我说'{pattern.trigger}'时, "
                        f"对方通常是'{pattern.response}'(效价:{pattern.valence:.1f})",
                        {"trust": pattern.confidence},
                        significance=0.7,
                        tags=["learned_pattern", "feedback"],
                    )
                    solidified += 1
        return solidified

    def generate_growth_diary(self, memory_metabolism) -> str | None:
        """生成成长日记条目。"""
        rules = self.extract_patterns()
        solidified = self.solidify_knowledge(memory_metabolism)
        if solidified == 0:
            return None

        entry = {
            "t": time.time(),
            "what_i_learned": f"从最近的互动中学到了{solidified}个行为模式",
            "how_i_changed": f"将这些模式固化为长期知识, 未来类似情境中将自动应用",
        }
        self.growth_diary_entries.append(entry)
        if memory_metabolism is not None:
            memory_metabolism.growth_log.append(entry)

        return f"[成长日记] {entry['what_i_learned']}。{entry['how_i_changed']}"

    def to_dict(self) -> dict:
        return {
            "patterns": {k: {"trigger": v.trigger, "valence": v.valence,
                              "count": v.count, "confidence": v.confidence}
                         for k, v in self.patterns.items()},
            "growth_diary": self.growth_diary_entries[-10:],
        }
