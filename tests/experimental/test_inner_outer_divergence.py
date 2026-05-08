"""内/外分叉测试 — 内部体验与外部表达分离。"""
from __future__ import annotations

import unittest

from character_mind.experimental.inner_experience import InnerExperienceStream
from character_mind.experimental.expression_policy import ExpressionPolicy


class TestInnerExperienceStream(unittest.TestCase):
    def test_records_private_belief_and_forbidden_wish(self):
        stream = InnerExperienceStream(max_items=5)
        item = stream.append(
            kind="private_belief",
            content="他不回消息可能是想离开我",
            intensity=0.8,
            source="self_model",
            expressible=False,
        )

        self.assertEqual(item["kind"], "private_belief")
        self.assertFalse(item["expressible"])
        self.assertEqual(stream.recent(1)[0]["content"], "他不回消息可能是想离开我")

    def test_trace_for_context_hides_unexpressible_content_by_default(self):
        stream = InnerExperienceStream(max_items=5)
        stream.append("felt_emotion", "fear", 0.7, "l1", True)
        stream.append("forbidden_wish", "希望他立刻证明他还在乎我", 0.9, "self_model", False)

        public_context = stream.format_for_context(include_private=False)
        private_context = stream.format_for_context(include_private=True)

        self.assertIn("fear", public_context)
        self.assertNotIn("立刻证明", public_context)
        self.assertIn("立刻证明", private_context)

    def test_records_inner_outer_divergence(self):
        stream = InnerExperienceStream(max_items=10)
        record = stream.record_divergence(
            inner={"kind": "forbidden_wish", "content": "不要离开我", "intensity": 0.9},
            outer={"type": "speech", "content": "没事，你忙吧。"},
            mechanism="masking",
        )

        self.assertEqual(record["mechanism"], "masking")
        self.assertIn("不要离开", record["inner"]["content"])
        self.assertIn("没事", record["outer"]["content"])


class TestExpressionPolicy(unittest.TestCase):
    def test_masks_unexpressible_wish_into_cold_speech(self):
        policy = ExpressionPolicy()
        inner_items = [
            {
                "kind": "forbidden_wish",
                "content": "不要离开我，快证明你还在乎我",
                "intensity": 0.9,
                "expressible": False,
            }
        ]
        self_model = {
            "active_mask": "装作无所谓，用短句保护自尊。",
            "private_intention": "希望对方主动解释并确认关系仍然安全。",
        }

        result = policy.compose(inner_items, self_model, proposed_text="你为什么不回我？")

        self.assertEqual(result["mechanism"], "masking")
        self.assertNotIn("不要离开", result["outer"]["content"])
        self.assertTrue(result["omitted"])

    def test_allows_expressible_emotion_to_pass(self):
        policy = ExpressionPolicy()
        result = policy.compose(
            [{"kind": "felt_emotion", "content": "fear", "intensity": 0.4, "expressible": True}],
            {},
            proposed_text="我有点不安。",
        )

        self.assertEqual(result["outer"]["content"], "我有点不安。")
        self.assertEqual(result["mechanism"], "direct_expression")
