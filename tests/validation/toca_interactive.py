"""TOCA 交互式对话 — 和拥有持续心理状态的角色聊天。

角色的心理状态在后台持续流动。你说话时、沉默时、打字时，
角色都在感受和变化。不只是等你输入才"想"。

用法:
    python tests/validation/toca_interactive.py

输入 /quit 退出, /state 查看角色当前心理状态。
"""
import sys, os, asyncio, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ['DEEPSEEK_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'REDACTED_API_KEY')

from character_mind.core.blackboard import Blackboard
from character_mind.core.perception_stream import PerceptionStream
from character_mind.core.behavior_stream import BehaviorStream
from character_mind.core.toca_runner import TocaRunner, TocaConfig
from character_mind.tests.validation.llm_provider import RealLLMProvider
from character_mind import get_orchestrator
from character_mind.benchmark.run_benchmark import register_all_skills


async def run_continuous_state(runner, ps, bb, interval: float):
    """后台持续更新角色心理状态。即使没有外部输入，内部状态也在流动。"""
    while True:
        # 注入一个"时间流逝"的感知——角色在等待、在感受时间的流动
        ps.feed_internal("时间在流逝...", intensity=0.15)
        bb.append_perception({
            "t": time.time(), "modality": "internal",
            "content": "时间在流逝...", "intensity": 0.15, "source": "",
        })
        await asyncio.sleep(interval)


async def main():
    register_all_skills()
    provider = RealLLMProvider()

    # 创建一个角色
    character_state = {
        "name": "林雨",
        "personality": {
            "openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.45,
            "agreeableness": 0.7, "neuroticism": 0.75,
            "attachment_style": "anxious",
            "defense_style": ["投射", "合理化"],
            "cognitive_biases": ["灾难化", "读心术"],
            "moral_stage": 3,
        },
        "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"],
                   "trauma_triggers": ["被忽视", "被拒绝"]},
        "ideal_world": {"ideal_self": "被坚定选择的人"},
        "motivation": {"current_goal": "想要确认自己是被在乎的"},
        "emotion_decay": {},
    }

    bb = Blackboard()
    ps = PerceptionStream()
    bs = BehaviorStream("林雨")
    config = TocaConfig(pipeline_time_s=12.0, instance_count=2, window_s=20.0)
    orch = get_orchestrator(anti_alignment_enabled=True)
    runner = TocaRunner(bb, ps, orch, provider, character_state, config)

    # 初始场景
    ps.feed_internal("你在等待。不知道对方什么时候会来消息。", intensity=0.3)

    await runner.start()

    # 启动后台状态流动——每8秒注入一次时间流逝感知
    bg_task = asyncio.create_task(run_continuous_state(runner, ps, bb, 8.0))

    print("\n林雨正在等待...（她的心理状态在后台持续流动）")
    print("输入 /quit 退出, /state 查看状态\n")

    try:
        while True:
            # 读取用户输入
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("你: "))

            if not user_input:
                continue
            if user_input == "/quit":
                break
            if user_input == "/state":
                state = bb.read()
                print(f"  情绪: {state.get('dominant_emotion', '?')}")
                pad = state.get('pad', {})
                print(f"  愉悦:{pad.get('pleasure',0):.1f} 唤醒:{pad.get('arousal',0):.1f}")
                defense = state.get('active_defense', {})
                if defense:
                    print(f"  防御: {defense.get('name','?')}")
                continue

            # 用户输入作为感知注入
            ps.feed_dialogue(user_input, source="你")
            bb.append_perception({
                "t": time.time(), "modality": "dialogue",
                "content": user_input, "intensity": 0.8, "source": "你",
            })

            # 等待角色的回应从连续流中自然产生
            print("林雨: ", end="", flush=True)
            last_text = ""
            waited = 0
            while waited < 25:
                await asyncio.sleep(2)
                waited += 2
                resp = runner.get_latest_response()
                if resp and resp.get("text", "").strip():
                    text = resp["text"].strip()
                    if text != last_text and len(text) > 3:
                        bs.emit("speech", text, target="你")
                        print(text)
                        break
                print(".", end="", flush=True)
            else:
                # 超时——角色选择沉默
                bs.emit("silence", "", target="你")
                print("（沉默）")

    finally:
        bg_task.cancel()
        await runner.stop()
        print(f"\n对话结束。状态已保存。")


asyncio.run(main())
