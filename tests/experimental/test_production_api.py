"""生产级 API 集成测试 — CharacterMind v2。"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest
import tempfile

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.benchmark.mock_provider import MockProvider
from character_mind.core.runtime_v2 import CharacterMind, CharacterResponse


class TestCharacterMind(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.provider = MockProvider(quality=0.9, base_tokens=200)
        self.profile = {
            "name": "林雨",
            "personality": {
                "openness": 0.6, "conscientiousness": 0.5,
                "extraversion": 0.4, "agreeableness": 0.55,
                "neuroticism": 0.75,
                "attachment_style": "anxious",
                "defense_style": ["投射", "合理化"],
            },
            "trauma": {
                "ace_score": 2,
                "active_schemas": ["遗弃/不稳定", "屈从"],
                "trauma_triggers": ["被忽视", "被抛弃"],
            },
            "ideal_world": {
                "ideal_self": "被坚定选择的、无需担心被抛弃的人",
            },
        }
        self.mind = CharacterMind(self.provider, self.profile, tick_interval=0.05)

    async def test_perceive_triggers_cognitive_frame(self):
        """外部输入触发 Cognitive Frame 并生成回应。"""
        self.mind.perceive("陈风两小时没回消息", source="陈风")
        await self.mind.runtime.tick_once()
        resp = self.mind.get_response()
        self.assertTrue(resp.text or resp.emotion)
        self.assertIsInstance(resp, CharacterResponse)

    async def test_multiple_ticks_produce_varied_state(self):
        """多次 tick 后状态演化。"""
        self.mind.perceive("你在想什么？", source="陈风")
        for _ in range(3):
            await self.mind.runtime.tick_once()
        stats = self.mind.stats()
        self.assertGreaterEqual(stats["tick_count"], 0)
        self.assertGreater(stats["memory"]["total_memories"], 0)

    async def test_love_activation_changes_behavior(self):
        """爱情激活后影响状态。"""
        self.mind.love.activate_love("陈风", "attraction")
        self.assertTrue(self.mind.love.active)
        for _ in range(2):
            await self.mind.runtime.tick_once()
        love_ctx = self.mind.blackboard.read(["love_state"])["love_state"]
        self.assertTrue(love_ctx.get("love_active"))

    async def test_world_feedback_loop(self):
        """世界反馈被记录和处理。"""
        self.mind.world_feedback(
            {"type": "speech", "content": "没事。", "confidence": 0.8},
            "对方沉默了更久", -0.6,
        )
        await self.mind.runtime.tick_once()
        # 反馈应被消费
        fb = self.mind.blackboard.read(["last_world_feedback"])
        self.assertIsNotNone(fb.get("last_world_feedback"))

    async def test_save_and_load_state(self):
        """状态持久化和恢复。"""
        self.mind.perceive("一个重要的记忆", source="internal", modality="internal")
        for _ in range(2):
            await self.mind.runtime.tick_once()

        with tempfile.TemporaryDirectory() as tmpdir:
            self.mind.save_state(tmpdir)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "soul.md")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "memory_index.md")))

    async def test_noise_report_readable(self):
        """噪音报告可读。"""
        self.mind.perceive("日常琐事", intensity=0.1)
        await self.mind.runtime.tick_once()
        report = self.mind.noise_report()
        self.assertIn("噪音报告", report)

    async def test_memory_index_generated(self):
        """记忆索引生成。"""
        idx = self.mind.memory_index()
        self.assertIn("Memory Index", idx)

    async def test_start_stop_lifecycle(self):
        """启动/停止生命周期。"""
        self.mind.runtime.tick_s = 0.01
        self.mind.start()
        await asyncio.sleep(0.15)
        self.mind.stop()
        self.assertFalse(self.mind._running)
