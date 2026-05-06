"""PerceptionStream — TOCA 连续感知流输入管道。

将外部输入（对话、观察、内部感受）转化为带时间戳的感知事件流。
每个管道实例从流中切出自己时间窗内的感知片段。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal


Modality = Literal["visual", "auditory", "internal", "somatic", "text", "dialogue"]


@dataclass
class Perception:
    """单条感知事件"""
    t: float                     # 时间戳
    modality: Modality           # 感知模态
    content: str                 # 内容描述
    intensity: float = 0.5       # 主观强度 (0-1)
    source: str = ""             # 来源 (说话者/对象)

    def to_dict(self) -> dict:
        return {
            "t": self.t, "modality": self.modality,
            "content": self.content, "intensity": self.intensity,
            "source": self.source,
        }


class PerceptionStream:
    """连续感知流管理器。

    用法:
        ps = PerceptionStream()
        ps.feed_visual("手机屏幕亮了", intensity=0.3)
        ps.feed_internal("他在想什么？", intensity=0.6)
        window = ps.get_window(duration=5.0)  # 最近5秒的感知
    """

    def __init__(self, max_window: float = 60.0):
        self._events: list[Perception] = []
        self.max_window = max_window

    def feed(self, modality: Modality, content: str, intensity: float = 0.5,
             source: str = ""):
        """输入一条感知。"""
        self._events.append(Perception(
            t=time.time(), modality=modality, content=content,
            intensity=intensity, source=source,
        ))
        self._trim()

    def feed_visual(self, content: str, intensity: float = 0.3, source: str = ""):
        self.feed("visual", content, intensity, source)

    def feed_auditory(self, content: str, intensity: float = 0.5, source: str = ""):
        self.feed("auditory", content, intensity, source)

    def feed_internal(self, content: str, intensity: float = 0.5):
        self.feed("internal", content, intensity, "")

    def feed_somatic(self, content: str, intensity: float = 0.5):
        self.feed("somatic", content, intensity, "")

    def feed_dialogue(self, content: str, source: str, intensity: float = 0.5):
        """一段对话。source 是说话者。"""
        self.feed("dialogue", content, intensity, source)

    def get_window(self, duration: float = 10.0) -> list[dict]:
        """获取最近 duration 秒的感知事件。"""
        cutoff = time.time() - duration
        return [e.to_dict() for e in self._events if e.t >= cutoff]

    def get_since(self, since_t: float) -> list[dict]:
        """获取自某个时间戳以来的所有感知。"""
        return [e.to_dict() for e in self._events if e.t >= since_t]

    def get_recent_text(self, duration: float = 10.0) -> str:
        """获取最近 N 秒感知的文本摘要（用于 prompt）。"""
        window = self.get_window(duration)
        if not window:
            return "(无感知输入)"
        lines = []
        for e in window:
            src = f"[{e['source']}] " if e['source'] else ""
            lines.append(f"t={e['t']:.0f} {e['modality']}: {src}{e['content']}")
        return "\n".join(lines)

    def _trim(self):
        """淘汰超出窗口的旧事件。"""
        cutoff = time.time() - self.max_window
        self._events = [e for e in self._events if e.t >= cutoff]

    def __len__(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()

    def to_dict(self) -> list[dict]:
        return [e.to_dict() for e in self._events]
