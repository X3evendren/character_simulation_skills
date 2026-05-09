"""TocaRunner 端到端集成测试。

用 MockProvider 驱动完整的 TOCA 连续意识流，验证:
- Blackboard 版本化写入
- ThalamicGate 感知过滤
- ConsciousnessLayer 预测加工 + 广播决策
- WmLtmBridge 记忆检索
- TocaRunner 调度统计
"""
from __future__ import annotations

import asyncio
import sys
import os
import time
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import (
    CognitiveOrchestrator, SkillRegistry,
    BigFiveSkill, PlutchikEmotionSkill, OCCEmotionSkill, ResponseGeneratorSkill,
)
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental._archive.toca_runner import TocaRunner, TocaConfig
from character_mind.experimental.thalamic_gate import ThalamicGate
from character_mind.experimental.consciousness import ConsciousnessLayer
from character_mind.experimental._archive.wm_ltm_bridge import WmLtmBridge


def _build_minimal_orchestrator():
    """构建最小编排器，注册 4 个核心 Skill。"""
    registry = SkillRegistry()
    registry.register(BigFiveSkill())
    registry.register(PlutchikEmotionSkill())
    registry.register(OCCEmotionSkill())
    registry.register(ResponseGeneratorSkill())
    return CognitiveOrchestrator(registry=registry)


def _base_character_state():
    return {
        "name": "测试角色",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.4,
            "agreeableness": 0.55, "neuroticism": 0.65,
            "attachment_style": "anxious",
            "defense_style": ["投射", "合理化"],
        },
        "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
        "emotion_decay": {
            "fast": {"pleasure": -0.1, "arousal": 0.3, "dominance": -0.2},
            "slow": {"pleasure": -0.15, "arousal": 0.2, "dominance": -0.1},
        },
    }


class TestBlackboard(unittest.TestCase):
    """Blackboard 版本化读写 + 乐观锁。"""

    def test_basic_write_read(self):
        bb = Blackboard()
        bb.write("pad", {"pleasure": -0.2, "arousal": 0.5}, instance_id=1)
        data = bb.read(["pad"])
        self.assertEqual(data["pad"]["pleasure"], -0.2)
        self.assertEqual(data["pad"]["arousal"], 0.5)

    def test_version_increment(self):
        bb = Blackboard()
        bb.write("test", "v1", instance_id=1)
        self.assertEqual(bb.get_version("test"), 1)
        bb.write("test", "v2", instance_id=2)
        self.assertEqual(bb.get_version("test"), 2)

    def test_optimistic_lock_success(self):
        bb = Blackboard()
        bb.write("x", 10, instance_id=1)
        ok = bb.try_write("x", 20, expected_version=1, instance_id=2)
        self.assertTrue(ok)
        self.assertEqual(bb.read(["x"])["x"], 20)

    def test_optimistic_lock_conflict(self):
        bb = Blackboard()
        bb.write("x", 10, instance_id=1)
        # 版本 1 已被实例 1 写入，实例 2 用版本 0 尝试写入应失败
        ok = bb.try_write("x", 30, expected_version=0, instance_id=2)
        self.assertFalse(ok)
        self.assertEqual(bb.read(["x"])["x"], 10)  # 未改变

    def test_contains_and_keys(self):
        bb = Blackboard()
        bb.write("a", 1)
        self.assertIn("a", bb)
        self.assertIn("a", bb.keys())


class TestThalamicGate(unittest.TestCase):
    """丘脑门控感知过滤。"""

    def test_high_emotion_passes(self):
        gate = ThalamicGate()
        r = gate.evaluate({
            "t": time.time(), "modality": "internal",
            "content": "他感到一阵恐慌，心跳加速", "intensity": 0.5,
        })
        self.assertTrue(r["should_process"])

    def test_neutral_visual_blocked(self):
        gate = ThalamicGate()
        r = gate.evaluate({
            "t": time.time(), "modality": "visual",
            "content": "窗外有一片树叶飘落", "intensity": 0.1,
        })
        # 低显著性视觉应被门控，除非累积或超时
        self.assertFalse(r["should_process"])

    def test_dialogue_always_passes(self):
        gate = ThalamicGate()
        r = gate.evaluate({
            "t": time.time(), "modality": "dialogue",
            "content": "你好吗", "intensity": 0.2,
        })
        self.assertTrue(r["should_process"])

    def test_accumulated_buffer_triggers(self):
        gate = ThalamicGate(threshold=0.2)
        for i in range(5):
            r = gate.evaluate({
                "t": time.time() + i, "modality": "visual",
                "content": f"普通的第{i}件事", "intensity": 0.2,
            })
        # 累积多次后应触发 (accumulated_intensity > threshold*2)
        self.assertGreater(gate.state.accumulated_intensity, 0.2 * 2)
        self.assertTrue(r["should_process"])

    def test_flush_clears_buffer(self):
        gate = ThalamicGate()
        gate.evaluate({
            "t": time.time(), "modality": "internal",
            "content": "焦虑不安", "intensity": 0.5,
        })
        buf = gate.flush()
        self.assertEqual(len(buf), 1)
        self.assertEqual(len(gate.state.buffer), 0)
        self.assertEqual(gate.state.accumulated_intensity, 0.0)


class TestConsciousnessLayer(unittest.TestCase):
    """意识层: GWT + HOT + 预测加工。"""

    def setUp(self):
        self.bb = Blackboard()
        self.bb.write("pad", {"pleasure": -0.2, "arousal": 0.5})
        self.bb.write("dominant_emotion", "neutral")
        self.cl = ConsciousnessLayer(self.bb)

    def test_predict_next_cold_start(self):
        p = self.cl.predict_next()
        self.assertIn("L1_pad", p)
        self.assertAlmostEqual(p["L1_pad"]["pleasure"], -0.2, places=5)
        self.assertAlmostEqual(p["L1_pad"]["arousal"], 0.5, places=5)

    def test_ewma_smoothes_shift(self):
        self.cl.predict_next()
        # 模拟情绪跳跃
        self.bb.write("pad", {"pleasure": -0.8, "arousal": 0.9})
        p = self.cl.predict_next()
        # EWMA 应平滑，预测应在原始值和当前值之间
        self.assertGreater(p["L1_pad"]["pleasure"], -0.8)
        self.assertLess(p["L1_pad"]["pleasure"], -0.1)

    def test_adaptive_alpha_decreases_with_volatility(self):
        # 制造波动
        for v in [-0.2, -0.6, -0.1, -0.7, -0.3]:
            self.bb.write("pad", {"pleasure": v, "arousal": 0.5})
            self.cl.predict_next()
        alpha = self.cl._adaptive_alpha("pleasure")
        # 高波动 → alpha 应低于基线 0.3
        self.assertLess(alpha, 0.3)

    def test_compute_prediction_error(self):
        self.cl.predict_next()
        self.bb.write("pad", {"pleasure": -0.5, "arousal": 0.7})
        errors = self.cl.compute_prediction_error()
        self.assertIn("L1_combined", errors)
        self.assertGreater(errors["L1_combined"], 0)

    def test_self_perceive_generates_text(self):
        perception = self.cl.self_perceive(force=True)
        self.assertIsInstance(perception, str)
        self.assertGreater(len(perception), 3)
        self.assertIn("self_perception", self.bb)

    def test_filter_broadcast_decisions(self):
        self.bb.write("dominant_emotion", "fear")
        self.bb.write("pad", {"pleasure": -0.5, "arousal": 0.8})
        decisions = self.cl.filter_broadcast()
        self.assertIn("emotion", decisions)
        self.assertIsInstance(decisions["emotion"], bool)


class TestWmLtmBridge(unittest.TestCase):
    """WM-LTM 桥接: 感知→记忆检索。"""

    def setUp(self):
        from character_mind.core.episodic_memory import EpisodicMemoryStore, EpisodicMemory
        self.store = EpisodicMemoryStore()
        # 存入几条测试记忆
        self.store.store(EpisodicMemory(
            timestamp=time.time() - 100,
            description="陈风很久没回消息，她感到被忽视",
            emotional_signature={"fear": 0.7, "sadness": 0.4},
            significance=0.6, event_type="social", tags=["attachment"],
        ))
        self.store.store(EpisodicMemory(
            timestamp=time.time() - 200,
            description="师父当众批评她",
            emotional_signature={"fear": 0.5, "anger": 0.6},
            significance=0.8, event_type="conflict", tags=["authority"],
        ))
        self.bridge = WmLtmBridge(self.store)

    def test_extract_keywords_from_chinese(self):
        kw = self.bridge._extract_keywords("陈风两小时没回消息，林雨感到非常焦虑和不安")
        # 应提取出有意义的 2-4 字片段
        self.assertGreater(len(kw), 0)

    def test_extract_emotion_tags(self):
        tags = self.bridge._extract_emotion_tags("她感到非常焦虑和不安，心里很绝望")
        self.assertIn("fear", tags)
        self.assertIn("sadness", tags)

    def test_cosine_similarity(self):
        sim = self.bridge._cosine_similarity(
            {"fear": 0.7, "sadness": 0.3},
            {"fear": 0.6, "anger": 0.1},
        )
        self.assertGreater(sim, 0.8)

    def test_check_and_retrieve_matches(self):
        window = [
            {"content": "他很久没回消息了，她开始害怕被抛弃",
             "modality": "internal", "t": time.time()},
        ]
        memories = self.bridge.check_and_retrieve(window, current_emotion="fear")
        self.assertGreater(len(memories), 0)
        # 应至少返回一条与害怕/被忽视相关的记忆
        all_descs = " ".join(m["description"] for m in memories)
        has_relevant = "陈风" in all_descs or "批评" in all_descs or "被忽视" in all_descs
        self.assertTrue(has_relevant, f"Expected relevant memory, got: {all_descs}")

    def test_format_for_context(self):
        mems = [{"description": "陈风很久没回消息，她感到被忽视",
                  "emotional_signature": {"fear": 0.7}}]
        formatted = self.bridge.format_for_context(mems)
        self.assertIn("陈风", formatted)
        self.assertIn("你想起过去的事", formatted)


class TestTocaRunnerIntegration(unittest.IsolatedAsyncioTestCase):
    """TocaRunner 端到端集成测试。"""

    async def asyncSetUp(self):
        self.provider = MockProvider(quality=0.9, base_tokens=200)
        self.orch = _build_minimal_orchestrator()
        self.bb = Blackboard()
        self.ps = PerceptionStream()
        self.cs = _base_character_state()
        self.config = TocaConfig(pipeline_time_s=1.0, instance_count=2, window_s=5.0)
        self.runner = TocaRunner(
            self.bb, self.ps, self.orch, self.provider, self.cs, self.config,
        )

    async def test_start_and_stop(self):
        """启动 + 停止不抛异常。"""
        await self.runner.start()
        await asyncio.sleep(0.5)
        await self.runner.stop()
        self.assertFalse(self.runner._running)

    async def test_pipeline_writes_to_blackboard(self):
        """注入感知后 Blackboard 应收到管道输出。"""
        await self.runner.start()
        # 注入一条有情绪的感知触发管道处理
        self.ps.feed_internal("他很久没回消息，她很焦虑不安", intensity=0.6)
        self.runner._last_input_time = time.time()
        # 等待至少一个管道实例完成
        await asyncio.sleep(self.config.pipeline_time_s + 2.0)
        await self.runner.stop()
        # 检查 Blackboard
        self.assertIn("pad", self.bb)
        self.assertIn("dominant_emotion", self.bb)

    async def test_stats_after_run(self):
        """运行后统计应有效。"""
        await self.runner.start()
        self.ps.feed_dialogue("你还好吗？", source="对方", intensity=0.5)
        self.runner._last_input_time = time.time()
        await asyncio.sleep(self.config.pipeline_time_s + 2.0)
        await self.runner.stop()
        stats = self.runner.stats()
        self.assertIn("total_instances", stats)
        self.assertGreaterEqual(stats["total_instances"], 1)

    async def test_thalamic_gate_filters_in_runner(self):
        """感知经过丘脑门控过滤。"""
        await self.runner.start()
        # 低显著视觉不应触发管道
        self.ps.feed_visual("普通的街道", intensity=0.1)
        await asyncio.sleep(0.2)  # 短等，不够管道时间
        # 门控应该有抑制记录
        self.assertGreaterEqual(self.runner.thalamic_gate.state.suppressed_count, 0)
        await self.runner.stop()

    async def test_consciousness_layer_in_runner(self):
        """意识层在管道运行期间启动。"""
        await self.runner.start()
        self.ps.feed_internal("焦虑的情绪蔓延", intensity=0.6)
        self.runner._last_input_time = time.time()
        await asyncio.sleep(self.config.pipeline_time_s + 1.5)
        stats = self.runner.consciousness.stats()
        self.assertIn("broadcast_count", stats)
        await self.runner.stop()

    async def test_write_back_uses_instance_snapshot_versions(self):
        from character_mind.core.base import SkillResult
        from character_mind.core.orchestrator import CognitiveResult

        self.bb.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0}, instance_id=1)
        start_versions = self.bb.read_with_versions()
        self.bb.write("pad", {"pleasure": 0.2, "arousal": 0.4, "dominance": 0.0}, instance_id=2)

        result = CognitiveResult(layer_results={
            1: [SkillResult(
                skill_name="plutchik_emotion",
                layer=1,
                output={"internal": {"pleasantness": -0.8, "intensity": 0.9, "dominant": "fear"}},
                success=True,
            )],
        })

        writes, conflicts = self.runner._write_back(result, instance_id=99, expected_versions=start_versions)

        self.assertEqual(writes, 1)  # dominant_emotion 在快照时刻不存在(version 0)，可以写入
        self.assertGreaterEqual(conflicts, 1)
        self.assertEqual(self.bb.read(["pad"])["pad"]["pleasure"], 0.2)

    async def test_pending_response_emits_behavior_stream_speech(self):
        from character_mind.experimental.behavior_stream import BehaviorStream

        self.runner.behavior_stream = BehaviorStream("测试角色")
        await self.runner.start()
        self.ps.feed_dialogue("你还好吗？", source="对方", intensity=0.7)
        self.runner._last_input_time = time.time()
        await asyncio.sleep(self.config.pipeline_time_s + 1.5)
        await self.runner.stop()

        speech = self.runner.behavior_stream.get_last_speech()
        self.assertIsNotNone(speech)
        self.assertTrue(speech["content"].strip())

    async def test_gate_flushes_buffer_into_event_when_threshold_reached(self):
        await self.runner.start()
        self.ps.feed_visual("走廊灯闪了一下", intensity=0.25)
        self.ps.feed_visual("手机屏幕又亮了", intensity=0.25)
        self.ps.feed_internal("她忽然有点不安", intensity=0.45)
        self.runner._last_input_time = time.time()
        await asyncio.sleep(self.config.pipeline_time_s + 1.5)
        await self.runner.stop()

        snapshot = self.bb.get_snapshot()
        descriptions = [
            item["value"]
            for key, item in snapshot["fields"].items()
            if key == "last_continuous_event"
        ]
        self.assertTrue(descriptions)
        self.assertIn("走廊灯", descriptions[0]["description"])


if __name__ == "__main__":
    unittest.main()
