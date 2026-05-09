"""世界反馈回路测试 — 行动后果影响内部状态。"""
from __future__ import annotations

import asyncio
import unittest

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.world_adapter import WorldAdapter
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime


class TestWorldAdapter(unittest.TestCase):
    def test_records_channel_input_as_perception(self):
        adapter = WorldAdapter()
        event = adapter.receive(channel="chat", source="陈风", content="刚才在开会", intensity=0.6)

        self.assertEqual(event["modality"], "dialogue")
        self.assertEqual(event["source"], "陈风")
        self.assertIn("开会", event["content"])

    def test_records_action_feedback(self):
        adapter = WorldAdapter()
        feedback = adapter.feedback(
            action={"type": "speech", "content": "没事，你忙吧。"},
            result="对方沉默了更久",
            valence=-0.4,
        )

        self.assertEqual(feedback["kind"], "action_feedback")
        self.assertLess(feedback["valence"], 0)


class TestWorldFeedbackRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_negative_feedback_changes_inner_stream(self):
        bb = Blackboard()
        adapter = WorldAdapter()
        adapter.feedback(
            action={"type": "speech", "content": "没事，你忙吧。"},
            result="对方沉默了更久",
            valence=-0.6,
        )
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.world_adapter = adapter

        await runtime.tick_once()

        contents = " ".join(item["content"] for item in runtime.inner_stream.recent(5))
        self.assertIn("对方沉默了更久", contents)
