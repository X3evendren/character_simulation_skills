"""意识工作空间测试 — 预测误差驱动显著性 + 有限全局工作空间。"""
from __future__ import annotations

import unittest

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.consciousness import ConsciousnessLayer


class TestConsciousWorkspace(unittest.TestCase):
    def test_prediction_error_increases_emotion_salience(self):
        bb = Blackboard()
        bb.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0})
        bb.write("dominant_emotion", "neutral")
        layer = ConsciousnessLayer(bb)

        layer.predict_next()
        bb.write("pad", {"pleasure": -0.8, "arousal": 0.9, "dominance": -0.2})
        layer.compute_prediction_error()
        salience = layer.score_salience()

        self.assertGreater(salience["emotion"], 0.55)

    def test_workspace_keeps_only_highest_salience_items(self):
        bb = Blackboard()
        layer = ConsciousnessLayer(bb)
        layer.workspace_capacity = 3

        items = [
            {"kind": "emotion", "content": "fear", "salience": 0.7, "source": "l1"},
            {"kind": "memory", "content": "old abandonment", "salience": 0.9, "source": "wm_ltm"},
            {"kind": "intention", "content": "ask why", "salience": 0.6, "source": "self_model"},
            {"kind": "noise", "content": "street light", "salience": 0.1, "source": "visual"},
        ]

        selected = layer.update_workspace(items)

        self.assertEqual(len(selected), 3)
        self.assertEqual(selected[0]["kind"], "memory")
        self.assertNotIn("noise", [item["kind"] for item in selected])
        self.assertEqual(bb.read(["conscious_workspace"])["conscious_workspace"], selected)
