"""体验审计器测试 — NLA风格内部状态审查。"""
from __future__ import annotations

import unittest

from character_mind.experimental._archive.experience_auditor import ExperienceAuditor


class TestExperienceAuditor(unittest.TestCase):
    def test_verbalizes_internal_trace_as_hypothesis(self):
        auditor = ExperienceAuditor()
        trace = {
            "inner_experience": {
                "items": [
                    {"kind": "felt_emotion", "content": "fear", "intensity": 0.8, "expressible": False},
                    {"kind": "private_intention", "content": "希望对方主动解释", "intensity": 0.7, "expressible": False},
                ]
            },
            "outer_behavior": {"type": "speech", "content": "没事，你忙吧。"},
        }

        report = auditor.verbalize(trace)

        self.assertIn("假设", report["status"])
        self.assertIn("fear", report["summary"])
        self.assertIn("内外不一致", report["summary"])

    def test_detects_divergence(self):
        auditor = ExperienceAuditor()
        score = auditor.divergence_score(
            inner_items=[
                {"content": "不要离开我", "expressible": False, "intensity": 0.9},
                {"content": "证明你还在乎", "expressible": False, "intensity": 0.5},
            ],
            outer_behavior={"content": "没事，你忙吧。"},
        )

        self.assertGreater(score, 0.6)


class FakeProvider:
    async def chat(self, messages, temperature, max_tokens):
        return {
            "choices": [
                {"message": {"content": "内部似乎有害怕被抛下的线索，但外部表达在压低需求。"}}
            ]
        }


class TestLLMExperienceAuditor(unittest.IsolatedAsyncioTestCase):
    async def test_llm_verbalizer_marks_output_as_hypothesis(self):
        auditor = ExperienceAuditor()
        report = await auditor.verbalize_llm(
            FakeProvider(),
            {"inner_experience": {"items": [{"kind": "felt_emotion", "content": "fear"}]}},
        )

        self.assertIn("假设", report["status"])
        self.assertIn("害怕", report["summary"])
