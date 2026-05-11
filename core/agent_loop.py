"""Agent 执行循环 — 抄 nanobot runner.py + Claude Code query.ts。

流式 + 工具调用: 每轮迭代一次完整的流式 HTTP 请求。
工具调用的"暂停/恢复"是迭代边界，不是流内中断。
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .provider import OpenAIProvider, LLMResponse, ToolCallRequest
from .tools.base import ToolRegistry, ToolResult


@dataclass
class AgentTurn:
    final_text: str = ""
    tool_calls: list[ToolResult] = field(default_factory=list)
    total_tokens: int = 0
    iterations: int = 0
    elapsed: float = 0.0


class AgentLoop:
    """Agent 执行循环。抄 nanobot runner.py。

    每轮迭代:
    1. 流式调用 LLM → on_delta 回调实时输出文本
    2. 流结束后，检测 tool_calls
    3. 有 tool_calls → 执行 → 注入结果到消息 → 开启下一轮
    4. 无 tool_calls → 结束，返回最终文本
    """

    def __init__(self, provider: OpenAIProvider, registry: ToolRegistry,
                 max_iterations: int = 10):
        self.provider = provider
        self.registry = registry
        self.max_iterations = max_iterations

    async def run(self, system_prompt: str, user_message: str,
                  on_delta=None) -> AgentTurn:
        """执行一轮 agent 对话。

        on_delta: async def fn(text: str) — 每收到 token 时调用
        """
        t0 = time.time()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        turn = AgentTurn()
        tools = self.registry.get_definitions() if self.registry else None
        text_buf = ""

        for iteration in range(self.max_iterations):
            turn.iterations = iteration + 1

            # 流式调用
            resp = await self.provider.chat_stream(
                messages, temperature=0.7, max_tokens=4000, tools=tools,
                on_delta=on_delta,
            )
            turn.total_tokens += resp.usage.get("total_tokens", 0)
            text_buf = resp.content

            # 无 tool_call → 结束
            if not resp.tool_calls:
                turn.final_text = text_buf
                break

            # 有 tool_call → 暂停流式 → 执行工具 → 注入结果
            # 构建 assistant 消息
            assistant_msg = {"role": "assistant", "content": text_buf or None}
            tc_list = []
            for tc in resp.tool_calls:
                tc_list.append({
                    "id": tc.id, "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)},
                })
            if tc_list:
                assistant_msg["tool_calls"] = tc_list
            messages.append(assistant_msg)

            # 并发执行工具
            tasks = [self.registry.execute(tc.name, tc.arguments) for tc in resp.tool_calls]
            results = await asyncio.gather(*tasks)

            for tc, tr in zip(resp.tool_calls, results):
                turn.tool_calls.append(tr)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tr.output[:4000] if tr.success else f"Error: {tr.error}",
                })

        turn.elapsed = time.time() - t0
        return turn
