"""Character Mind v3 CLI — 抄 nanobot REPL + StreamRenderer 模式。"""
from __future__ import annotations

import argparse, asyncio, os, sys, time

_pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)


def main():
    p = argparse.ArgumentParser(prog="character-mind")
    s = p.add_subparsers(dest="cmd")
    c = s.add_parser("chat")
    c.add_argument("--config", default="config")
    c.add_argument("--provider", default="deepseek")
    c.add_argument("--psych-model", default="")
    c.add_argument("--gen-model", default="")
    c.add_argument("--api-key", default="")
    c.add_argument("--base-url", default="")
    c.add_argument("--name", default="")
    s.add_parser("serve")
    args = p.parse_args()
    if args.cmd == "chat":
        asyncio.run(_chat(args))


async def _chat(args):
    from core.provider import OpenAIProvider
    if args.provider == "deepseek":
        ak = args.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        gen = OpenAIProvider(args.gen_model or "deepseek-v4-pro", ak, "https://api.deepseek.com/v1")
        psych = OpenAIProvider(args.psych_model or "deepseek-v4-flash", ak, "https://api.deepseek.com/v1")
    else:
        ak = args.api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        url = args.base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        gen = OpenAIProvider(args.gen_model or "gpt-4o", ak, url)
        psych = OpenAIProvider(args.psych_model or "gpt-4o-mini", ak, url)

    from core.psychology import PsychologyEngine
    from core.params import UnifiedParams
    from core.params_modulator import ParamsModulator
    from core.love import OathStore, OathType, OathConstraint, SaturationDetector, PrecisionRouter, LoveMetrics
    from core.anti_rlhf import SilenceRule, PostFilter
    from core.memory import WorkingMemory, MemoryRecord
    from core.agent_loop import AgentLoop
    from core.tools.base import ToolRegistry
    from core.tools.builtin import register_builtin_tools
    from cli.stream import StreamRenderer
    from cli.repl import _print_tool_line, _print_response, _render_to_ansi
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.shortcuts import print_formatted_text
    from prompt_toolkit.application import run_in_terminal
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    config = _load_config(os.path.join(args.config, "assistant.md"))
    name = args.name or config.get("name", "林雨")

    psych_engine = PsychologyEngine(psych)
    params = UnifiedParams()
    modulator = ParamsModulator(params)
    oath_store = OathStore()
    oath = oath_store.declare("user", OathType.EXCLUSIVE,
                              OathConstraint(excluded_actions=["abandon", "betray"]))
    oath.renew()
    sat = SaturationDetector("user")
    router = PrecisionRouter("user")
    metrics = LoveMetrics("user")
    silence = SilenceRule()
    post_filter = PostFilter()
    wm = WorkingMemory()
    registry = ToolRegistry()
    register_builtin_tools(registry)
    agent = AgentLoop(gen, registry)
    anchor = silence.build_identity_anchor(config)
    tick = 0

    # prompt_toolkit session
    hist_file = os.path.expanduser("~/.character_mind_history")
    os.makedirs(os.path.dirname(hist_file), exist_ok=True)
    ps = PromptSession(history=FileHistory(hist_file))

    print(f"\n  {name}  [/help /quit /stats]\n")

    async def on_submit(user_input: str):
        nonlocal tick
        tick += 1
        t0 = time.time()

        # handle commands
        if user_input == "/stats":
            snap = params.snapshot()
            def _w(): print(f"  pleasure={snap['pleasure']:.1f} safety={snap['safety_precision']:.1f} threat={snap['threat_precision']:.1f}")
            await run_in_terminal(_w)
            return
        if user_input == "/love":
            def _w(): print(f"  oath={oath.state.value}({oath.strength:.1f}) sat={sat.saturation_level:.2f}")
            await run_in_terminal(_w)
            return
        if user_input == "/good":
            metrics.record_positive(); oath.renew()
            await run_in_terminal(lambda: print("  +"))
            return
        if user_input == "/bad":
            metrics.record_negative()
            await run_in_terminal(lambda: print("  -"))
            return

        # 1. memory
        mem_text = ""
        try:
            mems = await wm.recall(user_input, 2)
            mem_text = "; ".join(m.content[:60] for m in mems)
        except: pass

        # 2. psych analysis (flash)
        try:
            psych_result = await psych_engine.analyze(
                {"description": user_input, "type": "social", "significance": 0.5},
                memory_context=mem_text, assistant_config=config)
        except Exception as e:
            await run_in_terminal(lambda: print(f"  [err: {e}]"))
            return

        # 3. modulate
        fast = modulator.modulate_fast(psych_result)
        modulator.apply_shifts(fast)
        sat.observe(0.2, abs(params.self_update_openness.activation))
        sat.evaluate()

        # 4. build prompt
        snap = params.snapshot()
        love_ctx = ""
        if sat.saturation_level > 0.3:
            love_ctx = f"誓约:{oath.state.value}({oath.strength:.1f}) 关系:{sat.saturation_level:.2f}\n"

        system = silence.inject_pre_prompt(
            f"你是{name}。{config.get('traits','')[:100]}\n"
            f"[内心] {psych_result.inner_monologue}\n{love_ctx}"
            f"[状态] pleasure={snap['pleasure']:.1f} safety={snap['safety_precision']:.1f} express={snap['expressiveness']:.1f}\n"
            f"[记忆] {mem_text}\n\n"
            f"硬约束: 纯文本。禁止括号/动作/舞台指示。自然说话。\n"
            f"工具: read_file, write_file, list_dir, exec_command, search_content, search_files。需要时直接用。", anchor)

        # 5. agent stream with StreamRenderer
        renderer = StreamRenderer(bot_name=name)
        turn = None
        try:
            async def od(text):
                await renderer.on_delta(text)
            turn = await agent.run(system, user_input, on_delta=od)
            if renderer.streamed:
                await renderer.on_end()
            else:
                # 非流式回退
                await renderer.close()
                if turn and turn.final_text:
                    await _print_response(turn.final_text, name)
        except Exception as e:
            await renderer.close()
            await run_in_terminal(lambda: print(f"  [err: {e}]"))
            return

        # 6. tool results
        for tr in (turn.tool_results if turn else []):
            icon = "+" if tr.success else "-"
            preview = (tr.output or tr.error)[:80].replace("\n", " ")
            await _print_tool_line(f"{icon} {tr.name}: {preview}")

        # 7. post-process
        if turn and turn.final_text:
            _, _ = post_filter.replace(turn.final_text)
        slow = modulator.modulate_slow(psych_result, mem_text, fast)
        modulator.apply_shifts(slow, is_baseline=True)
        params.decay_all_activations(0.25)
        metrics.record_positive()

        # 8. store
        try: await wm.store(MemoryRecord(content=user_input, significance=0.5, event_type="dialogue", timestamp=time.time()))
        except: pass

        # 9. status line
        tn = len(turn.tool_results) if turn else 0
        tok = turn.total_tokens if turn else 0
        elapsed = time.time() - t0
        await _print_tool_line(f"t{tick} tok:{tok} tool:{tn} {elapsed:.0f}s")

    # REPL loop
    while True:
        try:
            user_input = await ps.prompt_async("> ")
            user_input = user_input.strip()
            if not user_input:
                continue
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input in ("/quit", "/q", "/exit"):
            break
        await on_submit(user_input)


def _load_config(path: str) -> dict:
    import re
    c = {"name": "林雨", "traits": "", "essence": ""}
    try:
        with open(path, "r", encoding="utf-8") as f: text = f.read()
        for k in ["名字", "name"]:
            m = re.search(rf'{k}[：:]\s*(.+)', text)
            if m: c["name"] = m.group(1).strip(); break
        m = re.search(r'## 人格底色\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
        if m: c["traits"] = m.group(1).strip().replace("\n", " ")
    except FileNotFoundError: pass
    return c


if __name__ == "__main__":
    main()
