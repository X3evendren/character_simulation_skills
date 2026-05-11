"""LLM Provider — OpenAI SDK 实现。抄 nanobot openai_compat_provider.py。

支持所有 OpenAI 兼容接口: DeepSeek, Ollama, vLLM 等。
流式 + 非流式 + 工具调用。
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class LLMResponse:
    content: str = ""
    reasoning_content: str = ""
    tool_calls: list["ToolCallRequest"] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    finish_reason: str = "stop"


@dataclass
class ToolCallRequest:
    id: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    tool_call_id: str = ""
    name: str = ""
    output: str = ""
    error: str = ""
    success: bool = True


class OpenAIProvider:
    """OpenAI SDK Provider。抄 nanobot openai_compat_provider.py。"""

    def __init__(self, model: str = "gpt-4o", api_key: str = "",
                 base_url: str = "https://api.openai.com/v1"):
        from openai import AsyncOpenAI
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", "not-needed"),
            base_url=base_url,
            max_retries=0,
        )

    async def chat(self, messages, temperature=0.7, max_tokens=4096,
                   tools=None) -> LLMResponse:
        kwargs = dict(model=self.model, messages=messages,
                      temperature=temperature, max_tokens=max_tokens)
        if tools:
            kwargs["tools"] = tools

        resp = await self.client.chat.completions.create(**kwargs)
        return self._parse_response(resp)

    async def chat_stream(self, messages, temperature=0.7, max_tokens=4096,
                          tools=None, on_delta=None) -> LLMResponse:
        """流式调用。on_delta: async def fn(text: str)。"""
        kwargs = dict(model=self.model, messages=messages,
                      temperature=temperature, max_tokens=max_tokens, stream=True)
        if tools:
            kwargs["tools"] = tools

        stream = await self.client.chat.completions.create(**kwargs)
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
            if on_delta and chunk.choices:
                text = chunk.choices[0].delta.content
                if text:
                    await on_delta(text)
        return self._parse_chunks(chunks)

    def _parse_response(self, resp) -> LLMResponse:
        choice = resp.choices[0] if resp.choices else None
        if not choice:
            return LLMResponse()
        msg = choice.message
        content = msg.content or ""
        reasoning = getattr(msg, 'reasoning_content', '') or ''
        tool_calls = []
        for tc in (msg.tool_calls or []):
            import json
            args = {}
            try:
                args = json.loads(tc.function.arguments)
            except: pass
            tool_calls.append(ToolCallRequest(id=tc.id, name=tc.function.name, arguments=args))
        return LLMResponse(content=content, reasoning_content=reasoning,
                          tool_calls=tool_calls, usage=self._usage(resp),
                          finish_reason=choice.finish_reason or "stop")

    def _parse_chunks(self, chunks) -> LLMResponse:
        content_parts = []
        reasoning_parts = []
        tc_bufs: dict[int, dict] = {}
        finish = "stop"
        for c in chunks:
            if not c.choices: continue
            d = c.choices[0].delta
            if d.content: content_parts.append(d.content)
            rc = getattr(d, 'reasoning_content', '')
            if rc: reasoning_parts.append(rc)
            if c.choices[0].finish_reason: finish = c.choices[0].finish_reason
            for tc in (d.tool_calls or []):
                buf = tc_bufs.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id: buf["id"] = tc.id
                if tc.function:
                    if tc.function.name: buf["name"] += tc.function.name
                    if tc.function.arguments: buf["arguments"] += tc.function.arguments

        import json
        tool_calls = []
        for buf in sorted(tc_bufs.values(), key=lambda b: b.get("index", 0)):
            args = {}
            try: args = json.loads(buf["arguments"])
            except: pass
            tool_calls.append(ToolCallRequest(id=buf["id"], name=buf["name"], arguments=args))

        return LLMResponse(
            content="".join(content_parts),
            reasoning_content="".join(reasoning_parts),
            tool_calls=tool_calls,
            usage=self._chunks_usage(chunks),
            finish_reason=finish,
        )

    def _usage(self, resp) -> dict:
        try:
            u = resp.usage
            return {"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens}
        except: return {}

    def _chunks_usage(self, chunks) -> dict:
        for c in reversed(chunks):
            if c.usage:
                return {"prompt_tokens": c.usage.prompt_tokens,
                        "completion_tokens": c.usage.completion_tokens,
                        "total_tokens": c.usage.total_tokens}
        return {}
