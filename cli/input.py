"""终端输入 — 纯 input() + 手动历史文件。

不用 prompt_toolkit——它与流式输出冲突，会吞掉 print 和 on_delta。
"""
from __future__ import annotations

import os
import atexit


_HIST_FILE = os.path.expanduser("~/.character_mind_history")
_history: list[str] = []


def _load_history():
    global _history
    try:
        with open(_HIST_FILE, "r", encoding="utf-8") as f:
            _history = [line.rstrip("\n") for line in f if line.strip()]
    except FileNotFoundError:
        pass


def _save_history():
    try:
        os.makedirs(os.path.dirname(_HIST_FILE), exist_ok=True)
        with open(_HIST_FILE, "w", encoding="utf-8") as f:
            for line in _history[-500:]:
                f.write(line + "\n")
    except Exception:
        pass


_load_history()
atexit.register(_save_history)


def get_input(prompt: str = "> ") -> str:
    """读取一行输入。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""

def add_history(line: str):
    """添加一行到历史。"""
    if line and (not _history or _history[-1] != line):
        _history.append(line)
