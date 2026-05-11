"""终端显示 — 抄 Claude Code StatusLine + Spinner 模式。

Rich Live 底部状态栏 + 旋转动画。
"""
from __future__ import annotations

import sys
import time
import threading
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout


class TerminalUI:
    """终端 UI — Rich Live 底部状态栏。

    抄 Claude Code StatusLine.tsx 的数据驱动模式。
    """

    def __init__(self):
        self._console = Console(file=sys.stderr, force_terminal=sys.stderr.isatty())
        self._live: Live | None = None
        self._visible = sys.stderr.isatty()
        self._data = {
            "model": "", "tick": 0, "tokens": 0, "tools": 0,
            "elapsed": 0, "status": "",
        }
        self._spinner_frame = 0

    def start(self):
        if not self._visible:
            return
        self._live = Live(self._render(), console=self._console,
                         auto_refresh=False, transient=True)
        self._live.start()

    def stop(self):
        if self._live:
            self._live.stop()
            self._live = None

    def update(self, **kwargs):
        self._data.update(kwargs)
        if self._live:
            self._live.update(self._render())
            self._live.refresh()

    def thinking(self, msg: str = "思考中"):
        """显示等待状态。"""
        self.update(status=msg)

    def done(self):
        """清除状态。"""
        self.update(status="", elapsed=0)

    def _render(self):
        d = self._data
        layout = Layout()

        # 第一行: 状态
        status_text = Text()
        if d.get("status"):
            status_text.append(d["status"], style="yellow")
            status_text.append(" ", "")
        status_text.append(f"tick:{d.get('tick',0)}", style="dim")
        tok = d.get("tokens", 0)
        if tok:
            status_text.append(f" tok:{tok}", style="dim")
        tools = d.get("tools", 0)
        if tools:
            status_text.append(f" tools:{tools}", style="yellow")
        elapsed = d.get("elapsed", 0)
        if elapsed:
            status_text.append(f" {elapsed:.1f}s", style="dim")

        layout.split_column(Layout(status_text, size=1))
        return Panel(layout, border_style="dim cyan", padding=(0, 1))
