"""LLM Provider 插件式接口 — 参考 nanobot providers/base.py 设计。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class LLMResponse:
    """LLM 返回的统一响应"""
    content: str = ""
    tool_calls: list["ToolCallRequest"] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    finish_reason: str = "stop"


@dataclass
class ToolCallRequest:
    """LLM 请求的工具调用"""
    id: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_call_id: str = ""
    name: str = ""
    output: str = ""
    error: str = ""
    success: bool = True


class LLMProvider(ABC):
    """插件式 LLM 后端抽象接口。

    支持的 Provider 类型:
    - openai: OpenAI API 及兼容接口 (Ollama, vLLM, DeepSeek 等)
    - anthropic: Anthropic Claude API
    - 自定义: 实现此接口即可

    用法:
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="...")
        response = await provider.chat(messages, temperature=0.3)
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """同步聊天接口——等待完整响应后返回。"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """流式聊天接口——逐个 token 返回。"""
        ...

    @abstractmethod
    def supports_tools(self) -> bool:
        """该 Provider 是否支持原生 function calling。"""
        ...

    @abstractmethod
    def supports_streaming(self) -> bool:
        """该 Provider 是否支持流式输出。"""
        ...


class OpenAIProvider(LLMProvider):
    """OpenAI API 兼容 Provider。

    支持所有 OpenAI 兼容接口: Ollama, vLLM, DeepSeek, Groq 等。
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "",
                 base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key or "not-needed"
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages, temperature=0.7, max_tokens=4096, tools=None):
        import urllib.request
        import urllib.error
        import json as _json

        payload = _json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:500]
            return LLMResponse(content=f"[HTTP {e.code}] {body}", usage={})
        except Exception as e:
            return LLMResponse(content=f"[错误: {e}]", usage={})

        data = _json.loads(text)
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {}) if choice else {}
        content = message.get("content", "") or ""

        tool_calls = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            args = {}
            try:
                args = _json.loads(func.get("arguments", "{}"))
            except Exception:
                pass
            tool_calls.append(ToolCallRequest(
                id=tc.get("id", ""),
                name=func.get("name", ""),
                arguments=args,
            ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop") if choice else "stop",
        )

    async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, tools=None):
        """流式输出——urllib 实现。"""
        import urllib.request
        import json as _json

        payload = _json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except _json.JSONDecodeError:
                        continue

    def supports_tools(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API Provider。"""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str = ""):
        self.model = model
        self.api_key = api_key

    async def chat(self, messages, temperature=0.7, max_tokens=4096, tools=None):
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system

        resp = await client.messages.create(**kwargs)

        content = ""
        tool_calls = []
        for block in resp.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens},
            finish_reason=resp.stop_reason or "stop",
        )

    async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, tools=None):
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system

        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def supports_tools(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
