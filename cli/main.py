"""Character Mind v3 CLI"""
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
    from cli.input import get_input
    from cli.commands import create_default_registry

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
    cmd_reg = create_default_registry(params, oath, sat, metrics, None, None)
    anchor = silence.build_identity_anchor(config)
    tick = 0

    print(f"\n  {name}  [/help]\n")

    while True:
        try:
            ui = await get_input("> ")
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not ui: continue

        if ui.startswith("/"):
            cmd, args = cmd_reg.match(ui)
            if cmd:
                if cmd.name == "quit": break
                r = cmd.handler(args, {})
                if r: print(f"  {r}")
            else: print(f"  ? {ui}")
            continue

        tick += 1
        t0 = time.time()

        # 1. psych (flash)
        mem_text = ""
        try:
            mems = await wm.recall(ui, 2)
            mem_text = "; ".join(m.content[:60] for m in mems)
        except: pass

        print("  ...", end="", flush=True)
        try:
            psych_result = await psych_engine.analyze(
                {"description": ui, "type": "social", "significance": 0.5},
                memory_context=mem_text, assistant_config=config)
        except Exception as e:
            print(f"\r  [psych err: {e}]"); continue

        # 2. modulate
        fast = modulator.modulate_fast(psych_result)
        modulator.apply_shifts(fast)
        sat.observe(0.2, abs(params.self_update_openness.activation))
        sat.evaluate()

        # 3. prompt
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

        # 4. agent stream
        turn = None
        try:
            first = True
            async def od(text):
                nonlocal first
                if first: print("\r", end=""); first = False
                print(text, end="", flush=True)
            turn = await agent.run(system, ui, on_delta=od)
            if not first: print()
        except Exception as e:
            print(f"\r  [err: {e}]"); continue

        # 5. tools
        for tr in (turn.tool_results if turn else []):
            i = "+" if tr.success else "-"
            print(f"  {i} {tr.name}: {(tr.output or tr.error)[:80].replace(chr(10),' ')}")

        # 6. post
        if turn and turn.final_text:
            _, mods = post_filter.replace(turn.final_text)
        slow = modulator.modulate_slow(psych_result, mem_text, fast)
        modulator.apply_shifts(slow, is_baseline=True)
        params.decay_all_activations(0.25)
        metrics.record_positive()

        # 7. store
        try: await wm.store(MemoryRecord(content=ui, significance=0.5, event_type="dialogue", timestamp=time.time()))
        except: pass

        # 8. status
        tn = len(turn.tool_results) if turn else 0
        tok = turn.total_tokens if turn else 0
        print(f"  [t{tick} tok:{tok} tool:{tn} {time.time()-t0:.0f}s]")


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
