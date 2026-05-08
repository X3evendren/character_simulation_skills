"""爱情状态 + 反馈闭环 测试。"""
from __future__ import annotations

import time
import unittest

from character_mind.experimental.love_state import LoveState
from character_mind.experimental.feedback_loop import FeedbackLoop
from character_mind.experimental.memory_metabolism import MemoryMetabolism


class TestLoveState(unittest.TestCase):
    def setUp(self):
        self.ls = LoveState()

    def test_default_inactive(self):
        self.assertFalse(self.ls.active)
        self.assertEqual(self.ls.stage, "none")

    def test_activate_attraction(self):
        self.ls.activate_love("角色A", "attraction")
        self.assertTrue(self.ls.active)
        self.assertEqual(self.ls.target_id, "角色A")
        # DA 应升高
        self.assertGreater(self.ls.neurotransmitter_modulation["DA"], 0.3)
        # 5-HT 应下降
        self.assertLess(self.ls.neurotransmitter_modulation["5HT"], 0)
        # PFC 抑制
        self.assertGreater(self.ls.pfc_inhibition["critical_judgment"], 0.3)

    def test_activate_attachment(self):
        self.ls.activate_love("角色B", "attachment")
        # 催产素为主
        self.assertGreater(self.ls.neurotransmitter_modulation["OXT"], 0.4)
        # PFC 抑制较弱
        self.assertLess(self.ls.pfc_inhibition["critical_judgment"], 0.2)

    def test_deactivate_resets(self):
        self.ls.activate_love("角色A", "attraction")
        self.ls.deactivate_love()
        self.assertFalse(self.ls.active)
        self.assertEqual(self.ls.stage, "none")
        self.assertEqual(self.ls.target_id, "")

    def test_stage_transition_lust_to_attraction(self):
        self.ls.activate_love("角色A", "lust")
        # 模拟 31 天
        for _ in range(31):
            self.ls.tick(86400)  # 每天 tick
        self.assertEqual(self.ls.stage, "attraction")

    def test_attraction_blends_to_attachment(self):
        self.ls.activate_love("角色A", "attraction")
        # 模拟 200 天
        for _ in range(200):
            self.ls.tick(86400)
        self.assertGreater(self.ls.attachment_transition, 0.05)
        self.assertGreater(self.ls.neurotransmitter_modulation["OXT"], 0.1)


class TestFeedbackLoop(unittest.TestCase):
    def setUp(self):
        self.fl = FeedbackLoop()
        self.mm = MemoryMetabolism()

    def test_record_feedback(self):
        self.fl.record_feedback(
            {"type": "speech", "content": "没事，你忙吧。"},
            "对方沉默了更久", -0.6,
        )
        self.assertEqual(len(self.fl._feedback_buffer), 1)

    def test_extract_patterns_requires_min_occurrences(self):
        for _ in range(3):
            self.fl.record_feedback(
                {"type": "speech", "content": "没事。"},
                "对方失望", -0.5,
            )
        patterns = self.fl.extract_patterns()
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["trigger"], "没事。")

    def test_solidify_high_confidence_pattern(self):
        for _ in range(8):  # 需要 count>=5 AND confidence>=0.7 (=count/10, so need 7+)
            self.fl.record_feedback(
                {"type": "speech", "content": "行吧。"},
                "对方接受了", 0.7,
            )
        self.fl.extract_patterns()
        solidified = self.fl.solidify_knowledge(self.mm)
        self.assertGreater(solidified, 0)

    def test_generate_growth_diary(self):
        for _ in range(8):
            self.fl.record_feedback(
                {"type": "speech", "content": "好。"},
                "对方满意", 0.6,
            )
        diary = self.fl.generate_growth_diary(self.mm)
        self.assertIsNotNone(diary)
