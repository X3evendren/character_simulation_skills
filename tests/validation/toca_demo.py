"""TOCA 端到端演示：连续状态流感知→分析→回应。"""
import sys, os, asyncio, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ['DEEPSEEK_API_KEY'] = 'REDACTED_API_KEY'
os.environ['DEEPSEEK_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', '')

from character_simulation_skills.core.blackboard import Blackboard
from character_simulation_skills.core.perception_stream import PerceptionStream
from character_simulation_skills.core.toca_runner import TocaRunner, TocaConfig
from character_simulation_skills.tests.validation.llm_provider import RealLLMProvider
from character_simulation_skills import get_orchestrator, get_registry
from character_simulation_skills.benchmark.run_benchmark import register_all_skills


async def main():
    # 初始化
    register_all_skills()
    bb = Blackboard()
    ps = PerceptionStream()
    provider = RealLLMProvider()

    cs = {
        "name": "林雨",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.4,
            "agreeableness": 0.55, "neuroticism": 0.75,
            "attachment_style": "anxious",
            "defense_style": ["投射"],
            "cognitive_biases": ["灾难化"],
            "moral_stage": 3,
        },
        "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"], "trauma_triggers": ["被忽视"]},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }

    config = TocaConfig(pipeline_time_s=12.0, instance_count=2, window_s=8.0)
    runner = TocaRunner(bb, ps, None, provider, cs, config)

    print("TOCA Demo: 连续状态流\n")
    print(f"Config: {config.instance_count} instances, {config.interval:.1f}s interval, {config.window_s}s window\n")

    # 模拟一段连续感知输入
    timeline = [
        (0.0, "visual", "手机屏幕亮了", 0.2, ""),
        (1.0, "visual", "不是他的消息，是广告推送", 0.3, ""),
        (2.0, "internal", "他在忙吗？", 0.5, ""),
        (3.0, "visual", "朋友圈刷到他发的照片，和其他人在一起", 0.7, ""),
        (3.5, "somatic", "胸口发紧，手指冰凉", 0.8, ""),
        (4.0, "internal", "他在和别人玩，没想过给我发消息", 0.7, ""),
        (6.0, "auditory", "手机终于响了——特殊铃声", 0.6, "手机"),
        (6.5, "visual", "是他的消息：'刚看到，怎么了'", 0.4, ""),
        (7.0, "internal", "我要怎么回？不能让他觉得我太粘人", 0.6, ""),
    ]

    # 启动 TOCA（在后台调度管道实例）
    await runner.start()
    t0 = time.time()

    # 按时间轴输入感知
    for t_offset, modality, content, intensity, source in timeline:
        await asyncio.sleep(max(0.1, t_offset - (time.time() - t0)))
        ps.feed(modality, content, intensity, source)
        # 同步到 Blackboard
        bb.append_perception({"t": time.time(), "modality": modality,
                              "content": content, "intensity": intensity, "source": source})
        print(f"  t={time.time()-t0:.1f}s [{modality}] {content[:50]}", flush=True)

    # 等待管道实例完成
    await asyncio.sleep(config.pipeline_time_s + 1)

    # 停止
    await runner.stop()

    # 结果
    stats = runner.stats()
    print(f"\n=== TOCA Stats ===")
    print(f"Instances: {stats['completed']}/{stats['total_instances']} completed")
    print(f"Tokens: {stats['total_tokens']}")
    print(f"Write success rate: {stats['write_success_rate']:.0%}")

    print(f"\n=== Blackboard State ===")
    state = bb.read()
    for k, v in state.items():
        if k not in ("perception_stream",):
            print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:100]}")

    resp = runner.get_latest_response()
    if resp:
        print(f"\n=== Character Response ===")
        print(f"  {resp['text'][:200]}")

asyncio.run(main())
