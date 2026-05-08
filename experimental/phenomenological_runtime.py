"""Long-running phenomenological agent runtime."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .inner_experience import InnerExperienceStream
from .expression_policy import ExpressionPolicy


@dataclass
class PhenomenologicalRuntime:
    blackboard: object
    perception_stream: object
    toca_runner: object | None
    tick_s: float = 1.0
    inner_stream: InnerExperienceStream = field(default_factory=InnerExperienceStream)
    expression_policy: ExpressionPolicy = field(default_factory=ExpressionPolicy)
    running: bool = False
    tick_count: int = 0
    _task: asyncio.Task | None = None
    world_adapter: object | None = None
    _last_feedback_count: int = 0
    behavior_stream: object | None = None
    _last_outer_behavior: dict | None = None
    idle_after_s: float = 5.0
    last_external_input_t: float = 0.0

    # ═══ 生命周期 ═══

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        if self.toca_runner is not None:
            await self.toca_runner.start()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self.toca_runner is not None:
            await self.toca_runner.stop()

    async def _loop(self) -> None:
        while self.running:
            await self.tick_once()
            await asyncio.sleep(self.tick_s)

    # ═══ 单次 Tick ═══

    async def tick_once(self) -> dict:
        self.tick_count += 1
        self._consume_world_feedback()
        self._maybe_generate_idle_thought()
        self._update_inner_stream()
        self._apply_expression_policy()
        self._publish_outer_behavior()
        heartbeat = {"t": time.time(), "tick": self.tick_count}
        self.blackboard.write("runtime_heartbeat", heartbeat)
        return heartbeat

    # ═══ 内部体验更新 ═══

    def _update_inner_stream(self) -> None:
        state = self.blackboard.read([
            "dominant_emotion", "self_model", "conscious_workspace", "pad",
        ])
        emotion = state.get("dominant_emotion")
        if emotion:
            self.inner_stream.append("felt_emotion", emotion, 0.6, "blackboard", True)

        self_model = state.get("self_model", {})
        conflict = self_model.get("unresolved_conflict", "")
        if conflict:
            self.inner_stream.append("private_conflict", conflict, 0.75, "self_model", False)

        intention = self_model.get("private_intention", "")
        if intention:
            self.inner_stream.append("private_intention", intention, 0.7, "self_model", False)

        self.blackboard.write("inner_experience", self.inner_stream.to_dict())

    # ═══ 世界反馈消费 ═══

    def _consume_world_feedback(self) -> None:
        if self.world_adapter is None:
            return
        feedback = getattr(self.world_adapter, "feedback_events", [])
        new_items = feedback[self._last_feedback_count:]
        self._last_feedback_count = len(feedback)
        for item in new_items:
            intensity = abs(item.get("valence", 0.0))
            expressible = item.get("valence", 0.0) >= 0
            self.inner_stream.append(
                "action_consequence",
                item.get("result", ""),
                intensity,
                "world_feedback",
                expressible,
            )
        if new_items:
            self.blackboard.write("last_world_feedback", new_items[-1])

    # ═══ 表达策略应用 ═══

    def _apply_expression_policy(self) -> None:
        state = self.blackboard.read(["pending_response", "self_model"])
        response = state.get("pending_response")
        if not isinstance(response, dict) or not response.get("text"):
            return
        self_model = state.get("self_model", {})
        inner_items = self.inner_stream.recent(8, include_private=True)
        composed = self.expression_policy.compose(
            inner_items,
            self_model,
            proposed_text=response.get("text", ""),
        )
        outer = composed["outer"]
        self.blackboard.write("outer_behavior", outer)
        if composed["mechanism"] != "direct_expression" and composed.get("inner_used"):
            self.inner_stream.record_divergence(
                inner=composed["inner_used"][0],
                outer=outer,
                mechanism=composed["mechanism"],
            )

    # ═══ 行为流发布 ═══

    def _publish_outer_behavior(self) -> None:
        if self.behavior_stream is None:
            return
        outer = self.blackboard.read(["outer_behavior"]).get("outer_behavior")
        if not isinstance(outer, dict) or not outer.get("content"):
            return
        if self._last_outer_behavior == outer:
            return
        self._last_outer_behavior = dict(outer)
        btype = outer.get("type", "speech")
        self.behavior_stream.emit(btype, outer["content"], outer.get("confidence", 0.8))

    # ═══ 空闲思维 ═══

    def _maybe_generate_idle_thought(self) -> None:
        now = time.time()
        if self.last_external_input_t and now - self.last_external_input_t < self.idle_after_s:
            return
        state = self.blackboard.read(["self_model", "dominant_emotion"])
        conflict = state.get("self_model", {}).get("unresolved_conflict", "")
        if conflict:
            self.inner_stream.append(
                "spontaneous_thought",
                f"空闲时反复回到这个冲突: {conflict}",
                0.55,
                "idle_mentation",
                False,
            )
