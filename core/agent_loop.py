"""Agent 执行循环 — 抄 nanobot runner.py + Claude Code query.ts。

while True:
    LLM 生成 → 检测 tool_call → 暂停 → 执行工具 → 注入结果 → 继续生成 → ... → 最终回复
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .provider import LLMProvider, LLMResponse, ToolCallRequest, ToolResult
from .tools.base import ToolRegistry


@dataclass
class AgentTurn:
    """一次 agent 轮次的结果"""
    final_text: str = ""
    tool_calls: list[ToolResult] = field(default_factory=list)
    total_tokens: int = 0
    iterations: int = 0
    elapsed: float = 0.0


class AgentLoop:
    """Agent 执行循环。

    抄 Claude Code query.ts 的 while loop 模式:
    1. 发消息给 LLM
    2. 如果 LLM 返回 tool_call → 执行 → 注入结果 → 回到步骤1
    3. 如果 LLM 返回纯文本 → 结束，返回结果

    抄 nanobot runner.py 的并发工具执行 + 错误处理。
    """

    def __init__(self, provider: LLMProvider, registry: ToolRegistry,
                 max_iterations: int = 10):
        self.provider = provider
        self.registry = registry
        self.max_iterations = max_iterations

    async def run(self, system_prompt: str, user_message: str,
                  stream_callback=None) -> AgentTurn:
        """执行一轮 agent 对话。

        stream_callback: 可选，每收到 token 时调用 callback(token_str)
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

            # 调用 LLM
            resp = await self.provider.chat(
                messages, temperature=0.7, max_tokens=4000, tools=tools,
            )
            turn.total_tokens += resp.usage.get("total_tokens", 0)

            # 无 tool_call → 结束
            if not resp.tool_calls:
                turn.final_text = resp.content
                break

            # 有 tool_call → 执行
            # 先把 assistant 消息加入历史
            assistant_msg = {"role": "assistant", "content": resp.content or ""}
            if tools:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": str(tc.arguments)}}
                    for tc in resp.tool_calls
                ]
            messages.append(assistant_msg)

            # 执行工具 (并发)
            tasks = []
            for tc in resp.tool_calls:
                tasks.append(self.registry.execute(tc.name, tc.arguments))
            results = await asyncio.gather(*tasks)

            # 注入工具结果
            for tc, tr in zip(resp.tool_calls, results):
                turn.tool_calls.append(tr)
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tr.output if tr.success else f"Error: {tr.error}",
                }
                messages.append(tool_msg)

        turn.elapsed = time.time() - t0
        return turn
