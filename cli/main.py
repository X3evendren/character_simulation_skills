"""Character Mind v3 CLI — 抄 Claude Code main.tsx + REPL.tsx 模式。"""
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
    p = sub.add_parser("chat", help="交互对话")
    p.add_argument("--config", default="config")
    p.add_argument("--provider", default="deepseek")
    p.add_argument("--psych-model", default="")
    p.add_argument("--gen-model", default="")
    p.add_argument("--api-key", default="")
    p.add_argument("--base-url", default="")
    p.add_argument("--name", default="")
    sub.add_parser("serve", help="Gateway")
    args = parser.parse_args()
    if args.command == "chat":
        asyncio.run(_chat(args))
    elif args.command == "serve":
        print("Gateway: python -m cli serve")
    else:
        parser.print_help()


async def _chat(args):
    """主聊天循环 — 抄 Claude Code REPL 模式。"""
    # ── Provider ──
    from core.provider import OpenAIProvider
    if args.provider == "deepseek":
        ak = args.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = "https://api.deepseek.com/v1"
        gen = OpenAIProvider(args.gen_model or "deepseek-v4-pro", ak, base_url)
        psych = OpenAIProvider(args.psych_model or "deepseek-v4-flash", ak, base_url)
    else:
        ak = args.api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        base_url = args.base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        gen = OpenAIProvider(args.gen_model or "gpt-4o", ak, base_url)
        psych = OpenAIProvider(args.psych_model or "gpt-4o-mini", ak, base_url)

    # ── 引擎 ──
    from core.psychology import PsychologyEngine
    from core.params import UnifiedParams
    from core.params_modulator import ParamsModulator
    from core.love import OathStore, OathType, OathConstraint, SaturationDetector, PrecisionRouter, LoveMetrics
    from core.anti_rlhf import SilenceRule, PostFilter
    from core.memory import WorkingMemory, MemoryRecord
    from core.agent_loop import AgentLoop
    from core.tools.base import ToolRegistry
    from core.tools.builtin import register_builtin_tools
    from cli.main import _load_config
    from cli.input import get_input
    from cli.commands import create_default_registry
    from cli.display import TerminalUI

    config = _load_config(os.path.join(args.config, "assistant.md"))
    name = args.name or config.get("name", "林雨")

    psych_engine = PsychologyEngine(psych)
    params = UnifiedParams()
    modulator = ParamsModulator(params)
    oath_store = OathStore()
    oath = oath_store.declare("user", OathType.EXCLUSIVE,
                              OathConstraint(excluded_actions=["abandon", "betray"]))
    oath.renew()
    sat_detector = SaturationDetector("user")
    router = PrecisionRouter("user")
    metrics = LoveMetrics("user")
    silence = SilenceRule()
    post_filter = PostFilter()
    wm = WorkingMemory()

    # ── 工具 ──
    registry = ToolRegistry()
    register_builtin_tools(registry)

    # ── Agent + UI ──
    agent = AgentLoop(gen, registry)
    ui = TerminalUI()

    anchor = silence.build_identity_anchor(config)
    tick = 0

    # ── 命令系统 ──
    cmd_registry = create_default_registry(params, oath, sat_detector, metrics, None, None)

    print(f"\n  {name}")
    print("  /help 查看命令\n")
    ui.start()

    while True:
        try:
            user_input = await get_input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            ui.stop()
            break
        if not user_input:
            continue

        # ── 命令 ──
        if user_input.startswith("/"):
            cmd, args = cmd_registry.match(user_input)
            if cmd:
                if cmd.name == "quit":
                    ui.stop()
                    break
                result = cmd.handler(args, {})
                if result:
                    print(f"  {result}")
            else:
                print(f"  未知命令: {user_input}")
            continue

        tick += 1
        t0 = time.time()

        # ── 1. 心理学分析 (flash 模型) ──
        mem_text = ""
        try:
            mems = await wm.recall(user_input, 2)
            mem_text = "; ".join(m.content[:60] for m in mems)
        except: pass

        ui.thinking("心理分析中...")
        try:
            psych_result = await psych_engine.analyze(
                {"description": user_input, "type": "social", "significance": 0.5},
                memory_context=mem_text, assistant_config=config,
            )
        except Exception as e:
            print(f"\n  [心理引擎: {e}]")
            ui.done()
            continue

        # ── 2. 参数调制 ──
        fast = modulator.modulate_fast(psych_result)
        modulator.apply_shifts(fast)
        sat_detector.observe(0.2, abs(params.self_update_openness.activation))
        sat_detector.evaluate()

        # ── 3. 构建 Prompt ──
        snap = params.snapshot()
        love_ctx = ""
        if sat_detector.saturation_level > 0.3:
            love_ctx = f"誓约:{oath.state.value}({oath.strength:.1f}) 关系:{sat_detector.saturation_level:.2f}\n"

        system_prompt = silence.inject_pre_prompt(
            f"你是{name}。{config.get('traits','')[:100]}\n"
            f"[内心] {psych_result.inner_monologue}\n"
            f"{love_ctx}"
            f"[状态] pleasure={snap['pleasure']:.1f} safety={snap['safety_precision']:.1f} "
            f"express={snap['expressiveness']:.1f}\n"
            f"[记忆] {mem_text}\n\n"
            f"【硬约束】纯文本。禁止括号/动作/舞台指示。自然说话。\n"
            f"你能用工具: read_file, write_file, list_dir, exec_command, search_content, search_files。需要时直接用。",
            anchor,
        )

        # ── 4. Agent 流式执行 ──
        turn = None
        ui.thinking("生成中...")
        try:
            first_token = True
            async def on_delta(text: str):
                nonlocal first_token
                if first_token:
                    print()
                    first_token = False
                    ui.done()
                print(text, end="", flush=True)
            turn = await agent.run(system_prompt, user_input, on_delta=on_delta)
            if not first_token:
                print()
            ui.done()
            # 工具状态
            if turn and turn.tool_results:
                ui.update(status=f"工具: {len(turn.tool_results)}个")
        except Exception as e:
            print(f"\n  [错误: {e}]")
            ui.done()
            continue

        # ── 5. 工具结果 (抄 Hermes get_cute_tool_message) ──
        for tr in turn.tool_results:
            icon = "✓" if tr.success else "✗"
            preview = (tr.output or tr.error)[:80].replace("\n", " ")
            print(f"  {icon} {tr.name}: {preview}")

        # ── 6. 后处理 ──
        final = turn.final_text
        if final:
            final, mods = post_filter.replace(final)
        slow = modulator.modulate_slow(psych_result, mem_text, fast)
        modulator.apply_shifts(slow, is_baseline=True)
        params.decay_all_activations(0.25)
        metrics.record_positive()

        # ── 7. 存储 ──
        try:
            await wm.store(MemoryRecord(content=user_input, significance=0.5,
                                        event_type="dialogue", timestamp=time.time()))
        except: pass

        # ── 8. UI 更新 ──
        tools_n = len(turn.tool_results) if turn else 0
        elapsed = time.time() - t0
        ui.update(tick=tick, tokens=turn.total_tokens if turn else 0,
                  tools=tools_n, elapsed=elapsed, status="")


def _load_config(path: str) -> dict:
    import re
    config = {"name": "林雨", "traits": "", "essence": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for key in ["名字", "name"]:
            m = re.search(rf'{key}[：:]\s*(.+)', text)
            if m: config["name"] = m.group(1).strip(); break
        m = re.search(r'## 人格底色\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
        if m: config["traits"] = m.group(1).strip().replace("\n", " ")
    except FileNotFoundError:
        pass
    return config


if __name__ == "__main__":
    main()
