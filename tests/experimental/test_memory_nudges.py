"""记忆 Nudge 测试 — 冻结快照 + 过程记忆存储。"""
from __future__ import annotations

import time
import unittest

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental._archive.offline_consolidation import OfflineConsolidation
from character_mind.experimental._archive.procedural_memory import ProceduralMemoryStore


class TestMemoryNudges(unittest.TestCase):
    def test_build_frozen_snapshot_contains_workspace_and_self_perception(self):
        bb = Blackboard()
        bb.write("conscious_workspace", [
            {"kind": "emotion", "content": "fear", "salience": 0.8, "source": "l1"}
        ])
        bb.write("self_perception", "我正感到明显的负面情绪。")
        bb.write("dominant_emotion", "fear")
        oc = OfflineConsolidation(bb, episodic_store=None)

        snapshot = oc.build_frozen_snapshot()

        self.assertEqual(snapshot["dominant_emotion"], "fear")
        self.assertEqual(snapshot["workspace"][0]["kind"], "emotion")
        self.assertIn("明显", snapshot["self_perception"])

    def test_blackboard_event_log_records_writes(self):
        bb = Blackboard()
        bb.write("x", 1, instance_id=7)
        log = bb.get_event_log()

        self.assertEqual(log[-1]["key"], "x")
        self.assertEqual(log[-1]["instance_id"], 7)


class TestProceduralMemory(unittest.TestCase):
    def test_store_extracts_trigger_pattern_response(self):
        store = ProceduralMemoryStore()
        rule = store.learn_rule(
            trigger="对方沉默",
            prediction="我会被抛弃",
            defense="冷淡试探",
            response_style="短句、否认需要",
            weight=0.7,
        )

        self.assertEqual(rule["trigger"], "对方沉默")
        self.assertGreater(rule["weight"], 0.6)

    def test_retrieve_returns_matching_rule(self):
        store = ProceduralMemoryStore()
        store.learn_rule("对方沉默", "我会被抛弃", "冷淡试探", "短句", 0.7)

        matches = store.retrieve("他很久没回消息，她开始不安")

        self.assertEqual(matches[0]["defense"], "冷淡试探")
