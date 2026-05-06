"""真实 LLM Provider — 支持 DeepSeek / Ollama / OpenAI。

DeepSeek: 使用 OpenAI 兼容 API，base_url=https://api.deepseek.com/v1
"""
from __future__ import annotations

import os
import json
import subprocess
import asyncio
from openai import AsyncOpenAI


class RealLLMProvider:
    """真实 LLM provider。默认使用 DeepSeek API。"""

    def __init__(self, model: str | None = None):
        backend = os.environ.get("LLM_BACKEND", "deepseek")
        self.backend = backend

        if backend == "deepseek":
            self.model = model or os.environ.get("LLM_MODEL", "deepseek-chat")
            self._client = AsyncOpenAI(
                api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
                base_url="https://api.deepseek.com/v1",
            )
        elif backend == "ollama":
            self.model = model or os.environ.get("LLM_MODEL", "qwen3:14b-q4_K_M")
        elif backend == "openai":
            self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
            self._client = AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                base_url=os.environ.get("LLM_BASE_URL", None),
            )
        else:
            raise ValueError(f"Unknown backend: {backend}")

        # 非 Ollama 后端都用 OpenAI 兼容客户端
        if backend != "ollama" and not hasattr(self, "_client"):
            self._client = AsyncOpenAI(
                api_key=os.environ.get(f"{backend.upper()}_API_KEY", ""),
                base_url=os.environ.get("LLM_BASE_URL", None),
            )

    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 500) -> dict:
        if self.backend == "ollama":
            return await self._chat_ollama(messages, temperature, max_tokens)
        else:
            return await self._chat_openai(messages, temperature, max_tokens)

    async def _chat_openai(self, messages: list[dict], temperature: float,
                           max_tokens: int) -> dict:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or "{}"
        usage = response.usage
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        }

    async def _chat_ollama(self, messages: list[dict], temperature: float,
                           max_tokens: int) -> dict:
        num_predict = max(max_tokens, 800)
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        }, ensure_ascii=False)

        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/chat", "-d", payload],
                capture_output=True, timeout=300, encoding="utf-8", errors="replace",
            ),
        )
        if proc.returncode != 0:
            raise Exception(f"Ollama curl failed: {proc.stderr}")
        resp = json.loads(proc.stdout)
        content = resp.get("message", {}).get("content", "") or "{}"
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": resp.get("prompt_eval_count", 0),
                "completion_tokens": resp.get("eval_count", 0),
                "total_tokens": resp.get("prompt_eval_count", 0) + resp.get("eval_count", 0),
            },
        }

