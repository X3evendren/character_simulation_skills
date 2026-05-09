"""Profile Isolation — CHARACTER_MIND_HOME 多实例隔离。

统一所有路径解析——当设置 CHARACTER_MIND_HOME 环境变量时，
所有持久化数据写入指定目录而非 ~/.character_mind。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class IsolationContext:
    """多实例隔离上下文——统一路径解析。

    用法:
        iso = IsolationContext.resolve()
        workspace_dir = iso.workspace_dir("my_character")
        cron_dir = iso.cron_dir
    """

    home_dir: str
    workspace_dir: str    # {home}/workspaces
    sessions_dir: str     # {home}/sessions
    cron_dir: str         # {home}/cron
    memory_dir: str       # {home}/memory
    skills_dir: str       # {home}/skills
    logs_dir: str         # {home}/logs

    @classmethod
    def resolve(cls, home_override: str = "") -> "IsolationContext":
        """解析所有路径——优先使用环境变量。"""
        home = home_override or os.environ.get(
            "CHARACTER_MIND_HOME",
            os.path.join(os.path.expanduser("~"), ".character_mind"),
        )
        return cls(
            home_dir=home,
            workspace_dir=os.path.join(home, "workspaces"),
            sessions_dir=os.path.join(home, "sessions"),
            cron_dir=os.path.join(home, "cron"),
            memory_dir=os.path.join(home, "memory"),
            skills_dir=os.path.join(home, "skills"),
            logs_dir=os.path.join(home, "logs"),
        )

    def ensure_dirs(self) -> None:
        """创建所有目录（如不存在）。"""
        for d in [self.workspace_dir, self.sessions_dir, self.cron_dir,
                   self.memory_dir, self.skills_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)

    def workspace_path(self, name: str) -> str:
        """获取指定工作区的路径。"""
        return os.path.join(self.workspace_dir, name)

    def session_path(self, session_id: str) -> str:
        """获取会话文件路径。"""
        return os.path.join(self.sessions_dir, f"{session_id}.json")

    def cron_jobs_path(self) -> str:
        """获取 cron 作业文件路径。"""
        return os.path.join(self.cron_dir, "jobs.json")


def get_isolation() -> IsolationContext:
    """获取当前进程的隔离上下文（单例）。"""
    global _isolation_singleton
    if "_isolation_singleton" not in globals() or _isolation_singleton is None:
        _isolation_singleton = IsolationContext.resolve()
    return _isolation_singleton


_isolation_singleton: IsolationContext | None = None
