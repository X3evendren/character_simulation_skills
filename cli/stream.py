"""Stream renderer — 抄 nanobot cli/stream.py 模式。"""
from __future__ import annotations

import sys
import time
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text


class StreamRenderer:
    """Rich Live streaming, auto_refresh=False 避免闪烁。

    抄 nanobot StreamRenderer 的核心模式:
    spinner → first visible delta → Live renders → on_end stops
    """

    def __init__(self, bot_name: str = "assistant"):
        self._bot_name = bot_name
        self._buf = ""
        self._live: Live | None = None
        self._t = 0.0
        self._console = Console(file=sys.stdout, force_terminal=sys.stdout.isatty())
        self._spinner = None

    def _start_spinner(self):
        if sys.stdout.isatty():
            self._spinner = self._console.status(f"[dim]{self._bot_name} 思考中...[/dim]", spinner="dots")
            self._spinner.start()

    def _stop_spinner(self):
        if self._spinner:
            self._spinner.stop()
            self._spinner = None

    async def on_delta(self, delta: str):
        self._buf += delta
        if self._live is None:
            if not self._buf.strip():
                return
            self._stop_spinner()
            self._live = Live(self._render(), console=self._console, auto_refresh=False)
            self._live.start()
        now = time.monotonic()
        if (now - self._t) > 0.1:
            self._live.update(self._render())
            self._live.refresh()
            self._t = now

    async def on_end(self):
        if self._live:
            self._live.update(self._render())
            self._live.refresh()
            self._live.stop()
            self._live = None
        self._stop_spinner()

    def _render(self):
        return Markdown(self._buf) if self._buf else Text(self._buf or "")

    def print_tool(self, icon: str, name: str, duration: float, result_preview: str = ""):
        """工具执行反馈 — 抄 Hermes display.py 的 get_cute_tool_message。"""
        sec = f"{duration:.1f}s" if duration >= 0.01 else ""
        line = f"  {icon} {name} {sec}"
        if result_preview:
            line += f" → {result_preview[:80]}"
        self._console.print(f"[dim]{line}[/dim]")

    def print_error(self, msg: str):
        self._console.print(f"[red]  ✗ {msg}[/red]")

    def print_info(self, msg: str):
        self._console.print(f"[dim]  {msg}[/dim]")
