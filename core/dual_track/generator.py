"""双轨异步生成 — Fast/Slow Track + Merger + Policy Gate。

核心差异化模块:
- Fast Track: 低延迟模型，立即生成行为前缀
- Slow Track: 强推理模型，深度推理 + 一致性校验
- Merger: 对齐/去重/渐进替换
- Policy Gate: 安全审批
- State Buffer: Token 状态追踪
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


class TokenType(Enum):
    APPEND = "append"        # 追加 token
    PATCH = "patch"          # 局部替换
    INVALIDATE = "invalidate"  # 回滚
    COMMIT = "commit"        # 提交确认


@dataclass
class StreamToken:
    """流式输出 Token"""
    type: TokenType
    content: str = ""
    range_start: int = 0     # patch/invalidate 的范围
    range_end: int = 0


class StateBuffer:
    """Token 状态缓冲区——追踪 Fast/Slow 输出状态。

    - fast_tokens: Fast Track 已生成的 token 列表
    - slow_tokens: Slow Track 已生成的 token 列表
    - overlap_window: 重叠窗口 token
    - committed_index: 已提交的 token 索引
    """

    def __init__(self, overlap_size: int = 30):
        self.fast_tokens: list[str] = []
        self.slow_tokens: list[str] = []
        self.overlap_size = overlap_size
        self.committed_index: int = 0

    def add_fast(self, token: str):
        self.fast_tokens.append(token)

    def add_slow(self, token: str):
        self.slow_tokens.append(token)

    def get_overlap_window(self) -> list[str]:
        """获取 Fast 尾部的重叠窗口（Slow 以此为软前缀）。"""
        return self.fast_tokens[-self.overlap_size:] if len(self.fast_tokens) >= self.overlap_size else self.fast_tokens

    @property
    def fast_text(self) -> str:
        return "".join(self.fast_tokens)

    @property
    def slow_text(self) -> str:
        return "".join(self.slow_tokens)


class PolicyGate:
    """安全审批门——抄 Hermes approval.py 的设计模式。

    决策规则:
    - 纯文本输出: ✅ 直接流式
    - 只读工具 (read_file, search): ⚠️ 等待 Slow 确认
    - 外部调用 (web_fetch): ❌ 必须 Slow 审批
    - 写操作 (exec_command, write_file): ❌ 必须审批 + 可能需要用户确认
    """

    @staticmethod
    def classify_action(action_type: str) -> str:
        """分类行为风险等级: allow / warn / block"""
        if action_type in ("say", "stay_silent", "respond"):
            return "allow"
        if action_type in ("read_file", "search_files", "search_content", "web_search"):
            return "warn"
        if action_type in ("web_fetch",):
            return "block"
        if action_type in ("exec_command", "write_file", "edit_file"):
            return "block"
        return "warn"

    @staticmethod
    def should_wait_for_slow(action_type: str) -> bool:
        """是否需要等待 Slow Track 审批。"""
        return PolicyGate.classify_action(action_type) in ("warn", "block")

    @staticmethod
    def requires_user_approval(action_type: str) -> bool:
        """是否需要用户确认。"""
        return action_type in ("exec_command", "write_file")


class StreamMerger:
    """流合并器——对齐 Fast/Slow 输出流。

    支持:
    - Append: 追加 Slow 的不同内容
    - Patch: 局部替换 Fast 的错误内容
    - Invalidate: 回滚 Fast 的不正确内容

    MVP 阶段: 只做 append，不做 patch 和 rollback。
    """

    def __init__(self, buffer: StateBuffer):
        self.buffer = buffer

    def merge(self, slow_token: str, fast_text: str) -> list[StreamToken]:
        """合并 Fast 和 Slow 输出流。

        当前策略 (MVP):
        - 如果 Fast 还没输出完 → Fast 流、Slow 暂存
        - Fast 输出完毕后 → Slow 作为追加内容流式输出
        - 检测到冲突时 → 标记需要替换的区间
        """
        tokens: list[StreamToken] = []

        # Fast 已输出但 Slow 还未输出的部分 → 先让 Fast 流完
        if len(self.buffer.slow_tokens) == 0:
            # 首个 Slow token，检查是否与 Fast 重复
            if slow_token in fast_text[-10:]:
                return tokens  # 跳过重复

        self.buffer.add_slow(slow_token)

        # 对齐检查: Slow 前缀 vs Fast 尾部重叠
        if len(self.buffer.slow_tokens) <= 3:
            overlap = self.buffer.get_overlap_window()
            slow_prefix = "".join(self.buffer.slow_tokens)
            fast_tail = "".join(overlap)
            if slow_prefix == fast_tail[-len(slow_prefix):]:
                return tokens  # 完全重叠，跳过

        # 追加 Slow 的不同内容
        tokens.append(StreamToken(type=TokenType.APPEND, content=slow_token))
        return tokens

    def finalize(self) -> StreamToken:
        """合并完成——发送 commit。"""
        self.buffer.committed_index = len(self.buffer.fast_tokens) + len(self.buffer.slow_tokens)
        return StreamToken(type=TokenType.COMMIT)


class DualTrackGenerator:
    """双轨异步生成器。

    用法:
        gen = DualTrackGenerator(fast_provider, slow_provider)
        async for token in gen.generate(psychology_result, mindstate, ...):
            yield token
    """

    def __init__(self, fast_provider, slow_provider,
                 overlap_size: int = 30,
                 fast_timeout: float = 0.15):
        self.fast_provider = fast_provider
        self.slow_provider = slow_provider
        self.buffer = StateBuffer(overlap_size=overlap_size)
        self.merger = StreamMerger(self.buffer)
        self.policy_gate = PolicyGate()
        self.fast_timeout = fast_timeout

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        mindstate=None,
        drive_state=None,
        memory_context: str = "",
    ) -> AsyncIterator[StreamToken]:
        """执行双轨异步生成。

        1. Fast Track 立即生成行为前缀
        2. Slow Track 异步启动（用 Fast 输出作软前缀）
        3. Merger 实时合成两个流
        """
        messages = [{"role": "user", "content": user_message}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # 1. 启动 Fast Track
        fast_task = asyncio.create_task(
            self._run_fast(messages)
        )

        # 2. 等待 Fast 开始输出（有 timeout）
        fast_started = False
        try:
            async for token in fast_task:
                if not fast_started:
                    fast_started = True
                self.buffer.add_fast(token)
                yield StreamToken(type=TokenType.APPEND, content=token)
        except Exception as e:
            yield StreamToken(type=TokenType.APPEND, content=f"[Fast Track 异常: {e}]")

        # 3. 启动 Slow Track（用 Fast 输出作软前缀）
        slow_messages = list(messages)
        fast_context = self.buffer.fast_text[-200:] if self.buffer.fast_text else ""
        if fast_context:
            slow_messages[-1]["content"] = (
                f"{user_message}\n\n[前面已输出的内容，从这里继续]:\n{fast_context}"
            )

        try:
            async for token in self._run_slow(slow_messages):
                merged = self.merger.merge(token, self.buffer.fast_text)
                for mt in merged:
                    yield mt
        except Exception as e:
            yield StreamToken(type=TokenType.APPEND, content=f"[Slow Track 异常: {e}]")

        # 4. 最终 Commit
        yield self.merger.finalize()

    async def _run_fast(self, messages: list[dict]) -> AsyncIterator[str]:
        """Fast Track — 快速、低延迟生成。"""
        resp = await self.fast_provider.chat(
            messages, temperature=0.6, max_tokens=300,
        )
        for char in resp.content:
            yield char
            await asyncio.sleep(0)  # 让出控制权

    async def _run_slow(self, messages: list[dict]) -> AsyncIterator[str]:
        """Slow Track — 深度、推理生成。"""
        resp = await self.slow_provider.chat(
            messages, temperature=0.7, max_tokens=2000,
        )
        for char in resp.content:
            yield char
            await asyncio.sleep(0)
