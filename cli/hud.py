"""HUD — 工作状态栏。只显示工作相关: FSM、tick、token、工具。"""
from __future__ import annotations

import sys


class ConsoleHUD:
    """终端底部状态栏——纯工作信息，不暴露情感参数。"""

    def __init__(self):
        self._visible = sys.stderr.isatty()
        self._last_line = ""

    def start(self):
        pass

    def stop(self):
        if self._last_line:
            sys.stderr.write("\r" + " " * len(self._last_line) + "\r")
            sys.stderr.flush()

    def update(self, **kwargs):
        if not self._visible:
            return
        d = kwargs
        parts = []
        if d.get("fsm"): parts.append(f"[{d['fsm']}]")
        if d.get("tick"): parts.append(f"tick:{d['tick']}")
        tok = d.get("tokens", 0)
        if tok: parts.append(f"tok:{tok}")
        tools = d.get("tools_used", 0)
        if tools: parts.append(f"tools:{tools}")
        elapsed = d.get("elapsed", 0)
        if elapsed: parts.append(f"{elapsed:.1f}s")

        line = " ".join(parts)
        sys.stderr.write("\r" + " " * len(self._last_line) + "\r")
        if line:
            sys.stderr.write(line)
        sys.stderr.flush()
        self._last_line = line
