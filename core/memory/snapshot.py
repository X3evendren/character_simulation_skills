"""冻结快照 — 会话边界优化。

参考 Hermes Agent memory_tool.py (第 123-142 行) 的设计:
- 会话开始时: 从持久化存储生成快照，注入 system prompt
- 会话中途: 写入立即持久化，但快照不变（不破坏前缀缓存）
- 下一轮会话: 新快照包含上轮写入
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .store import MemoryStore, MemoryRecord


@dataclass
class FrozenSnapshot:
    """会话边界记忆快照。

    为 LLM 前缀缓存优化——会话中间快照不变。
    """

    snapshot_text: str = ""
    frozen_at: float = 0.0
    dirty: bool = False          # 会话中途有写入时置 True

    def freeze(self, stores: dict[str, MemoryStore]) -> str:
        """生成当前状态的冻结快照 → 注入 system prompt。

        Args:
            stores: {"working": ..., "stm": ..., "ltm": ..., "core": ...}
        """
        parts = ["【记忆快照】"]

        # Core 图谱: 最重要的实体关系
        core = stores.get("core")
        if core and hasattr(core, "query_subgraph"):
            try:
                subgraph = core.query_subgraph("*", depth=1)
                if subgraph.get("summary"):
                    parts.append(f"核心关系: {subgraph['summary']}")
            except Exception:
                pass

        # LTM: 最近的重大事件
        ltm = stores.get("ltm")
        if ltm:
            import asyncio
            try:
                recent = asyncio.get_event_loop().run_until_complete(
                    ltm.recall("", 5)
                ) if asyncio.get_event_loop().is_running() else []
            except RuntimeError:
                recent = []
            for r in recent:
                parts.append(f"- {r.content[:100]}")

        # STM: 最近对话上下文
        stm = stores.get("stm")
        if stm:
            import asyncio
            try:
                recent = asyncio.get_event_loop().run_until_complete(
                    stm.recall("", 3)
                ) if asyncio.get_event_loop().is_running() else []
            except RuntimeError:
                recent = []
            for r in recent:
                parts.append(f"- {r.content[:100]}")

        self.snapshot_text = "\n".join(parts)
        self.frozen_at = time.time()
        self.dirty = False
        return self.snapshot_text

    def mark_dirty(self):
        """会话中途有写入 → 标记为脏，下轮需要刷新。"""
        self.dirty = True

    def is_stale(self) -> bool:
        """快照是否过期（需要重新冻结）。"""
        return self.dirty or (time.time() - self.frozen_at > 3600)

    def format_for_prompt(self) -> str:
        """格式化为 Prompt 可注入的文本。"""
        if not self.snapshot_text:
            return ""
        return self.snapshot_text
