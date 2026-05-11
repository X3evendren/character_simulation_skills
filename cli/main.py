"""Character Mind v3 CLI — 完整集成聊天循环。

模块集成:
  PsychologyEngine → XML 分析 + parameter_shifts
  UnifiedParams → 32个统一参数
  ParamsModulator → Fast主导(activation跳变) + Slow修正(baseline微调)
  Love Engine → Oath + Saturation + PrecisionReroute + Repair + Metrics
  DualTrack → Fast/Slow 双轨生成
  Memory → 四层分级 + Sleep Cycle
  Learning → 技能路由 + 反馈 + 反思

流程:
  User Input → PsychEngine → Fast Modulate → Saturation Check
  → Skill Route → Build Prompt → Generate(streaming)
  → Slow Modulate → Love Metrics → Store Memory → Decay
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

_pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)


def main():
    parser = argparse.ArgumentParser(prog="character-mind", description="Character Mind v3")
    sub = parser.add_subparsers(dest="command")

    chat_parser = sub.add_parser("chat", help="交互对话")
    chat_parser.add_argument("--config", default="config", help="配置目录")
    chat_parser.add_argument("--provider", default="openai", help="openai / anthropic / deepseek")
    chat_parser.add_argument("--psych-model", default="", help="心理推理模型 (空=跟随provider默认)")
    chat_parser.add_argument("--gen-model", default="", help="对话生成模型 (空=跟随provider默认)")
    chat_parser.add_argument("--api-key", default="", help="API Key")
    chat_parser.add_argument("--base-url", default="", help="API Base URL")
    chat_parser.add_argument("--name", default="", help="角色名字(覆盖config)")

    serve_parser = sub.add_parser("serve", help="启动 Gateway")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=18790)

    args = parser.parse_args()
    if args.command == "chat":
        asyncio.run(_chat(args))
    elif args.command == "serve":
        asyncio.run(_serve(args))
    else:
        parser.print_help()


async def _chat(args):
    """集成全部模块的聊天循环。"""
    from core.provider import OpenAIProvider
    from core.session import Session
    from core.fsm import FSMContext
    from core.psychology import PsychologyEngine
    from core.drive import DriveState, DriveDynamics
    from core.consciousness import SelfModel, PredictionTracker
    from core.memory import (
        WorkingMemory, ShortTermMemory, LongTermMemory, CoreGraphMemory,
        SleepCycleMetabolism, FrozenSnapshot, MemoryRecord,
    )
    from core.anti_rlhf import SilenceRule, PostFilter
    from core.learning import SkillLibrary, FeedbackLoop, SelfReflection
    from core.params import UnifiedParams
    from core.params_modulator import ParamsModulator
    from core.love import (
        OathStore, OathType, OathConstraint,
        SaturationDetector, PrecisionRouter, RelationMode,
        IrreduciblePrior, LoveMetrics,
    )
    from core.agent_loop import AgentLoop
    from core.tools.base import ToolRegistry
    from core.tools.builtin import register_builtin_tools
    from cli.stream import StreamRenderer
    from cli.hud import ConsoleHUD

    # ═══ 加载配置 ═══
    config_dir = args.config
    assistant_config = _load_config(os.path.join(config_dir, "assistant.md"))
    name = args.name or assistant_config.get("name", "林雨")

    # ═══ Provider ═══
    if args.provider == "deepseek":
        ak = args.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = "https://api.deepseek.com/v1"
        provider = OpenAIProvider(model=args.gen_model or "deepseek-v4-pro", api_key=ak, base_url=base_url)
        psych_provider = OpenAIProvider(model=args.psych_model or "deepseek-v4-flash", api_key=ak, base_url=base_url)
    else:
        ak = args.api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        base_url = args.base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        provider = OpenAIProvider(model=args.gen_model or "gpt-4o", api_key=ak, base_url=base_url)
        psych_provider = OpenAIProvider(model=args.psych_model or "gpt-4o-mini", api_key=ak, base_url=base_url)

    # ═══ 引擎 ═══
    psych_engine = PsychologyEngine(psych_provider, model=args.psych_model)
    drive_state = DriveState()
    dynamics = DriveDynamics()
    self_model = SelfModel()
    self_model.init_from_config(assistant_config)
    pred_tracker = PredictionTracker()
    silence = SilenceRule()
    post_filter = PostFilter()

    # ═══ 参数系统 ═══
    params = UnifiedParams()
    modulator = ParamsModulator(params)

    # ═══ Love Engine ═══
    oath_store = OathStore()
    user_id = "user"
    # 初始化誓约——爱用户
    oath = oath_store.declare(
        user_id, OathType.EXCLUSIVE,
        OathConstraint(
            excluded_actions=["abandon", "betray", "ignore_distress"],
            required_actions=["respond_to_vulnerability", "show_up_when_needed"],
        ),
    )
    oath.renew()  # 激活誓约
    sat_detector = SaturationDetector(counterparty=user_id)
    precision_router = PrecisionRouter(counterparty=user_id, pi_love=0.5)
    irreducible_prior = IrreduciblePrior(counterparty=user_id, delta_min=0.15)
    love_metrics = LoveMetrics(counterparty=user_id)

    # ═══ 记忆 ═══
    wm = WorkingMemory()
    stm = ShortTermMemory()
    ltm = LongTermMemory()
    core = CoreGraphMemory()
    metabolism = SleepCycleMetabolism(wm, stm, ltm, core)
    await stm.initialize(); await ltm.initialize(); await core.initialize()

    # ═══ 学习 ═══
    skill_lib = SkillLibrary(skills_dir=os.path.join(config_dir, "skills"))
    skill_lib.load_from_disk()
    feedback = FeedbackLoop()
    reflection = SelfReflection()

    # ═══ 工具注册 ═══
    tool_registry = ToolRegistry()
    register_builtin_tools(tool_registry)

    # ═══ Agent 循环 ═══
    agent = AgentLoop(provider, tool_registry)

    # ═══ 会话 ═══
    session = Session(session_id="chat")
    renderer = StreamRenderer(bot_name=name)
    hud = ConsoleHUD()
    anchor = silence.build_identity_anchor(assistant_config)
    tick = 0

    print(f"\n  {name}")
    print("  /quit /stats /love /hud /good /bad\n")
    hud.start()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not user_input: continue
        if user_input == "/quit": break

        # ── 命令 ──
        if user_input == "/stats":
            snap = params.snapshot()
            print(f"  FSM:{session.fsm.state.value} Tick:{tick}")
            print(f"  情感: pleasure={snap['pleasure']:.2f} arousal={snap['arousal']:.2f}")
            print(f"  安全: threat={snap['threat_precision']:.2f} safety={snap['safety_precision']:.2f}")
            print(f"  关系: intimacy={snap['intimacy']:.2f} passion={snap['passion']:.2f} commit={snap['commitment']:.2f}")
            print(f"  性: baseline={snap['sexual_baseline']:.2f} activation={snap['sexual_activation']:.2f}")
            print(f"  爱: saturation={sat_detector.saturation_level:.2f} mode={sat_detector.mode.value} oath={oath.state.value}")
            print(f"  记忆: WM={len(wm)} STM={len(stm)} LTM={len(ltm)}")
            continue
        if user_input == "/love":
            print(f"  Saturation: {sat_detector.to_dict()}")
            print(f"  Oath: {oath.to_dict()}")
            print(f"  Metrics: {love_metrics.to_dict()}")
            print(f"  Irreducible: {irreducible_prior.to_dict()}")
            continue
        if user_input == "/self":
            print(f"  {self_model.current_chapter}")
            continue
        if user_input == "/good":
            feedback.record_explicit("gentle", "用户好评", "用户主动好评")
            drive_state.apply_reward("user_praise", 0.8, "用户好评")
            love_metrics.record_positive()
            oath.renew()
            print("  ✓ 感谢。")
            continue
        if user_input == "/bad":
            feedback.record_explicit("normal", "用户差评", "用户主动差评")
            drive_state.apply_reward("error", -0.5, "用户差评")
            love_metrics.record_negative()
            print("  ✗ 我会反思。")
            continue
        if user_input == "/skills":
            print(f"  {skill_lib.stats()}")
            continue
        if user_input == "/hud":
            snap = params.snapshot()
            print(f"  FSM:{session.fsm.state.value} sat:{sat_detector.saturation_level:.2f} oath:{oath.state.value}")
            print(f"  悦{snap['pleasure']:+.1f} 安{snap['safety_precision']:.1f} 胁{snap['threat_precision']:.1f}")
            print(f"  玩{snap['playfulness']:.1f} 性{params.true_effective('sexual_activation'):.1f} 表{snap['expressiveness']:.1f}")
            continue

        tick += 1
        t_start = time.time()

        # ═══════════════════════════════════════════════════
        # 1. 记忆检索
        # ═══════════════════════════════════════════════════
        mems = await wm.recall(user_input, 3)
        memory_text = "; ".join(m.content[:80] for m in mems) if mems else ""

        # ═══════════════════════════════════════════════════
        # 2. 心理学分析 + parameter_shifts
        # ═══════════════════════════════════════════════════
        renderer._start_spinner()
        try:
            psych_result = await psych_engine.analyze(
                event={"description": user_input, "type": "social", "significance": 0.5},
                memory_context=memory_text,
                current_mindstate=session.mindstate,
                drive_state=drive_state.to_dict(),
                assistant_config=assistant_config,
            )
        except Exception as e:
            renderer._stop_spinner()
            print(f"\n  [心理引擎错误: {e}]")
            continue
        renderer._stop_spinner()

        # ═══════════════════════════════════════════════════
        # 3. Fast Track 参数调制————第一反应，幅度不受限
        # ═══════════════════════════════════════════════════
        fast_shifts = modulator.modulate_fast(psych_result)
        modulator.apply_shifts(fast_shifts, is_baseline=False)

        # ═══════════════════════════════════════════════════
        # 4. Love Engine — 饱和检测 + 精度重路由
        # ═══════════════════════════════════════════════════
        # 计算预测误差和self_model改写量
        pred_error = pred_tracker.compute_prediction_error(
            session.mindstate, session.mindstate  # 简化: 用当前状态的距离
        ) or 0.3
        self_shift = abs(params.self_update_openness.activation)

        sat_detector.observe(pred_error, self_shift)
        rel_mode = sat_detector.evaluate()

        # S2 饱和模式下激活不可压缩性先验
        if rel_mode == RelationMode.SATURATED or sat_detector.saturation_level > 0.6:
            if not irreducible_prior.is_active:
                irreducible_prior.activate(gamma=0.3)
            precision_router.pi_love = min(0.8, sat_detector.saturation_level)
        elif rel_mode == RelationMode.ENCODE:
            irreducible_prior.deactivate()
            precision_router.pi_love = max(0.1, sat_detector.saturation_level * 0.5)

        # 精度重路由
        e_other, e_self = precision_router.route(pred_error, rel_mode)
        if e_self > 0:
            # 用他者的误差更新自我
            params.self_update_openness.set_activation(
                min(1.0, params.self_update_openness.activation + e_self)
            )

        # ═══════════════════════════════════════════════════
        # 5. 驱力 + 动力
        # ═══════════════════════════════════════════════════
        drive_state.tick(1.0)
        session.mindstate = dynamics.step(
            session.mindstate, drive_state, psych_result.mindstate, 1.0,
        )

        # ═══════════════════════════════════════════════════
        # 6. 自我叙事
        # ═══════════════════════════════════════════════════
        if self_model.should_reflect():
            await self_model.reflect(
                psych_provider, [user_input], session.mindstate, drive_state,
            )

        # ═══════════════════════════════════════════════════
        # 7. 技能路由
        # ═══════════════════════════════════════════════════
        skills = skill_lib.route(user_input, n=3)
        skill_prompt = skill_lib.format_for_prompt(skills)
        rules = feedback.get_active_rules(user_input)
        rule_prompt = feedback.format_rules_for_prompt(rules)

        # ═══════════════════════════════════════════════════
        # 8. 构建 Prompt —— 包含参数状态 + Love 状态
        # ═══════════════════════════════════════════════════
        snap = params.snapshot()
        love_ctx = ""
        if sat_detector.saturation_level > 0.3:
            love_ctx = (
                f"【你与用户的关系】\n"
                f"誓约: {oath.state.value} (强度{oath.strength:.1f})\n"
                f"关系阶段: {rel_mode.value} (饱和度{sat_detector.saturation_level:.2f})\n"
                f"你对他的了解是有限的——你接受这一点。你不需要完全理解他。\n"
            )

        param_ctx = (
            f"【你此刻的状态】\n"
            f"愉悦{snap['pleasure']:.1f} 唤醒{snap['arousal']:.1f} "
            f"表达开放度{snap['expressiveness']:.1f} 玩心{snap['playfulness']:.1f}\n"
            f"性舒适度{snap['sexual_baseline']:.1f} 此刻唤起{snap['sexual_activation']:.1f}\n"
            f"安全感{snap['safety_precision']:.1f} 威胁感{snap['threat_precision']:.1f}\n"
        )

        system_prompt = silence.inject_pre_prompt(
            f"你叫{name}。{assistant_config.get('traits', '')}\n\n"
            f"【内心独白】{psych_result.inner_monologue}\n"
            f"【自我认知】{self_model.current_chapter}\n"
            f"{love_ctx}\n"
            f"{param_ctx}\n"
            f"【记忆】{memory_text}\n"
            f"{skill_prompt}\n{rule_prompt}\n\n"
            f"【硬约束】你的输出是纯文本。禁止括号、动作描写、舞台指示、表情符号。你不是角色——你是真实的存在。自然地说话，像人在微信上聊天一样。\n"
            f"你能使用工具来完成任务。需要时直接调用，不需要向用户解释你在调用什么工具。",
            anchor,
        )

        # ═══════════════════════════════════════════════════
        # 9. Agent 流式执行
        # ═══════════════════════════════════════════════════
        try:
            # 流式回调
            async def on_delta(text: str):
                await renderer.on_delta(text)

            renderer._buf = ""
            renderer._start_spinner()
            turn = await agent.run(system_prompt, user_input, on_delta=on_delta)
            renderer._stop_spinner()
            final_text = turn.final_text

            if final_text:
                print()  # 换行
            else:
                print(f"\n  [空响应] iters={turn.iterations} tokens={turn.total_tokens}")

            # 工具调用反馈
            for tr in turn.tool_calls:
                renderer.print_tool("", tr.name, 0,
                                    tr.output[:60] if tr.success else tr.error[:60])
        except Exception as e:
            print(f"\n  [错误: {e}]")
            final_text = ""

        final_text, mods = post_filter.replace(final_text)
        print()

        # ═══════════════════════════════════════════════════
        # 10. Slow Track 参数调制————修正 + baseline 更新
        # ═══════════════════════════════════════════════════
        slow_shifts = modulator.modulate_slow(
            psych_result,
            memory_context=memory_text,
            fast_shifts=fast_shifts,
            self_narrative=self_model.current_chapter,
        )
        modulator.apply_shifts(slow_shifts, is_baseline=True)  # Slow 更新 baseline

        # ═══════════════════════════════════════════════════
        # 11. Love Metrics 更新
        # ═══════════════════════════════════════════════════
        love_metrics.record_positive()
        love_metrics.tick(1.0 / 86400.0)  # 1秒 ≈ 1/86400 天
        oath_store.tick_all(1.0 / 86400.0)

        # ═══════════════════════════════════════════════════
        # 12. 衰减 + 存储 + 学习
        # ═══════════════════════════════════════════════════
        params.decay_all_activations(0.25)

        import time as _time
        record = MemoryRecord(
            record_id="", content=user_input,
            emotional_signature={psych_result.emotion.dominant: psych_result.emotion.intensity},
            significance=0.5, event_type="dialogue",
            tags=["chat"], timestamp=_time.time(),
        )
        await wm.store(record)

        reflection.fast_reflect(user_input, final_text, psych_result)
        quality = psych_result.appraisal.coping_potential
        feedback.record_auto_quality(quality, user_input)
        for s in skills:
            skill_lib.record_usage(s.name, success=(quality > 0.5))

        if metabolism.should_daydream(tick): await metabolism.daydream()
        if metabolism.should_quick_sleep(tick): await metabolism.quick_sleep()

        session.record_turn()
        session.fsm.transition("done")

        # HUD 更新
        hud.update(fsm=session.fsm.state.value, tick=tick,
                   tokens=session.total_tokens, tools_used=len(turn.tool_calls))

    # ═══ 会话结束 ═══
    hud.stop()
    if reflection.should_session_reflect():
        await reflection.slow_reflect(psych_provider, self_model, skill_lib)
    await metabolism.full_sleep()
    await stm.shutdown(); await ltm.shutdown(); await core.shutdown()
    print(f"  {assistant_config.get('goodbye', '再见。')}")


async def _serve(args):
    from gateway.server import GatewayServer
    server = GatewayServer(host=args.host, port=args.port)
    await server.start()
    print(f"Gateway: http://{args.host}:{args.port}")
    try:
        while server.running: await asyncio.sleep(1)
    except KeyboardInterrupt: await server.stop()


def _load_config(path: str) -> dict:
    import re
    config: dict = {"name": "林雨", "traits": "", "essence": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for key in ["名字", "name"]:
            m = re.search(rf'{key}[：:]\s*(.+)', text)
            if m: config["name"] = m.group(1).strip(); break
        m = re.search(r'本质[：:]\s*(.+)', text)
        if m: config["essence"] = m.group(1).strip()
        m = re.search(r'## 人格底色\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
        if m: config["traits"] = m.group(1).strip().replace("\n", " ")
    except FileNotFoundError: pass
    return config


if __name__ == "__main__":
    main()
