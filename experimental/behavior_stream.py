"""BehaviorStream — TOCA 连续行为流输出管道。

角色产生的所有行为（话语、动作、表情、沉默）都记录在行为流中。
其他角色可以读取此流作为感知输入——这是多角色连续对话的基础。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

BehaviorType = Literal["speech", "action", "micro_expression", "silence", "internal"]


@dataclass
class Behavior:
    """单条行为记录"""
    t: float
    type: BehaviorType
    content: str
    confidence: float = 0.8
    target: str = ""  # 对话对象

    def to_dict(self) -> dict:
        return {
            "t": self.t, "type": self.type, "content": self.content,
            "confidence": self.confidence, "target": self.target,
        }


class BehaviorStream:
    """角色行为流。记录角色产出的所有行为。"""

    def __init__(self, character_name: str = ""):
        self.name = character_name
        self._behaviors: list[Behavior] = []

    def emit(self, btype: BehaviorType, content: str, confidence: float = 0.8,
             target: str = ""):
        """记录一条行为。"""
        self._behaviors.append(Behavior(
            t=time.time(), type=btype, content=content,
            confidence=confidence, target=target,
        ))

    def get_recent(self, duration: float = 30.0) -> list[dict]:
        """获取最近 N 秒的行为。"""
        cutoff = time.time() - duration
        return [b.to_dict() for b in self._behaviors if b.t >= cutoff]

    def get_last_speech(self) -> dict | None:
        """获取最近一次 speech 类型的行为。"""
        for b in reversed(self._behaviors):
            if b.type == "speech" and b.content:
                return b.to_dict()
        return None

    def get_since(self, since_t: float) -> list[dict]:
        """获取自某个时间戳以来的所有行为。"""
        return [b.to_dict() for b in self._behaviors if b.t >= since_t]

    def as_perceptions(self, source_name: str = "") -> list[dict]:
        """将行为转换为感知流格式，供其他角色读取。"""
        perps = []
        for b in self._behaviors:
            modality_map = {
                "speech": "dialogue",
                "action": "visual",
                "micro_expression": "visual",
                "silence": "visual",
                "internal": "internal",
            }
            perps.append({
                "t": b.t,
                "modality": modality_map.get(b.type, "visual"),
                "content": b.content,
                "intensity": b.confidence,
                "source": source_name or self.name,
            })
        return perps

    def __len__(self) -> int:
        return len(self._behaviors)

    def clear(self):
        self._behaviors.clear()

    def to_dict(self) -> list[dict]:
        return [b.to_dict() for b in self._behaviors]
