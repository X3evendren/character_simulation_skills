"""HUD 状态栏 — 终端底部实时状态显示。

抄 Claude Code REPL 的状态栏 + Hermes 的皮肤系统。
使用 Rich Live 实时更新，不干扰主对话流。
"""
from __future__ import annotations

import sys
import time
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.table import Table


class HUD:
    """终端状态栏——显示关键运行时信息。

    布局:
      左侧: FSM状态 | 饱和度 | 誓约
      右侧: Tick | Token | 工具调用
      底部: 情感参数条
    """

    def __init__(self, console: Console | None = None):
        self._console = console or Console(file=sys.stderr, force_terminal=sys.stderr.isatty())
        self._live: Live | None = None
        self._visible = sys.stderr.isatty()
        self._data: dict = {}

    def start(self):
        if not self._visible:
            return
        self._live = Live(self._render(), console=self._console, auto_refresh=False,
                         transient=True, vertical_overflow="visible")
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

    def _render(self):
        d = self._data
        layout = Layout()
        layout.split_column(
            Layout(self._bar(d), size=1),
            Layout(self._params(d), size=1),
        )
        return Panel(layout, border_style="dim cyan", padding=(0, 1))

    def _bar(self, d: dict) -> Text:
        parts = []
        # 左侧
        fsm = d.get("fsm", "?")
        sat = d.get("sat", 0)
        oath = d.get("oath", "?")
        parts.append((f"[FSM:{fsm}]", "cyan"))
        parts.append((f" [sat:{sat:.1f}]", "yellow" if sat < 0.3 else "green"))
        parts.append((f" [誓约:{oath}]", "magenta"))

        # 右侧
        tick = d.get("tick", 0)
        tok = d.get("tokens", 0)
        tools = d.get("tools_used", 0)
        parts.append((" " * 4, ""))
        parts.append((f"[tick:{tick}]", "dim"))
        parts.append((f" [tok:{tok}]", "dim"))
        if tools:
            parts.append((f" [tools:{tools}]", "yellow"))

        text = Text()
        for content, style in parts:
            text.append(content, style=style)
        return text

    def _params(self, d: dict) -> Text:
        params = d.get("params", {})
        if not params:
            return Text("")

        items = [
            ("愉悦", params.get("pleasure", 0), -1, 1),
            ("唤醒", params.get("arousal", 0), 0, 1),
            ("安全", params.get("safety", 0.5), 0, 1),
            ("威胁", params.get("threat", 0.5), 0, 1),
            ("表达", params.get("expressiveness", 0.3), 0, 1),
            ("玩心", params.get("playfulness", 0.1), 0, 1),
            ("性", params.get("sexual", 0), 0, 1),
        ]

        text = Text()
        for name, val, vmin, vmax in items:
            # 颜色映射
            if name in ("威胁",) and val > 0.5:
                color = "red"
            elif name in ("安全", "愉悦") and val > 0.5:
                color = "green"
            elif name in ("性",) and val > 0.4:
                color = "magenta"
            elif name in ("玩心",) and val > 0.5:
                color = "yellow"
            else:
                color = "dim"

            text.append(f" {name}", style="dim")
            text.append(f"{val:+.1f}", style=color)

        return text


class ConsoleHUD:
    """简化版 HUD——纯 print 到 stderr，不需要 Rich Live。

    用于不支持 TTY 的环境。
    """

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
        fsm = d.get("fsm", "?")
        sat = d.get("sat", 0)
        oath = d.get("oath", "?")
        tick = d.get("tick", 0)
        params = d.get("params", {})

        line = (f"\r[FSM:{fsm}] [sat:{sat:.1f}] [誓约:{oath}] "
                f"[tick:{tick}] "
                f"愉悦{params.get('pleasure',0):+.1f} "
                f"安全{params.get('safety',0.5):.1f} "
                f"威胁{params.get('threat',0.5):.1f}")

        sys.stderr.write("\r" + " " * len(self._last_line) + "\r")
        sys.stderr.write(line)
        sys.stderr.flush()
        self._last_line = line
