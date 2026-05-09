"""Behavior Channel — 双通道行为模式。

借鉴 OpenClaw 的双通道设计，将行为流分为：
- InboundChannel: 感知管道，追踪输入状态机
- OutboundChannel: 行为管道，管理输出草稿和发布

零 token 成本，纯状态机。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class InboundState(str, Enum):
    IDLE = "idle"
    RECEIVING = "receiving"
    PROCESSING = "processing"
    RESPONDING = "responding"


class OutboundState(str, Enum):
    IDLE = "idle"
    DRAFTING = "drafting"
    COMMITTING = "committing"
    EXPRESSED = "expressed"


@dataclass
class DraftEntry:
    """草稿缓冲区条目。"""
    content: str
    confidence: float = 0.5
    draft_type: str = "speech"       # speech / action / micro_expression
    created_at: float = 0.0
    expires_at: float = 0.0           # TTL 过期时间
    committed: bool = False

    def is_expired(self) -> bool:
        return time.time() > self.expires_at if self.expires_at > 0 else False


@dataclass
class InboundChannel:
    """感知通道——追踪外部输入的处理状态。

    状态机: IDLE → RECEIVING → PROCESSING → RESPONDING → IDLE

    属性:
        state: 当前状态
        last_perception: 最近一次感知内容
        typing_indicator: 是否显示"对方正在输入"
        status_reaction: 对输入的状态反应 (seen/reacted/hearted 等)
    """

    state: InboundState = InboundState.IDLE
    last_perception: dict | None = None
    last_input_t: float = 0.0
    typing_indicator: bool = False
    status_reaction: str = ""         # seen / reacted / hearted / angry
    draft_ttl: float = 5.0

    def receive(self, content: str, source: str = "external",
                intensity: float = 0.5) -> None:
        """接收感知输入，推进状态机。"""
        self.state = InboundState.RECEIVING
        self.last_input_t = time.time()
        self.last_perception = {
            "content": content,
            "source": source,
            "intensity": intensity,
            "received_at": self.last_input_t,
        }
        self.status_reaction = self._infer_reaction(content, intensity)

    def start_processing(self) -> None:
        """开始处理感知输入。"""
        if self.state == InboundState.RECEIVING:
            self.state = InboundState.PROCESSING

    def start_responding(self) -> None:
        """开始生成回应。"""
        self.state = InboundState.RESPONDING

    def finish_response(self) -> None:
        """回应完成，返回空闲。"""
        self.state = InboundState.IDLE
        self.typing_indicator = False

    def set_typing(self, is_typing: bool) -> None:
        self.typing_indicator = is_typing

    @staticmethod
    def _infer_reaction(content: str, intensity: float) -> str:
        """推断对输入的状态反应。"""
        if intensity < 0.3:
            return "seen"
        content_lower = content.lower()
        if any(w in content_lower for w in ("爱", "喜欢", "想你", "love", "miss")):
            return "hearted"
        if any(w in content_lower for w in ("冲突", "争吵", "恨", "angry", "hate")):
            return "angry"
        return "reacted"

    def status(self) -> dict:
        return {
            "state": self.state.value,
            "typing": self.typing_indicator,
            "reaction": self.status_reaction,
            "last_input_age": time.time() - self.last_input_t if self.last_input_t > 0 else -1,
        }


@dataclass
class OutboundChannel:
    """行为通道——管理输出草稿和发布。

    状态机: IDLE → DRAFTING → COMMITTING → EXPRESSED → IDLE

    属性:
        state: 当前状态
        drafts: 草稿缓冲区（候选行为）
        committed: 已提交待发布的行为
    """

    state: OutboundState = OutboundState.IDLE
    drafts: list[DraftEntry] = field(default_factory=list)
    committed: list[DraftEntry] = field(default_factory=list)
    max_drafts: int = 5
    draft_ttl: float = 5.0
    _last_emit_t: float = 0.0
    _emit_cooldown: float = 0.5  # 两次发布最小间隔

    def start_drafting(self) -> None:
        """开始起草行为。"""
        self.state = OutboundState.DRAFTING

    def add_draft(self, content: str, confidence: float = 0.5,
                  draft_type: str = "speech") -> DraftEntry:
        """添加草稿。自动修剪过期和超量。"""
        self._prune_expired()
        if len(self.drafts) >= self.max_drafts:
            self.drafts = self.drafts[-(self.max_drafts - 1):]

        draft = DraftEntry(
            content=content,
            confidence=confidence,
            draft_type=draft_type,
            created_at=time.time(),
            expires_at=time.time() + self.draft_ttl,
        )
        self.drafts.append(draft)
        return draft

    def commit(self, draft: DraftEntry) -> None:
        """提交草稿——将其标记为待发布。"""
        draft.committed = True
        self.committed.append(draft)
        self.state = OutboundState.COMMITTING

    def express(self) -> DraftEntry | None:
        """发布已提交的行为。返回最近提交的草稿。"""
        now = time.time()
        if now - self._last_emit_t < self._emit_cooldown:
            return None

        if not self.committed:
            # 尝试自动提交置信度最高的草稿
            active = [d for d in self.drafts if not d.committed and not d.is_expired()]
            if active:
                best = max(active, key=lambda d: d.confidence)
                self.commit(best)
            else:
                return None

        if self.committed:
            self._last_emit_t = now
            self.state = OutboundState.EXPRESSED
            return self.committed[-1]
        return None

    def finish_expression(self) -> None:
        """表达完成，清理已发布并返回空闲。"""
        self.committed.clear()
        self.state = OutboundState.IDLE

    def cancel_drafts(self) -> None:
        """取消所有未提交的草稿。"""
        self.drafts = [d for d in self.drafts if d.committed]
        if not self.drafts:
            self.state = OutboundState.IDLE

    def _prune_expired(self) -> None:
        """清理过期草稿。"""
        self.drafts = [d for d in self.drafts if not d.is_expired()]

    def status(self) -> dict:
        self._prune_expired()
        return {
            "state": self.state.value,
            "draft_count": len(self.drafts),
            "committed_count": len(self.committed),
            "cooldown_remaining": max(0, self._emit_cooldown - (time.time() - self._last_emit_t)),
        }
