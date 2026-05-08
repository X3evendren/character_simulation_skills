"""PhenomenologicalRuntime 测试 — 守护进程生命周期和内部/外部循环。"""
from __future__ import annotations

import asyncio
import os
import sys
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime


class TestPhenomenologicalRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_start_stop_lifecycle(self):
        runtime = PhenomenologicalRuntime(
            blackboard=Blackboard(),
            perception_stream=PerceptionStream(),
            toca_runner=None,
            tick_s=0.05,
        )

        await runtime.start()
        await asyncio.sleep(0.12)
        await runtime.stop()

        self.assertFalse(runtime.running)
        self.assertGreaterEqual(runtime.tick_count, 1)

    async def test_tick_writes_runtime_heartbeat(self):
        bb = Blackboard()
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)

        await runtime.tick_once()

        heartbeat = bb.read(["runtime_heartbeat"])["runtime_heartbeat"]
        self.assertEqual(heartbeat["tick"], 1)

    async def test_tick_generates_inner_experience_from_blackboard(self):
        bb = Blackboard()
        bb.write("dominant_emotion", "fear")
        bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下或显得太需要。",
            "private_intention": "希望对方主动解释。",
            "active_mask": "装作无所谓。",
        })
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)

        await runtime.tick_once()

        recent = runtime.inner_stream.recent(5)
        contents = " ".join(item["content"] for item in recent)
        self.assertIn("fear", contents)
        self.assertIn("主动解释", contents)

    async def test_expression_policy_records_divergence_when_response_exists(self):
        bb = Blackboard()
        bb.write("pending_response", {"text": "你为什么不回我？", "confidence": 0.8})
        bb.write("self_model", {
            "active_mask": "装作无所谓，用短句保护自尊。",
            "private_intention": "希望对方主动解释。",
        })
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.inner_stream.append(
            "forbidden_wish", "不要离开我，快证明你还在乎我", 0.9, "self_model", False
        )

        await runtime.tick_once()

        outer = bb.read(["outer_behavior"])["outer_behavior"]
        self.assertEqual(outer["content"], "没事，你忙吧。")
        divergence = [
            item for item in runtime.inner_stream.recent(10)
            if item.get("kind") == "inner_outer_divergence"
        ]
        self.assertTrue(divergence)

    async def test_outer_behavior_publishes_to_behavior_stream(self):
        from character_mind.experimental.behavior_stream import BehaviorStream

        bb = Blackboard()
        behavior = BehaviorStream("林雨")
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.behavior_stream = behavior
        bb.write("outer_behavior", {"type": "speech", "content": "没事，你忙吧。"})

        await runtime.tick_once()

        self.assertEqual(behavior.get_last_speech()["content"], "没事，你忙吧。")

    async def test_idle_tick_generates_spontaneous_thought(self):
        bb = Blackboard()
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.idle_after_s = 0.0
        bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下或显得太需要。",
        })

        await runtime.tick_once()

        recent = runtime.inner_stream.recent(5)
        self.assertTrue(any(item["kind"] == "spontaneous_thought" for item in recent))
