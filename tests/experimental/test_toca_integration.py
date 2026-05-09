"""核心模块测试 — Blackboard, ThalamicGate, ConsciousnessLayer"""
from __future__ import annotations

import os
import sys
import time
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.thalamic_gate import ThalamicGate
from character_mind.experimental.consciousness import ConsciousnessLayer


class TestBlackboard(unittest.TestCase):
    """Blackboard 版本化读写 + 乐观锁。"""

    def test_basic_write_read(self):
        bb = Blackboard()
        bb.write("pad", {"pleasure": -0.2, "arousal": 0.5}, instance_id=1)
        data = bb.read(["pad"])
        self.assertEqual(data["pad"]["pleasure"], -0.2)

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
        ok = bb.try_write("x", 30, expected_version=0, instance_id=2)
        self.assertFalse(ok)
        self.assertEqual(bb.read(["x"])["x"], 10)

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


class TestConsciousnessLayer(unittest.TestCase):
    """意识层: GWT + 预测加工。"""

    def setUp(self):
        self.bb = Blackboard()
        self.bb.write("pad", {"pleasure": -0.2, "arousal": 0.5})
        self.bb.write("dominant_emotion", "neutral")
        self.cl = ConsciousnessLayer(self.bb)

    def test_predict_next_cold_start(self):
        p = self.cl.predict_next()
        self.assertIn("L1_pad", p)

    def test_ewma_smoothes_shift(self):
        self.cl.predict_next()
        self.bb.write("pad", {"pleasure": -0.8, "arousal": 0.9})
        p = self.cl.predict_next()
        self.assertGreater(p["L1_pad"]["pleasure"], -0.8)

    def test_adaptive_alpha_decreases_with_volatility(self):
        for v in [-0.2, -0.6, -0.1, -0.7, -0.3]:
            self.bb.write("pad", {"pleasure": v, "arousal": 0.5})
            self.cl.predict_next()
        alpha = self.cl._adaptive_alpha("pleasure")
        self.assertLess(alpha, 0.3)

    def test_compute_prediction_error(self):
        self.cl.predict_next()
        self.bb.write("pad", {"pleasure": -0.5, "arousal": 0.7})
        errors = self.cl.compute_prediction_error()
        self.assertIn("L1_combined", errors)

    def test_self_perceive_generates_text(self):
        perception = self.cl.self_perceive(force=True)
        self.assertIsInstance(perception, str)
        self.assertGreater(len(perception), 3)

    def test_filter_broadcast_decisions(self):
        self.bb.write("dominant_emotion", "fear")
        self.bb.write("pad", {"pleasure": -0.5, "arousal": 0.8})
        decisions = self.cl.filter_broadcast()
        self.assertIsInstance(decisions["emotion"], bool)


if __name__ == "__main__":
    unittest.main()
