"""终端 REPL — 直接抄 nanobot cli/commands.py 交互模式。"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from contextlib import suppress
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import prompt as pt_prompt
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.application import run_in_terminal

from .stream import StreamRenderer, _make_console


def _render_to_ansi(render_fn) -> str:
    """Render Rich output to ANSI for prompt_toolkit safe printing."""
    console = _make_console()
    ansi_console = Console(
        force_terminal=sys.stdout.isatty(),
        color_system=console.color_system or "standard",
        width=console.width,
    )
    with ansi_console.capture() as capture:
        render_fn(ansi_console)
    return capture.get()


async def _print_tool_line(text: str):
    """打印工具进度——通过 run_in_terminal 安全写入。"""
    def _write():
        ansi = _render_to_ansi(lambda c: c.print(f"  [dim]┊ {text}[/dim]"))
        print_formatted_text(ANSI(ansi), end="")
    await run_in_terminal(_write)


async def _print_response(text: str, bot_name: str):
    """打印最终回复——通过 run_in_terminal。"""
    def _write():
        ansi = _render_to_ansi(lambda c: (
            c.print(),
            c.print(f"[cyan]{bot_name}[/cyan]"),
            c.print(Markdown(text) if text else Text("")),
            c.print(),
        ))
        print_formatted_text(ANSI(ansi), end="")
    await run_in_terminal(_write)


class REPL:
    """交互式 REPL — 抄 nanobot run_interactive()。"""

    def __init__(self, name: str = "assistant",
                 get_input: callable = None,
                 on_submit: callable = None):
        self.name = name
        self._get_input = get_input
        self._on_submit = on_submit
        self._running = False

    async def run(self):
        """主 REPL 循环。"""
        console = _make_console()
        console.print(f"\n  {self.name}")
        console.print("  /help /quit /stats\n")

        # prompt_toolkit session with history
        hist_file = os.path.expanduser("~/.character_mind_history")
        os.makedirs(os.path.dirname(hist_file), exist_ok=True)
        session = PromptSession(history=FileHistory(hist_file))

        self._running = True
        while self._running:
            try:
                user_input = await session.prompt_async("> ")
                user_input = user_input.strip()
                if not user_input:
                    continue
            except (EOFError, KeyboardInterrupt):
                console.print("\nGoodbye!")
                break

            # command dispatch
            if user_input.startswith("/"):
                result = self._handle_command(user_input)
                if result == "quit":
                    break
                if result:
                    def _w():
                        ansi = _render_to_ansi(lambda c: c.print(f"  {result}"))
                        print_formatted_text(ANSI(ansi), end="")
                    await run_in_terminal(_w)
                continue

            # submit to agent
            if self._on_submit:
                await self._on_submit(user_input)

    def stop(self):
        self._running = False

    def _handle_command(self, text: str) -> str:
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0]
        if cmd in ("quit", "q", "exit"):
            self._running = False
            return "quit"
        # commands handled by _on_submit caller via command_registry
        return ""
