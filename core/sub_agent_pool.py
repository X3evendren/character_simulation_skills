"""Sub-Agent Pool — 子智能体并发池。

限制最大并发数，防止 API 速率限制耗尽。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .sub_agent import SubAgentManager, SubAgentSpec, SubAgentHandle


@dataclass
class SubAgentPool:
    """子智能体并发池。

    用法:
        pool = SubAgentPool(manager, max_concurrent=5)
        handle = await pool.acquire(spec)
        result = await pool.collect(handle)
        pool.release(handle)
    """

    manager: SubAgentManager
    max_concurrent: int = 5
    _active_count: int = 0
    _wait_queue: list[asyncio.Event] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self, spec: SubAgentSpec,
                      parent_id: str = "") -> SubAgentHandle:
        """获取一个池槽位并 spawn 子智能体。若池满则等待。"""
        while self._active_count >= self.max_concurrent:
            event = asyncio.Event()
            self._wait_queue.append(event)
            await event.wait()

        async with self._lock:
            self._active_count += 1

        return await self.manager.spawn(spec, parent_id=parent_id)

    async def collect(self, handle: SubAgentHandle,
                      timeout: float = 30.0) -> dict | None:
        """收集结果并自动释放槽位。"""
        try:
            return await self.manager.collect(handle, timeout=timeout)
        finally:
            self._release_slot()

    def release(self, handle: SubAgentHandle) -> None:
        """手动释放槽位。"""
        self.manager.cleanup(handle.agent_id)
        self._release_slot()

    def _release_slot(self) -> None:
        """释放一个槽位，唤醒等待队列。"""
        self._active_count = max(0, self._active_count - 1)
        if self._wait_queue:
            event = self._wait_queue.pop(0)
            event.set()

    @property
    def available(self) -> int:
        return self.max_concurrent - self._active_count

    @property
    def active_count(self) -> int:
        return self._active_count

    def stats(self) -> dict:
        return {
            "max_concurrent": self.max_concurrent,
            "active": self._active_count,
            "waiting": len(self._wait_queue),
            "available": self.available,
        }
