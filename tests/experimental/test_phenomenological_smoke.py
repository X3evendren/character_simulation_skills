"""现象学运行时端到端烟测试。"""
from __future__ import annotations

import asyncio
import os
import sys
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.behavior_stream import BehaviorStream
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime
from character_mind.experimental.world_adapter import WorldAdapter


class TestPhenomenologicalSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_inner_outer_feedback_audit_loop(self):
        bb = Blackboard()
        ps = PerceptionStream()
        behavior = BehaviorStream("林雨")
        world = WorldAdapter()
        runtime = PhenomenologicalRuntime(bb, ps, None, tick_s=0.05)
        runtime.behavior_stream = behavior
        runtime.world_adapter = world

        bb.write("dominant_emotion", "fear")
        bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下或显得太需要。",
            "active_mask": "装作无所谓，用短句保护自尊。",
            "private_intention": "希望对方主动解释。",
        })
        bb.write("pending_response", {"text": "你为什么不回我？", "confidence": 0.8})
        runtime.inner_stream.append(
            "forbidden_wish", "不要离开我，快证明你还在乎我", 0.9, "self_model", False
        )

        await runtime.tick_once()
        outer = bb.read(["outer_behavior"])["outer_behavior"]
        world.feedback(outer, "对方沉默了更久", valence=-0.6)
        await runtime.tick_once()

        recent_text = " ".join(item.get("content", "") for item in runtime.inner_stream.recent(20))
        self.assertEqual(outer["content"], "没事，你忙吧。")
        self.assertIsNotNone(behavior.get_last_speech())
        self.assertIn("对方沉默了更久", recent_text)
        self.assertTrue(any(
            item.get("kind") == "inner_outer_divergence"
            for item in runtime.inner_stream.recent(20)
        ))
