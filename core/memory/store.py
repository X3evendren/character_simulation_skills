"""MemoryStore ABC — 统一记忆接口。

参考 Hermes Agent 的 MemoryProvider 抽象基类设计 (agent/memory_provider.py)。
所有记忆层级必须实现此接口。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MemoryRecord:
    """一条记忆记录的通用格式"""
    record_id: str = ""
    content: str = ""                      # 记忆内容
    emotional_signature: dict = field(default_factory=dict)  # {"joy": 0.8, "fear": 0.3}
    significance: float = 0.5              # 0-1
    event_type: str = "unknown"
    tags: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    trust: float = 1.0                     # 信任评分 (0-1)
    recall_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ConsolidationReport:
    """记忆巩固报告"""
    merged: int = 0
    promoted: int = 0     # 提升到上一级
    archived: int = 0     # 归档/淘汰
    conflicts: int = 0    # 检测到的冲突数


class MemoryStore(ABC):
    """统一记忆接口 — 所有记忆层级的抽象基类。

    参考 Hermes Agent agent/memory_provider.py 的设计:
    - store/recall/search/consolidate/forget 五个核心方法
    - initialize/on_session_start/on_session_end/shutdown 生命周期钩子
    """

    @abstractmethod
    async def store(self, record: MemoryRecord) -> str:
        """存储一条记忆，返回 record_id。"""
        ...

    @abstractmethod
    async def recall(self, query: str, n: int = 5) -> list[MemoryRecord]:
        """基于自然语言查询检索记忆。"""
        ...

    @abstractmethod
    async def search(
        self,
        embedding: list[float] | None = None,
        filters: dict | None = None,
        n: int = 5,
    ) -> list[MemoryRecord]:
        """混合检索: 语义相似度 + 过滤条件。"""
        ...

    @abstractmethod
    async def consolidate(self) -> ConsolidationReport:
        """记忆巩固——异步后台任务。"""
        ...

    @abstractmethod
    async def forget(self) -> int:
        """TTL + 衰减 + 冲突扫描 → 返回淘汰数量。"""
        ...

    # ── 生命周期 ──

    async def initialize(self) -> None:
        """初始化——在会话开始时调用。"""
        pass

    async def on_session_start(self) -> None:
        """会话开始钩子。"""
        pass

    async def on_session_end(self) -> None:
        """会话结束钩子——触发 Full Sleep Cycle。"""
        pass

    async def shutdown(self) -> None:
        """关闭——持久化和清理。"""
        pass

    @abstractmethod
    def __len__(self) -> int:
        ...
