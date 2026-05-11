"""终端输入 — 抄 Claude Code PromptInput + useArrowKeyHistory 模式。

优先用 prompt_toolkit (历史/编辑/vim)，回退 input()。
"""
from __future__ import annotations


async def get_input(prompt: str = "> ") -> str:
    """读取一行输入。支持上下箭头历史。"""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        import os
        hist_file = os.path.expanduser("~/.character_mind_history")
        _session = PromptSession(history=FileHistory(hist_file))
        return (await _session.prompt_async(prompt)).strip()
    except ImportError:
        import asyncio
        return (await asyncio.get_event_loop().run_in_executor(None, lambda: input(prompt))).strip()
