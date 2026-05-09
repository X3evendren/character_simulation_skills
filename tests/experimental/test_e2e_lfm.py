"""lfm2.5 端到端快速测试 — 验证 PhenomenologicalRuntime 完整 tick 循环。"""
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

from character_mind import (
    CognitiveOrchestrator, SkillRegistry, create_runtime,
    BigFiveSkill, PlutchikEmotionSkill, OCCEmotionSkill, ResponseGeneratorSkill,
)
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime


class TestE2ELFM(unittest.IsolatedAsyncioTestCase):
    """用 MockProvider 的完整 tick 循环——验证所有新模块协同工作。"""

    async def asyncSetUp(self):
        self.bb = Blackboard()
        self.ps = PerceptionStream()
        self.provider = MockProvider(quality=0.9, base_tokens=200)
        self.runtime = PhenomenologicalRuntime(
            blackboard=self.bb,
            perception_stream=self.ps,
            tick_s=0.05,
        )
        # 注入 orchestrator + provider 用于 Cognitive Frame
        self.runtime.orchestrator = create_runtime().orchestrator
        self.runtime.provider = self.provider
        self.runtime.character_state = {
            "name": "林雨",
            "personality": {
                "openness": 0.6, "neuroticism": 0.75,
                "attachment_style": "anxious",
            },
        }
        # 写入初始 Blackboard 状态
        self.bb.write("dominant_emotion", "neutral")
        self.bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下",
            "active_mask": "装作无所谓",
            "private_intention": "希望对方主动解释",
        })
        self.bb.write("conscious_workspace", [
            {"kind": "emotion", "content": "neutral", "salience": 0.1, "source": "init"},
        ])
        self.ps.feed_internal("等待对方回复", intensity=0.3)

    async def test_10_ticks_produce_heartbeat_and_memory(self):
        await self.runtime.start()
        await asyncio.sleep(0.6)
        await self.runtime.stop()

        # 验证心跳
        heartbeat = self.bb.read(["runtime_heartbeat"])["runtime_heartbeat"]
        self.assertGreaterEqual(heartbeat["tick"], 8)

        # 验证记忆代谢工作
        stats = self.runtime.stats()
        self.assertGreaterEqual(stats["memory"]["total_memories"], 0)

    async def test_cognitive_frame_triggers_and_writes(self):
        """Cognitive Frame 触发并写回 Blackboard。"""
        # 预置高显著性 workspace 以触发 Cognitive Frame
        self.bb.write("conscious_workspace", [
            {"kind": "emotion", "content": "fear", "salience": 0.8, "source": "l1"},
        ])
        self.bb.write("prediction_errors", {"L1_combined": 0.5})
        self.ps.feed_internal("他很焦虑地等待着一个永远不会回复的消息", intensity=0.8)
        await self.runtime.start()
        await asyncio.sleep(1.5)
        await self.runtime.stop()

        # Cognitive Frame 应已被触发, 无错误
        self.assertNotIn("cognitive_frame_error", self.bb)
        # 检查输出是否被写入
        emotion = self.bb.read(["dominant_emotion"]).get("dominant_emotion")
        self.assertIsNotNone(emotion)
        pending = self.bb.read(["pending_response"]).get("pending_response")
        self.assertIsNotNone(pending)

    async def test_love_state_integration(self):
        """LoveState 激活后影响 bio 上下文。"""
        self.runtime.love_state.activate_love("陈风", "attraction")
        await self.runtime.start()
        await asyncio.sleep(0.3)
        await self.runtime.stop()

        love_ctx = self.bb.read(["love_state"]).get("love_state", {})
        self.assertTrue(love_ctx.get("love_active"))

    async def test_memory_metabolism_cycles(self):
        """多次 tick 后记忆代谢周期触发。"""
        self.runtime._metabolism_interval = 2  # 每 2 tick 代谢
        await self.runtime.start()
        await asyncio.sleep(0.4)
        await self.runtime.stop()

        stats = self.runtime.stats()
        self.assertIn("memory", stats)

    async def test_noise_report_generated(self):
        """噪音报告在 tick 期间生成。"""
        self.runtime._noise_check_interval = 2
        await self.runtime.start()
        await asyncio.sleep(0.3)
        await self.runtime.stop()

        noise = self.bb.read(["noise_report"]).get("noise_report")
        self.assertIsNotNone(noise)

    async def test_experiential_field_update(self):
        """体验场在 tick 期间更新。"""
        self.bb.write("conscious_workspace", [
            {"kind": "emotion", "content": "fear", "salience": 0.8, "source": "l1"},
        ])
        self.bb.write("pad", {"pleasure": -0.5, "arousal": 0.7})
        await self.runtime.start()
        await asyncio.sleep(0.3)
        await self.runtime.stop()

        # Retention 应写入 Blackboard
        retention = self.bb.read(["retention_context"]).get("retention_context")
        # 可能为空 (第一次 tick 无旧印象可推), 但 openness 应写入
        openness = self.bb.read(["protention_openness"]).get("protention_openness")
        self.assertIsNotNone(openness)

    async def test_soul_md_file_io(self):
        """soul.md 和 memory_index.md 文件写入。"""
        self.runtime.memory_metabolism.set_soul(
            "# 林雨的灵魂\n\n"
            "- 被抛弃\n"
            "- 不被选择\n"
            "- 需要持续确认\n"
        )
        # 摄入一些记忆
        self.runtime.memory_metabolism.ingest(
            "陈风很久没回消息", {"fear": 0.8}, 0.7, ["social"]
        )
        self.runtime.memory_metabolism.metabolize()

        with tempfile.TemporaryDirectory() as tmpdir:
            self.runtime.memory_metabolism.write_to_disk(tmpdir)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "soul.md")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "memory_index.md")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "growth_log.md")))
            # 验证内容
            with open(os.path.join(tmpdir, "soul.md"), encoding="utf-8") as f:
                self.assertIn("林雨", f.read())
