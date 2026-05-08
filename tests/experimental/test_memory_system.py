"""记忆系统测试 — 五级代谢 + 体验场 + Skills 代谢 + 噪音管理。"""
from __future__ import annotations

import time
import unittest

from character_mind.experimental.memory_metabolism import MemoryMetabolism, MemoryEntry
from character_mind.experimental.experiential_field import (
    ExperientialField, RetentionBuffer, ProtentionSpread, workspace_to_dict,
)
from character_mind.experimental.skill_metabolism import SkillMetabolism, SkillTracker
from character_mind.experimental.noise_manager import NoiseManager


class TestMemoryMetabolism(unittest.TestCase):
    def setUp(self):
        self.mm = MemoryMetabolism()
        self.mm.core_identity_keywords = ["被抛弃", "不被选择"]

    def test_ingest_to_working(self):
        entry = self.mm.ingest("陈风两小时没回消息", {"fear": 0.7}, 0.6, ["social"])
        self.assertEqual(entry.tier, "working")
        self.assertEqual(len(self.mm.working), 1)

    def test_metabolize_working_to_short(self):
        self.mm.ingest("感到被忽视", {"fear": 0.6}, 0.5)
        self.mm.metabolize()
        # 情感强度>0.4 应升级到 short
        self.assertEqual(len(self.mm.working), 0)
        self.assertEqual(len(self.mm.short_term), 1)
        self.assertEqual(self.mm.short_term[0].tier, "short")

    def test_low_significance_stays_in_working(self):
        self.mm.ingest("普通的一天", {"neutral": 0.1}, 0.1)
        self.mm.metabolize()
        # 低显著低情感 → 留在 working
        self.assertEqual(len(self.mm.working), 1)

    def test_recall_tracking(self):
        entry = self.mm.ingest("重要事件", {"fear": 0.8}, 0.7)
        self.mm.metabolize()  # → short
        for _ in range(3):
            self.mm.recall(entry.memory_id)
        self.mm.metabolize()  # recall_count=3 → long
        self.assertEqual(len(self.mm.long_term), 1)

    def test_core_related_promotes_to_long(self):
        self.mm.ingest("他让我感受到被抛弃的恐惧", {"fear": 0.9}, 0.8)
        self.mm.metabolize()  # → short (情感>0.4), then core_related → long
        self.assertEqual(len(self.mm.long_term), 1)

    def test_core_identity_promotes_to_core(self):
        entry = self.mm.ingest("又一次被抛弃和不被选择", {"sadness": 0.9}, 0.9)
        self.mm.metabolize()  # → short then → long (core related)
        for _ in range(5):
            self.mm.recall(entry.memory_id)
        self.mm.metabolize()  # recall≥5 + core_match≥2 → core
        self.assertEqual(len(self.mm.core), 1)
        self.assertTrue(self.mm.core[0].pointer_in_index)

    def test_memory_index_is_pointer_only(self):
        self.mm.ingest("核心记忆内容", {"fear": 0.9}, 0.9)
        entry2 = self.mm.ingest("核心记忆内容2", {"sadness": 0.9}, 0.9)
        self.mm.metabolize()
        for _ in range(5):
            self.mm.recall(entry2.memory_id)
        self.mm.metabolize()
        idx = self.mm.build_memory_index()
        # 指针格式: {id} | {title} | {emotional_tag} | {time}
        for line in idx.split("\n"):
            if line.startswith("- ["):
                self.assertIn("|", line)
                self.assertLess(len(line), 150)  # 每行短

    def test_timeline_search(self):
        self.mm.ingest("事件A", {"fear": 0.5}, 0.5)
        self.mm.ingest("事件B", {"joy": 0.5}, 0.5)
        now = time.time()
        results = self.mm.search_by_time(now - 10, now + 10)
        self.assertEqual(len(results), 2)

    def test_noise_ratio(self):
        self.mm.ingest("无聊的事", {"neutral": 0.1}, 0.1)  # 低显著 → 噪音
        self.mm.ingest("重要的", {"fear": 0.8}, 0.8)        # 非噪音
        ratio = self.mm.noise_ratio()
        self.assertGreater(ratio, 0.0)

    def test_growth_log_generates(self):
        # 直接模拟触发条件: 手动推入 long→core 晋升
        self.mm.growth_log.append({"t": time.time(), "what_i_learned": "学到了新东西", "how_i_changed": "变了一些"})
        self.assertGreater(len(self.mm.growth_log), 0)
        gl = self.mm.build_growth_log()
        self.assertIn("Growth Log", gl)


class TestExperientialField(unittest.TestCase):
    def setUp(self):
        self.ef = ExperientialField()

    def test_retention_pushes_old_impression(self):
        ws1 = [{"kind": "emotion", "content": "fear", "salience": 0.8, "source": "l1"}]
        ws2 = [{"kind": "emotion", "content": "anger", "salience": 0.6, "source": "l1"}]
        self.ef.tick(ws1)  # 第一帧: 设置 current_impression (无旧印象可推)
        self.ef.tick(ws2)  # 第二帧: ws1 被推入 retention
        self.assertGreater(len(self.ef.retention.items), 0)

    def test_retention_decays(self):
        self.ef.retention.push("快乐的感觉", 1.0, "test")
        # 手动推进时间戳来触发衰减
        self.ef.retention.items[0].timestamp -= 10  # 10秒前
        initial_weight = self.ef.retention.items[0].weight
        self.ef.retention.tick()
        self.assertLess(self.ef.retention.items[0].weight, initial_weight)

    def test_retention_format_output(self):
        self.ef.retention.push("刚刚的担心还在回响", 0.8, "workspace", "fear")
        formatted = self.ef.retention.format_for_context()
        self.assertIn("刚刚过去的还在回响", formatted)

    def test_protention_samples_futures(self):
        self.ef.protention.update_trend({"pleasure": -0.5}, {"pleasure": -0.2})
        samples = self.ef.protention.sample_futures({"pleasure": -0.5})
        self.assertEqual(len(samples), 5)

    def test_protention_openness(self):
        self.ef.protention.update_trend({"pleasure": 0.1}, {"pleasure": 0.0})
        score = self.ef.protention.openness_score()
        self.assertGreaterEqual(score, 0.0)


class TestSkillMetabolism(unittest.TestCase):
    def setUp(self):
        self.sm = SkillMetabolism()

    def test_register_and_record(self):
        self.sm.register("big_five_analysis", 0)
        self.sm.record("big_five_analysis", 300, True, 0.8)
        self.assertEqual(self.sm.trackers["big_five_analysis"].activation_count, 1)

    def test_flags_30_days_inactive(self):
        self.sm.register("old_skill", 0)
        self.sm.trackers["old_skill"].last_activated = time.time() - 31 * 86400
        report = self.sm.run_metabolism()
        self.assertIn("old_skill", " ".join(report["flagged"]))

    def test_detects_overlap(self):
        self.sm.register("skill_a", 1)
        self.sm.register("skill_b", 1)
        # 先激活两个 skill 避免被 "30天未激活" 先标 FLAGGED
        self.sm.record("skill_a", 100, True, 0.8)
        self.sm.record("skill_b", 100, True, 0.8)
        self.sm.update_overlap("skill_a", "skill_b", 0.8)
        report = self.sm.run_metabolism()
        self.assertGreater(len(report["merge_candidates"]), 0)


class TestNoiseManager(unittest.TestCase):
    def test_aggregates_noise(self):
        mm = MemoryMetabolism()
        mm.ingest("噪音事件", {"neutral": 0.05}, 0.1)
        mm.ingest("重要事件", {"fear": 0.9}, 0.8)
        nm = NoiseManager(memory_metabolism=mm)
        report = nm.report()
        self.assertIn("total_noise_ratio", report)

    def test_format_for_agent(self):
        mm = MemoryMetabolism()
        mm.ingest("噪音", {"neutral": 0.05}, 0.1)
        nm = NoiseManager(memory_metabolism=mm)
        text = nm.format_for_agent()
        self.assertIn("噪音报告", text)
