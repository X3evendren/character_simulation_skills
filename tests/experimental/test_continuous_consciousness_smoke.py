"""连续意识系统烟测试。验证完整跑道: 感知→认知管道→意识层→自我模型→行为流。"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import CognitiveOrchestrator, SkillRegistry
from character_mind import BigFiveSkill, PlutchikEmotionSkill, OCCEmotionSkill, ResponseGeneratorSkill
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.behavior_stream import BehaviorStream
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.toca_runner import TocaRunner, TocaConfig


class TestContinuousConsciousnessSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_continuous_runtime_produces_workspace_self_model_and_behavior(self):
        registry = SkillRegistry()
        registry.register(BigFiveSkill())
        registry.register(PlutchikEmotionSkill())
        registry.register(OCCEmotionSkill())
        registry.register(ResponseGeneratorSkill())
        orchestrator = CognitiveOrchestrator(registry=registry)

        bb = Blackboard()
        ps = PerceptionStream()
        behavior = BehaviorStream("林雨")
        runner = TocaRunner(
            bb, ps, orchestrator, MockProvider(quality=0.9, base_tokens=200),
            {
                "name": "林雨",
                "personality": {
                    "openness": 0.6,
                    "conscientiousness": 0.5,
                    "extraversion": 0.4,
                    "agreeableness": 0.55,
                    "neuroticism": 0.75,
                    "attachment_style": "anxious",
                },
                "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
            },
            TocaConfig(pipeline_time_s=1.0, instance_count=2, window_s=5.0),
        )
        runner.behavior_stream = behavior

        await runner.start()
        ps.feed_internal("他很久没回消息，她开始害怕被抛下", intensity=0.8)
        runner._last_input_time = time.time()
        await asyncio.sleep(2.5)
        await runner.stop()

        fields = bb.read(["conscious_workspace", "self_model", "pending_response"])
        self.assertTrue(fields["conscious_workspace"])
        self.assertIn("unresolved_conflict", fields["self_model"])
        self.assertTrue(fields["pending_response"]["text"])
        self.assertIsNotNone(behavior.get_last_speech())
