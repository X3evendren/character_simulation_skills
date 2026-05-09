"""Behavior Controller — 双通道行为控制器。

连接 InboundChannel 和 OutboundChannel，管理整个从感知到表达的行为循环。
零 token 成本——纯状态机 + 草稿管理。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .behavior_channel import (
    InboundChannel, OutboundChannel, InboundState, OutboundState,
)


@dataclass
class BehaviorController:
    """双通道行为控制器。

    管理从感知输入到行为输出的完整生命周期：
    1. InboundChannel 接收感知 → 进入 RECEIVING
    2. 认知处理 → PROCESSING → RESPONDING
    3. OutboundChannel 起草行为 → DRAFTING
    4. 表达策略过滤 → COMMITTING
    5. 发布行为 → EXPRESSED

    Attributes:
        inbound: 感知通道
        outbound: 行为通道
        inner_experience: 内部体验缓存（被表达策略过滤的内容）
        divergence_log: 内/外部表达差异记录
    """

    inbound: InboundChannel = field(default_factory=InboundChannel)
    outbound: OutboundChannel = field(default_factory=OutboundChannel)
    inner_experience: list[dict] = field(default_factory=list)
    divergence_log: list[dict] = field(default_factory=list)
    max_divergence_log: int = 100

    # ── 感知阶段 ──

    def on_perceive(self, content: str, source: str = "external",
                    intensity: float = 0.5) -> None:
        """感知事件到达。"""
        self.inbound.receive(content, source, intensity)

    def on_processing_start(self) -> None:
        """开始认知处理。"""
        self.inbound.start_processing()
        self.inbound.set_typing(False)  # 处理期间不显示 typing

    def on_processing_end(self) -> None:
        """认知处理结束。"""
        self.inbound.start_responding()

    # ── 表达阶段 ──

    def on_response_ready(self, text: str, confidence: float = 0.5,
                          response_type: str = "speech") -> None:
        """回应已生成，进入起草阶段。"""
        self.outbound.start_drafting()
        draft = self.outbound.add_draft(text, confidence, response_type)
        self.outbound.commit(draft)

    def on_express(self, text: str, confidence: float = 0.5,
                   response_type: str = "speech") -> dict | None:
        """尝试表达（发布行为）。返回行为字典或 None（冷却中）。"""
        # 如果还没有草稿，创建新的
        if not self.outbound.committed:
            self.outbound.start_drafting()
            draft = self.outbound.add_draft(text, confidence, response_type)
            self.outbound.commit(draft)

        expressed = self.outbound.express()
        if expressed is None:
            return None

        self.inbound.finish_response()
        self.outbound.finish_expression()

        return {
            "type": expressed.draft_type,
            "content": expressed.content,
            "confidence": expressed.confidence,
            "timestamp": time.time(),
        }

    def on_silence(self) -> dict:
        """表达为沉默。"""
        self.inbound.finish_response()
        self.outbound.cancel_drafts()
        return {"type": "silence", "content": "", "confidence": 1.0, "timestamp": time.time()}

    # ── 内部/外部分裂 ──

    def record_inner_experience(self, experience: dict) -> None:
        """记录内部体验（角色真正感受到但可能不表达的）。"""
        experience["timestamp"] = time.time()
        self.inner_experience.append(experience)
        if len(self.inner_experience) > 50:
            self.inner_experience = self.inner_experience[-50:]

    def record_divergence(self, inner: dict, outer: dict, mechanism: str) -> None:
        """记录内部/外部分裂。"""
        self.divergence_log.append({
            "inner": inner,
            "outer": outer,
            "mechanism": mechanism,
            "timestamp": time.time(),
        })
        if len(self.divergence_log) > self.max_divergence_log:
            self.divergence_log = self.divergence_log[-self.max_divergence_log:]

    # ── 状态查询 ──

    def is_ready_to_express(self) -> bool:
        """是否可以发布行为（冷却已过且有已提交的草稿）。"""
        return (self.outbound.state == OutboundState.COMMITTING
                and bool(self.outbound.committed))

    def is_processing(self) -> bool:
        """是否正在处理感知输入。"""
        return self.inbound.state in (InboundState.PROCESSING, InboundState.RESPONDING)

    def status(self) -> dict:
        return {
            "inbound": self.inbound.status(),
            "outbound": self.outbound.status(),
            "inner_experiences": len(self.inner_experience),
            "divergences": len(self.divergence_log),
        }

    def reset(self) -> None:
        """重置双通道状态。"""
        self.inbound = InboundChannel()
        self.outbound = OutboundChannel()
        self.inner_experience.clear()
        # 保留 divergence_log 用于审计
