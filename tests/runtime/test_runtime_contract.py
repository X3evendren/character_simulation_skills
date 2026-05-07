import asyncio
import os
import sys
import time
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import create_runtime, get_orchestrator
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.core.episodic_memory import EpisodicMemory


class RuntimeContractTests(unittest.TestCase):
    def test_create_runtime_bootstraps_default_skills(self):
        runtime = create_runtime()
        self.assertGreater(runtime.registry.skill_count, 0)
        self.assertIn("big_five_analysis", runtime.registry)
        self.assertIn("response_generator", runtime.registry)

    def test_default_runtime_can_process_one_event(self):
        runtime = create_runtime()
        provider = MockProvider(quality=1.0, seed=7)
        character_state = {
            "personality": {
                "openness": 0.6,
                "conscientiousness": 0.5,
                "extraversion": 0.4,
                "agreeableness": 0.55,
                "neuroticism": 0.75,
                "attachment_style": "anxious",
            },
            "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": []},
            "emotion_decay": {},
            "personality_state_machine": {},
        }
        event = {
            "description": "他两个小时没有回消息。",
            "type": "social",
            "significance": 0.6,
            "participants": [{"name": "陈风", "relation": "partner"}],
        }

        result = asyncio.run(
            runtime.orchestrator.process_event(provider, character_state, event)
        )

        self.assertTrue(result.layer_results[0])
        self.assertTrue(result.layer_results[1])
        self.assertTrue(result.layer_results[2])
        self.assertTrue(result.layer_results[5])

    def test_create_runtime_isolates_mutable_state(self):
        first = create_runtime()
        second = create_runtime()

        first.episodic_store.store(EpisodicMemory(
            timestamp=time.time(),
            description="只属于 first 的记忆",
            emotional_signature={"anxiety": 0.7},
            significance=0.8,
            event_type="social",
        ))

        self.assertEqual(len(first.episodic_store), 1)
        self.assertEqual(len(second.episodic_store), 0)
        self.assertIsNot(first.orchestrator, second.orchestrator)

    def test_get_orchestrator_returns_a_fresh_runtime_instance(self):
        left = get_orchestrator()
        right = get_orchestrator()
        self.assertIsNot(left, right)
        self.assertIsNot(left.episodic_store, right.episodic_store)


if __name__ == "__main__":
    unittest.main()
