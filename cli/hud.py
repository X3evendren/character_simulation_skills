"""HUD — 工作状态栏。抄 Claude Code 状态栏。"""
from __future__ import annotations


class ConsoleHUD:
    """简单状态栏——每轮结束后打印一行状态到 stdout。"""

    def __init__(self):
        self._last = {}

    def start(self):
        pass

    def stop(self):
        pass

    def update(self, **kwargs):
        self._last = kwargs

    def show(self):
        """打印当前状态。"""
        d = self._last
        parts = []
        if d.get("tick"):
            parts.append(f"tick:{d['tick']}")
        tok = d.get("tokens", 0)
        if tok:
            parts.append(f"tok:{tok}")
        tools = d.get("tools_used", 0)
        if tools:
            parts.append(f"tools:{tools}")
        elapsed = d.get("elapsed", 0)
        if elapsed:
            parts.append(f"{elapsed:.1f}s")

        if parts:
            print(f"  [{', '.join(parts)}]")
