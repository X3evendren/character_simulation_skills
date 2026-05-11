"""Agent 主循环 — 直接抄 Claude Code query.ts。

结构:
  while True:
    1. 准备消息
    2. 创建 StreamingToolExecutor
    3. for await chunk in stream:
         - 检测 tool_use → executor.addTool(block)
         - executor.getCompletedResults() → yield 完成的结果
    4. executor.getRemainingResults() → 等待剩余
    5. 各种恢复检查 → continue 或 return
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .provider import OpenAIProvider
from .tools.base import ToolRegistry, ToolResult


@dataclass
class AgentTurn:
    """一次 agent 轮次的结果"""
    final_text: str = ""
    tool_results: list[ToolResult] = field(default_factory=list)
    total_tokens: int = 0
    iterations: int = 0
    elapsed: float = 0.0


class StreamingToolExecutor:
    """流式工具执行器 — 抄 Claude Code StreamingToolExecutor.ts。

    核心设计:
    - addTool(): 从流中收到 tool_use 时调用，立即排队执行
    - getCompletedResults(): 同步返回已完成工具的结果
    - getRemainingResults(): 异步等待所有剩余工具完成
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._tools: list[dict] = []  # {id, name, params, status, is_safe, result}

    def add_tool(self, tool_id: str, name: str, params: dict):
        """从流中收到 tool_use block — 立即排队。"""
        tool = self.registry.get(name)
        is_safe = getattr(tool, 'is_concurrency_safe', True) if tool else True
        self._tools.append({
            "id": tool_id, "name": name, "params": params,
            "status": "queued", "is_safe": is_safe, "result": None,
            "task": None,
        })
        # 非阻塞启动执行
        asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """处理队列 — 抄 processQueue()。"""
        for t in self._tools:
            if t["status"] != "queued":
                continue
            if self._can_execute(t["is_safe"]):
                await self._execute_one(t)
            elif not t["is_safe"]:
                break  # 非并发工具必须等待

    def _can_execute(self, is_safe: bool) -> bool:
        """检查是否可以执行新工具。"""
        if is_safe:
            return True
        # 非并发: 没有其他工具在执行
        return not any(
            t["status"] == "executing" for t in self._tools
        )

    async def _execute_one(self, tool: dict):
        """执行单个工具 — 抄 executeTool()。"""
        tool["status"] = "executing"
        reg = self.registry
        t = reg.get(tool["name"])
        if not t:
            tool["result"] = ToolResult(name=tool["name"], success=False, error="工具不存在")
        else:
            try:
                tool["result"] = await t.execute(**tool["params"])
            except Exception as e:
                tool["result"] = ToolResult(name=tool["name"], success=False, error=str(e))
        tool["status"] = "completed"

    def get_completed_results(self) -> list[tuple[str, ToolResult]]:
        """同步获取已完成结果 — 抄 getCompletedResults()。"""
        results = []
        for t in self._tools:
            if t["status"] == "completed" and t["result"] is not None:
                results.append((t["id"], t["result"]))
                t["status"] = "yielded"
        return results

    async def get_remaining_results(self) -> list[tuple[str, ToolResult]]:
        """等待所有剩余工具完成 — 抄 getRemainingResults()。"""
        # 等待所有 executing/queued 完成
        for _ in range(100):  # 最多等 10 秒
            pending = [t for t in self._tools if t["status"] in ("executing", "queued")]
            if not pending:
                break
            await asyncio.sleep(0.1)
        return self.get_completed_results()


class AgentLoop:
    """Agent 主循环 — 抄 Claude Code query.ts。"""

    def __init__(self, provider: OpenAIProvider, registry: ToolRegistry,
                 max_iterations: int = 10):
        self.provider = provider
        self.registry = registry
        self.max_iterations = max_iterations

    async def run(self, system_prompt: str, user_message: str,
                  on_delta=None) -> AgentTurn:
        """执行一个完整的 agent 轮次。

        on_delta: async def fn(text: str)
        """
        t0 = time.time()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        turn = AgentTurn()
        tools = self.registry.get_definitions() if self.registry else None

        for iteration in range(self.max_iterations):
            turn.iterations = iteration + 1

            # ── 创建流式执行器 ──
            executor = StreamingToolExecutor(self.registry)

            # ── 流式调用 LLM ──
            resp = await self.provider.chat_stream(
                messages, temperature=0.7, max_tokens=4000,
                tools=tools, on_delta=on_delta,
            )
            turn.total_tokens += resp.usage.get("total_tokens", 0)

            # ── 流中检测 tool_use → executor.addTool ──
            for tc in resp.tool_calls:
                executor.add_tool(tc.id, tc.name, tc.arguments)

            # ── 获取流中已完成的结果 ──
            completed = executor.get_completed_results()

            # ── 等待剩余 ──
            remaining = await executor.get_remaining_results()
            all_results = completed + remaining

            # ── 无 tool_call → 结束 ──
            if not resp.tool_calls:
                turn.final_text = resp.content
                break

            # ── 构建 assistant 消息 ──
            assistant_msg = {"role": "assistant"}
            if resp.content:
                assistant_msg["content"] = resp.content
            if resp.reasoning_content:
                assistant_msg["reasoning_content"] = resp.reasoning_content
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": str(tc.arguments)}}
                for tc in resp.tool_calls
            ]
            messages.append(assistant_msg)

            # ── 注入工具结果 ──
            for tool_id, tr in all_results:
                turn.tool_results.append(tr)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": tr.output[:4000] if tr.success else f"Error: {tr.error}",
                })

        turn.elapsed = time.time() - t0
        return turn
