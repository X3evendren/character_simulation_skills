"""Sub-Agent System — 子智能体管理系统。

支持 spawn（生成）/ collect（收集结果）/ cleanup（清理）子智能体。
子智能体共享 provider，在独立 CharacterMind 实例中运行。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class SubAgentSpec:
    """子智能体生成规格。"""
    name: str
    profile: dict
    task_prompt: str
    timeout_s: float = 60.0
    max_turns: int = 5
    provider_ref: object | None = None  # LLM provider


@dataclass
class SubAgentHandle:
    """子智能体句柄——用于跟踪和控制。"""
    agent_id: str
    name: str
    status: str = "pending"  # pending / running / completed / failed / timed_out
    spawned_at: float = 0.0
    completed_at: float = 0.0
    result: dict | None = None
    error: str = ""
    _task: asyncio.Task | None = field(default=None, repr=False)
    _cancel_event: asyncio.Event | None = field(default=None, repr=False)

    def elapsed(self) -> float:
        return time.time() - self.spawned_at if self.spawned_at > 0 else 0.0


class SubAgentManager:
    """子智能体管理器。

    用法:
        mgr = SubAgentManager(provider)
        handle = await mgr.spawn(SubAgentSpec(...))
        result = await mgr.collect(handle, timeout=30.0)
        mgr.cleanup(handle.agent_id)
    """

    def __init__(self, provider=None, max_agents: int = 10):
        self.provider = provider
        self.max_agents = max_agents
        self._agents: dict[str, SubAgentHandle] = {}
        self._parent_map: dict[str, str] = {}  # child_id -> parent_id

    async def spawn(self, spec: SubAgentSpec, parent_id: str = "") -> SubAgentHandle:
        """生成一个子智能体。"""
        # 检查容量
        running = sum(1 for h in self._agents.values() if h.status in ("pending", "running"))
        if running >= self.max_agents:
            raise RuntimeError(f"子智能体池已满 (max {self.max_agents})")

        agent_id = uuid.uuid4().hex[:12]
        handle = SubAgentHandle(
            agent_id=agent_id,
            name=spec.name,
            status="pending",
            spawned_at=time.time(),
        )
        self._agents[agent_id] = handle
        if parent_id:
            self._parent_map[agent_id] = parent_id

        # 异步执行
        handle._cancel_event = asyncio.Event()
        handle._task = asyncio.create_task(
            self._run_agent(agent_id, spec, handle._cancel_event)
        )
        return handle

    async def collect(self, handle: SubAgentHandle,
                      timeout: float = 30.0) -> dict | None:
        """等待子智能体完成并收集结果。"""
        if handle._task is None:
            return handle.result

        try:
            await asyncio.wait_for(handle._task, timeout=timeout)
        except asyncio.TimeoutError:
            handle.status = "timed_out"
            handle.error = f"超时 ({timeout}s)"
            if handle._task and not handle._task.done():
                handle._task.cancel()
            if handle._cancel_event:
                handle._cancel_event.set()
            handle.completed_at = time.time()

        return handle.result

    async def cancel(self, agent_id: str) -> bool:
        """取消子智能体。"""
        handle = self._agents.get(agent_id)
        if handle is None or handle.status not in ("pending", "running"):
            return False
        if handle._cancel_event:
            handle._cancel_event.set()
        if handle._task and not handle._task.done():
            handle._task.cancel()
        handle.status = "failed"
        handle.error = "被取消"
        handle.completed_at = time.time()
        return True

    def status(self, agent_id: str) -> str:
        """获取子智能体状态。"""
        handle = self._agents.get(agent_id)
        return handle.status if handle else "unknown"

    def list_active(self) -> list[str]:
        """列出活跃的（运行中或待处理）子智能体 ID。"""
        return [aid for aid, h in self._agents.items()
                if h.status in ("pending", "running")]

    def list_children(self, parent_id: str) -> list[str]:
        """列出指定父智能体的所有子智能体。"""
        return [cid for cid, pid in self._parent_map.items() if pid == parent_id]

    def cleanup(self, agent_id: str) -> None:
        """清理子智能体资源。"""
        handle = self._agents.pop(agent_id, None)
        if handle:
            if handle._task and not handle._task.done():
                handle._task.cancel()
        self._parent_map.pop(agent_id, None)

    def cleanup_children(self, parent_id: str) -> None:
        """清理指定父智能体的所有子智能体。"""
        for child_id in self.list_children(parent_id):
            self.cleanup(child_id)

    async def _run_agent(self, agent_id: str, spec: SubAgentSpec,
                         cancel_event: asyncio.Event) -> None:
        """运行子智能体的主循环。"""
        handle = self._agents.get(agent_id)
        if handle is None:
            return

        handle.status = "running"
        provider = spec.provider_ref or self.provider

        try:
            from character_mind.core.runtime_v2 import CharacterMind

            mind = CharacterMind(provider, spec.profile)
            mind.perceive(spec.task_prompt, source="sub_agent", modality="internal")

            turns = 0
            while turns < spec.max_turns:
                if cancel_event.is_set():
                    handle.status = "failed"
                    handle.error = "被取消"
                    handle.completed_at = time.time()
                    return

                await mind.runtime.tick_once()
                resp = mind.get_response()

                if resp.text:
                    handle.result = {
                        "text": resp.text,
                        "emotion": resp.emotion,
                        "action": resp.action,
                        "turns": turns + 1,
                    }
                    handle.status = "completed"
                    handle.completed_at = time.time()
                    return

                turns += 1

            handle.result = {
                "text": "",
                "emotion": "neutral",
                "turns": spec.max_turns,
            }
            handle.status = "completed"
            handle.completed_at = time.time()

        except asyncio.CancelledError:
            handle.status = "failed"
            handle.error = "任务被取消"
            handle.completed_at = time.time()
        except Exception as e:
            handle.status = "failed"
            handle.error = str(e)
            handle.completed_at = time.time()
