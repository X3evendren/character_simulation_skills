"""TOCA 双角色连续对话演示。

两个角色（焦虑型 × 回避型）在连续流中对话。
每个角色有自己的 Blackboard + PerceptionStream + TocaRunner。
当一方说话时，另一方将其作为感知输入。

用法:
    python tests/validation/toca_dialogue_demo.py
"""
import sys, os, asyncio, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ['DEEPSEEK_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'REDACTED_API_KEY')

from character_mind.core.blackboard import Blackboard
from character_mind.core.perception_stream import PerceptionStream
from character_mind.core.behavior_stream import BehaviorStream
from character_mind.core.toca_runner import TocaRunner, TocaConfig
from character_mind.tests.validation.llm_provider import RealLLMProvider
from character_mind import get_orchestrator, get_registry
from character_mind.benchmark.run_benchmark import register_all_skills


def make_char(name, neuroticism, agreeableness, attachment, defense, biases):
    return {
        "name": name,
        "personality": {
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": agreeableness, "neuroticism": neuroticism,
            "attachment_style": attachment, "defense_style": defense,
            "cognitive_biases": biases, "moral_stage": 3,
        },
        "trauma": {"ace_score": 2, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }


async def main():
    register_all_skills()
    provider = RealLLMProvider()

    # 两个角色
    anxious_cs = make_char("林雨", 0.75, 0.7, "anxious", ["投射"], ["灾难化", "读心术"])
    avoidant_cs = make_char("陈风", 0.45, 0.35, "avoidant", ["情感隔离", "理智化"], [])

    anxious_bb = Blackboard()
    avoidant_bb = Blackboard()
    anxious_ps = PerceptionStream()
    avoidant_ps = PerceptionStream()
    anxious_bs = BehaviorStream("林雨")
    avoidant_bs = BehaviorStream("陈风")

    config = TocaConfig(pipeline_time_s=12.0, instance_count=2, window_s=15.0)

    orch_a = get_orchestrator(anti_alignment_enabled=True)
    orch_b = get_orchestrator(anti_alignment_enabled=True)

    runner_a = TocaRunner(anxious_bb, anxious_ps, orch_a, provider, anxious_cs, config)
    runner_b = TocaRunner(avoidant_bb, avoidant_ps, orch_b, provider, avoidant_cs, config)

    print("TOCA 双角色连续对话\n")

    # 初始场景
    initial_event = "你们已经三天没有好好说话了。林雨一直在等陈风主动联系。此刻两人都在客厅里。"
    anxious_ps.feed_dialogue(initial_event, "场景")
    avoidant_ps.feed_dialogue(initial_event, "场景")

    await runner_a.start()
    await runner_b.start()
    t0 = time.time()

    dialogue_rounds = []
    last_speaker = None

    for round_num in range(4):
        # 等待管道实例产出回应
        await asyncio.sleep(config.pipeline_time_s + 2)

        # 检查两人是否有新回应
        for name, runner, bb, bs in [
            ("林雨", runner_a, anxious_bb, anxious_bs),
            ("陈风", runner_b, avoidant_bb, avoidant_bs),
        ]:
            resp = runner.get_latest_response()
            if resp and resp.get("text", "").strip():
                text = resp["text"].strip()
                # 避免同一个人连续说话
                if last_speaker != name:
                    bs.emit("speech", text, target="陈风" if name == "林雨" else "林雨")
                    elapsed = int(time.time() - t0)
                    print(f"  [{elapsed}s] {name}: {text[:120]}")
                    last_speaker = name
                    dialogue_rounds.append({"speaker": name, "text": text, "t": elapsed})

                    # 对方将此作为感知输入
                    if name == "林雨":
                        avoidant_ps.feed_dialogue(text, source="林雨")
                        avoidant_bb.append_perception({
                            "t": time.time(), "modality": "dialogue",
                            "content": text, "intensity": 0.7, "source": "林雨",
                        })
                    else:
                        anxious_ps.feed_dialogue(text, source="陈风")
                        anxious_bb.append_perception({
                            "t": time.time(), "modality": "dialogue",
                            "content": text, "intensity": 0.7, "source": "陈风",
                        })
                    break

    await runner_a.stop()
    await runner_b.stop()

    # 报告
    print(f"\n=== 对话记录 ({len(dialogue_rounds)} 轮) ===")
    for r in dialogue_rounds:
        print(f"  {r['speaker']}: {r['text'][:150]}")

    stats_a = runner_a.stats()
    stats_b = runner_b.stats()
    print(f"\n林雨: {stats_a['completed']} 实例, {stats_a['total_tokens']} tokens")
    print(f"陈风: {stats_b['completed']} 实例, {stats_b['total_tokens']} tokens")
    print(f"总计: {stats_a['total_tokens'] + stats_b['total_tokens']} tokens")

    state_a = anxious_bb.read()
    state_b = avoidant_bb.read()
    print(f"\n林雨状态: 情绪={state_a.get('dominant_emotion','?')}, pad={state_a.get('pad','?')}")
    print(f"陈风状态: 情绪={state_b.get('dominant_emotion','?')}, pad={state_b.get('pad','?')}")

asyncio.run(main())
