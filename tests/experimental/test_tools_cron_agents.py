"""工具系统 + 多Agent + Cron 测试"""
from __future__ import annotations

import os
import sys
import time
import tempfile
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.core.tools import (
    ToolRegistry, ToolDescriptor, ToolAvailability, ToolExecutorKind,
    TrustLevel, build_default_tool_registry,
)
from character_mind.core.multi_agent import AgentRegistry, AgentMessage
from character_mind.core.cron import CronScheduler, CronJob


class TestToolSystem(unittest.TestCase):
    def setUp(self):
        self.registry = build_default_tool_registry()

    def test_default_registry_has_tools(self):
        self.assertGreater(len(self.registry._tools), 0)

    def test_bash_only_for_owner(self):
        available = self.registry.list_available(TrustLevel.OWNER, {"auth_enabled": True}, is_sandboxed=True)
        names = [t.name for t in available]
        self.assertIn("bash", names)

    def test_bash_blocked_for_guest(self):
        available = self.registry.list_available(TrustLevel.GUEST, {})
        names = [t.name for t in available]
        self.assertNotIn("bash", names)

    def test_file_read_available_for_approved(self):
        available = self.registry.list_available(TrustLevel.APPROVED, {})
        names = [t.name for t in available]
        self.assertIn("file_read", names)

    def test_bash_blocked_without_sandbox(self):
        available = self.registry.list_available(TrustLevel.OWNER, {}, is_sandboxed=False)
        names = [t.name for t in available]
        self.assertNotIn("bash", names)  # sandbox_only

    def test_session_tools_always_available(self):
        available = self.registry.list_available(TrustLevel.GUEST, {})
        names = [t.name for t in available]
        for st in ["sessions_list", "sessions_send"]:
            self.assertIn(st, names)

    def test_build_tool_prompt(self):
        prompt = self.registry.build_tool_prompt(TrustLevel.OWNER, {"auth_enabled": True}, True)
        self.assertIn("可用工具", prompt)

    def test_parallel_safe_tools(self):
        safe = self.registry.get_parallel_safe()
        self.assertIn("file_read", safe)
        self.assertNotIn("bash", safe)


class TestMultiAgent(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()

    def test_register_and_list(self):
        self.registry.register("agent_a", object())
        self.registry.register("agent_b", object())
        self.assertIn("agent_a", self.registry.list_agents())

    def test_send_message(self):
        self.registry.register("a", object())
        self.registry.register("b", object())
        msg = self.registry.send("a", "b", "hello")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.from_agent, "a")
        self.assertEqual(msg.content, "hello")

    def test_unregister(self):
        self.registry.register("x", object())
        self.registry.unregister("x")
        self.assertNotIn("x", self.registry.list_agents())

    def test_messages_filtered_by_agent(self):
        self.registry.messages = [
            AgentMessage("a", "b", "hi", message_type="text"),
            AgentMessage("c", "a", "hello", message_type="text"),
        ]
        for_a = self.registry.get_messages_for("a")
        self.assertEqual(len(for_a), 2)

    def test_to_dict(self):
        self.registry.register("test", object())
        d = self.registry.to_dict()
        self.assertIn("test", d["agents"])


class TestCron(unittest.TestCase):
    def test_add_job(self):
        sched = CronScheduler()
        sched.add_job("daily_report", "3600", "生成日报", {"name": "test"})
        self.assertIn("daily_report", sched.jobs)

    def test_remove_job(self):
        sched = CronScheduler()
        sched.add_job("x", "60", "test", {})
        sched.remove_job("x")
        self.assertNotIn("x", sched.jobs)

    def test_parse_interval_star(self):
        sched = CronScheduler()
        self.assertEqual(sched._parse_interval("*/30"), 30.0)

    def test_parse_interval_number(self):
        sched = CronScheduler()
        self.assertEqual(sched._parse_interval("120"), 120.0)

    def test_parse_hourly(self):
        sched = CronScheduler()
        self.assertEqual(sched._parse_interval("hourly"), 3600.0)

    def test_job_save_load(self):
        with tempfile.TemporaryDirectory() as d:
            sched = CronScheduler(d)
            sched.add_job("test", "60", "test prompt", {"name": "char"})
            sched.save_jobs()
            # 新 scheduler 加载
            s2 = CronScheduler(d)
            s2.load_jobs()
            self.assertIn("test", s2.jobs)
