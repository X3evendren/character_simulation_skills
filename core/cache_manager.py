"""Cache Manager — 缓存感知的提示管理。

跟踪 Anthropic prompt cache breakpoints，延迟破坏性配置变更，
在 cache TTL 边界对齐失效时机，避免浪费已缓存的系统提示。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CacheManager:
    """提示缓存管理器。

    默认延迟 300 秒（对齐 Anthropic prompt cache TTL），
    确保已缓存的系统提示在当前窗口内仍可用。
    `--now` / force=True 可立即失效。

    Attributes:
        breakpoints: 缓存断点 token 位置估计
        pending_invalidations: 待执行的失效
        default_delay: 默认延迟秒数
    """

    default_delay: float = 300.0
    breakpoints: dict[str, int] = field(default_factory=dict)
    pending_invalidations: dict[str, float] = field(default_factory=dict)
    _last_forced: dict[str, float] = field(default_factory=dict)

    def record_breakpoint(self, key: str, token_position: int) -> None:
        """记录一个缓存断点。"""
        self.breakpoints[key] = token_position

    def schedule_invalidation(self, cache_key: str,
                              delay: float | None = None) -> None:
        """安排缓存失效——延迟到 TTL 边界。"""
        delay_s = delay if delay is not None else self.default_delay
        self.pending_invalidations[cache_key] = time.time() + delay_s

    def force_now(self, cache_key: str) -> None:
        """立即失效缓存（`--now` 等效）。"""
        self.pending_invalidations.pop(cache_key, None)
        self._last_forced[cache_key] = time.time()
        # 清除相关断点
        for bk in list(self.breakpoints):
            if bk.startswith(cache_key):
                self.breakpoints.pop(bk, None)

    def check(self, cache_key: str) -> bool:
        """检查缓存是否已失效。

        Returns:
            True 如果缓存应被清除（延迟已过或已强制）。
        """
        if cache_key in self._last_forced:
            return True
        deadline = self.pending_invalidations.get(cache_key)
        if deadline is None:
            return False
        if time.time() >= deadline:
            self.pending_invalidations.pop(cache_key, None)
            return True
        return False

    def is_pending(self, cache_key: str) -> bool:
        """是否有待处理的失效？"""
        return cache_key in self.pending_invalidations

    def remaining_seconds(self, cache_key: str) -> float:
        """距离失效还有多少秒。"""
        deadline = self.pending_invalidations.get(cache_key)
        if deadline is None:
            return 0.0
        return max(0.0, deadline - time.time())

    def status(self) -> dict:
        return {
            "pending_count": len(self.pending_invalidations),
            "breakpoints_count": len(self.breakpoints),
            "pending": {
                k: f"{self.remaining_seconds(k):.0f}s"
                for k in self.pending_invalidations
            },
        }
