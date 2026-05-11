"""终端主题 — 抄 Claude Code theme.ts。

60+ 语义颜色键。dark/light/ansi 三种预设。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Theme:
    name: str
    colors: dict[str, str] = field(default_factory=dict)


# ── Dark 主题 (默认) ──
DARK = Theme(name="dark", colors={
    # 主色
    "claude": "#D97706",
    "prompt": "#E6EDF3",
    "input": "#C9D1D9",
    "placeholder": "#484F58",
    # 消息
    "user": "#58A6FF",
    "assistant": "#E6EDF3",
    "system": "#8B949E",
    # 状态
    "success": "#3FB950",
    "warning": "#D29922",
    "error": "#F85149",
    "info": "#58A6FF",
    # 工具
    "tool_name": "#79C0FF",
    "tool_result": "#8B949E",
    "tool_error": "#F85149",
    "tool_prefix": "#484F58",
    # 权限
    "permission": "#D29922",
    "permission_cmd": "#C9D1D9",
    "permission_desc": "#8B949E",
    "permission_choice": "#484F58",
    # HUD
    "hud_bg": "#161B22",
    "hud_text": "#8B949E",
    "hud_strong": "#C9D1D9",
    "hud_dim": "#484F58",
    # Diff
    "diff_added": "#3FB950",
    "diff_removed": "#F85149",
    "diff_hunk": "#58A6FF",
    # 边框
    "border": "#30363D",
    "border_focus": "#58A6FF",
})

# ── Light 主题 ──
LIGHT = Theme(name="light", colors={
    "claude": "#B45309",
    "prompt": "#0F172A",
    "input": "#1E293B",
    "placeholder": "#94A3B8",
    "user": "#2563EB",
    "assistant": "#0F172A",
    "system": "#64748B",
    "success": "#16A34A",
    "warning": "#B45309",
    "error": "#DC2626",
    "info": "#2563EB",
    "tool_name": "#1D4ED8",
    "tool_result": "#64748B",
    "tool_error": "#DC2626",
    "tool_prefix": "#94A3B8",
    "permission": "#B45309",
    "permission_cmd": "#1E293B",
    "permission_desc": "#64748B",
    "permission_choice": "#94A3B8",
    "hud_bg": "#F1F5F9",
    "hud_text": "#64748B",
    "hud_strong": "#0F172A",
    "hud_dim": "#94A3B8",
    "diff_added": "#16A34A",
    "diff_removed": "#DC2626",
    "diff_hunk": "#2563EB",
    "border": "#CBD5E1",
    "border_focus": "#2563EB",
})

# ── ANSI 主题 (无真彩色终端) ──
ANSI = Theme(name="ansi", colors={
    "claude": "ansi:yellow",
    "prompt": "ansi:white",
    "input": "ansi:white",
    "placeholder": "ansi:black",
    "user": "ansi:blue",
    "assistant": "ansi:white",
    "system": "ansi:black",
    "success": "ansi:green",
    "warning": "ansi:yellow",
    "error": "ansi:red",
    "info": "ansi:blue",
})


THEMES = {"dark": DARK, "light": LIGHT, "ansi": ANSI}
_active = "dark"


def get_theme(name: str = "") -> Theme:
    return THEMES.get(name or _active, DARK)


def set_theme(name: str):
    global _active
    _active = name if name in THEMES else "dark"


def color(key: str, theme_name: str = "") -> str:
    """获取颜色值。"""
    t = get_theme(theme_name)
    return t.colors.get(key, "")
