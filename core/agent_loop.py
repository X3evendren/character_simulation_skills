"""Agent 执行循环 — 抄 Claude Code query.ts。

流程:
  while True:
    stream LLM → accumulate content + tool_calls
    if no tool_calls: break (done)
    partition: 只读(并行) + 写(串行)
    execute batch → inject results → continue
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .provider import OpenAIProvider
from .tools.base import ToolRegistry, ToolResult
from .tools.executor import execute_all


@dataclass
class AgentTurn:
    final_text: str = ""
    tool_results: list[ToolResult] = field(default_factory=list)
    total_tokens: int = 0
    iterations: int = 0
    elapsed: float = 0.0


class AgentLoop:
    """Agent 主循环。抄 Claude Code query.ts。

    每轮一次完整流式 HTTP。工具调用是迭代边界，不是流内中断。
    """

    def __init__(self, provider: OpenAIProvider, registry: ToolRegistry,
                 max_iterations: int = 10):
        self.provider = provider
        self.registry = registry
        self.max_iterations = max_iterations

    async def run(self, system_prompt: str, user_message: str,
                  on_delta=None) -> AgentTurn:
        """执行一个完整的 agent 轮次。

        on_delta: async def fn(text: str) — 流式 token 回调
        """
        t0 = time.time()
        messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
        messages.append({"role": "user", "content": user_message})

        turn = AgentTurn()
        tools = self.registry.get_definitions() if self.registry else None

        for iteration in range(self.max_iterations):
            turn.iterations = iteration + 1

            # ── 流式调用 LLM ──
            resp = await self.provider.chat_stream(
                messages, temperature=0.7, max_tokens=4000,
                tools=tools, on_delta=on_delta,
            )
            turn.total_tokens += resp.usage.get("total_tokens", 0)

            # ── 无 tool_call → 结束 ──
            if not resp.tool_calls:
                turn.final_text = resp.content
                break

            # ── 构建 assistant 消息 ──
            assistant_msg = {"role": "assistant"}
            if resp.content:
                assistant_msg["content"] = resp.content
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": str(tc.arguments)}}
                for tc in resp.tool_calls
            ]
            messages.append(assistant_msg)

            # ── 执行工具（先并行只读，后串行写）──
            calls = [{"name": tc.name, "arguments": tc.arguments}
                     for tc in resp.tool_calls]
            results = await execute_all(calls, self.registry)
            turn.tool_results.extend(results)

            # ── 注入工具结果 ──
            for tc, tr in zip(resp.tool_calls, results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tr.output[:4000] if tr.success else f"Error: {tr.error}",
                })

        turn.elapsed = time.time() - t0
        return turn
