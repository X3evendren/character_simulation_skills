"""TOCA 单人连续流自动化测试。"""
import sys, os, asyncio, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from character_mind.core.blackboard import Blackboard
from character_mind.core.perception_stream import PerceptionStream
from character_mind.core.toca_runner import TocaRunner, TocaConfig
from character_mind.tests.validation.llm_provider import RealLLMProvider
from character_mind import get_orchestrator


async def test():
    # 内置 Skill 自动注册 via get_orchestrator() -> get_registry() -> _register_builtin_skills()
    provider = RealLLMProvider()

    cs = {
        "name": "林雨",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.45,
            "agreeableness": 0.7, "neuroticism": 0.75,
            "attachment_style": "anxious", "defense_style": ["投射"],
            "cognitive_biases": ["灾难化", "读心术"], "moral_stage": 3,
        },
        "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"],
                   "trauma_triggers": ["被忽视"]},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }

    bb = Blackboard()
    ps = PerceptionStream()
    config = TocaConfig(pipeline_time_s=12.0, instance_count=2, window_s=15.0)
    orch = get_orchestrator(anti_alignment_enabled=True)
    runner = TocaRunner(bb, ps, orch, provider, cs, config)

    pipeline_wait = 14  # DeepSeek pipeline takes ~12s

    # Phase 1: 等待
    ps.feed_internal("你在等他的消息。已经两小时了。", intensity=0.5)
    print("Phase 1: 等待中...")
    await runner.start()
    await asyncio.sleep(6)
    state0 = bb.read()
    print(f"  初始情绪: {state0.get('dominant_emotion','?')}", flush=True)

    # Phase 2: 收到消息
    ps.feed_dialogue("刚看到，抱歉啊——今天有点忙", source="陈风")
    bb.append_perception({"t": time.time(), "modality": "dialogue",
                          "content": "刚看到，抱歉啊——今天有点忙", "intensity": 0.8, "source": "陈风"})
    print("Phase 2: 收到消息，等待回应...", flush=True)
    await asyncio.sleep(pipeline_wait)

    # Poll for response
    for _ in range(5):
        resp = runner.get_latest_response()
        if resp and resp.get("text", "").strip():
            print(f"  回应: {resp['text'][:200]}", flush=True)
            break
        await asyncio.sleep(2)

    state = bb.read()
    print(f"  状态: 情绪={state.get('dominant_emotion','?')}, "
          f"愉悦={state.get('pad',{}).get('pleasure',0):.1f}", flush=True)

    # Phase 3: 内心怀疑
    ps.feed_internal("他说'有点忙'...是不是不想理我？", intensity=0.6)
    bb.append_perception({"t": time.time(), "modality": "internal",
                          "content": "他说'有点忙'...是不是不想理我？", "intensity": 0.6, "source": ""})
    print("Phase 3: 产生怀疑...", flush=True)
    await asyncio.sleep(pipeline_wait)

    for _ in range(5):
        resp2 = runner.get_latest_response()
        if resp2 and resp2.get("text", "").strip():
            print(f"  回应: {resp2['text'][:200]}", flush=True)
            break
        await asyncio.sleep(2)

    state2 = bb.read()
    print(f"  状态: 情绪={state2.get('dominant_emotion','?')}, "
          f"愉悦={state2.get('pad',{}).get('pleasure',0):.1f}", flush=True)

    await runner.stop()
    s = runner.stats()
    print(f"\n完成: {s['completed']} 实例, {s['total_tokens']} tokens")

asyncio.run(test())
