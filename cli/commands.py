"""斜杠命令系统 — 抄 Claude Code commands.ts。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Command:
    name: str
    aliases: list[str]
    help: str
    handler: Callable  # async def fn(args: str, ctx: dict) -> str | None


class CommandRegistry:
    """命令注册表 — 抄 Claude Code loadAllCommands()。"""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, cmd: Command):
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd

    def find(self, name: str) -> Command | None:
        """按名称或别名查找命令 — 抄 Claude Code findCommand()。"""
        return self._commands.get(name)

    def match(self, text: str) -> tuple[Command | None, str]:
        """匹配命令 — 返回 (命令, 剩余参数)。"""
        if not text.startswith("/"):
            return None, text
        parts = text[1:].split(maxsplit=1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        return self.find(name), args

    def list_all(self) -> list[str]:
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(f"/{cmd.name} — {cmd.help}")
        return sorted(result)


def create_default_registry(params, oath, sat, metrics, skill_lib, hud) -> CommandRegistry:
    """创建默认命令注册表 — 抄 Claude Code COMMANDS()。"""
    r = CommandRegistry()

    r.register(Command("quit", ["q", "exit"], "退出", lambda a, c: "quit"))
    r.register(Command("stats", ["st"], "查看状态", lambda a, c: _cmd_stats(params)))
    r.register(Command("love", [], "查看关系状态", lambda a, c: _cmd_love(oath, sat, metrics)))
    r.register(Command("good", [], "好评反馈", lambda a, c: _cmd_good(oath, metrics)))
    r.register(Command("bad", [], "差评反馈", lambda a, c: _cmd_bad(metrics)))
    r.register(Command("hud", [], "切换HUD", lambda a, c: _cmd_hud(hud)))
    r.register(Command("skills", ["sk"], "列出技能", lambda a, c: str(skill_lib.stats())))
    r.register(Command("help", ["h", "?"], "帮助", lambda a, c: "\n".join(r.list_all())))

    return r


def _cmd_stats(params) -> str:
    snap = params.snapshot()
    return (f"pleasure={snap['pleasure']:.1f} safety={snap['safety_precision']:.1f} "
            f"threat={snap['threat_precision']:.1f} intimacy={snap['intimacy']:.1f} "
            f"express={snap['expressiveness']:.1f} playful={snap['playfulness']:.1f}")

def _cmd_love(oath, sat, metrics) -> str:
    return (f"oath={oath.state.value}({oath.strength:.1f}) "
            f"sat={sat.saturation_level:.2f} mode={sat.mode.value} "
            f"health={metrics.gottman_status} assurance={metrics.assurance:.2f}")

def _cmd_good(oath, metrics) -> str:
    metrics.record_positive(); oath.renew(); return "✓"
def _cmd_bad(metrics) -> str:
    metrics.record_negative(); return "✗"
def _cmd_hud(hud) -> str:
    hud.show(); return ""
