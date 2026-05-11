"""Character Mind v3 CLI — 抄 nanobot REPL: prompt_toolkit + patch_stdout + Rich Live。"""
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
    from rich.console import Console
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit.formatted_text import HTML

    console = Console()
    console.print("\n  林雨  [/help /quit /stats]\n", markup=False)

    # provider
    if args.provider == "deepseek":
        ak = args.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        gen = OpenAIProvider(args.gen_model or "deepseek-v4-pro", ak, "https://api.deepseek.com/v1")
        psych = OpenAIProvider(args.psych_model or "deepseek-v4-flash", ak, "https://api.deepseek.com/v1")
    else:
        ak = args.api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        url = args.base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        gen = OpenAIProvider(args.gen_model or "gpt-4o", ak, url)
        psych = OpenAIProvider(args.psych_model or "gpt-4o-mini", ak, url)

    # engines
    name = args.name or "林雨"
    psych_engine = PsychologyEngine(psych)
    params = UnifiedParams()
    modulator = ParamsModulator(params)
    oath = OathStore().declare("user", OathType.EXCLUSIVE,
                               OathConstraint(excluded_actions=["abandon", "betray"]))
    oath.renew()
    sat = SaturationDetector("user")
    metrics = LoveMetrics("user")
    silence = SilenceRule()
    post_filter = PostFilter()
    wm = WorkingMemory()
    registry = ToolRegistry(); register_builtin_tools(registry)
    agent = AgentLoop(gen, registry)
    anchor = silence.build_identity_anchor(
        {"name": name, "essence": "", "traits": _load_config(os.path.join(args.config, "assistant.md")).get("traits", "")})
    tick = 0

    # prompt_toolkit session
    hist = os.path.expanduser("~/.character_mind_history")
    os.makedirs(os.path.dirname(hist), exist_ok=True)
    session = PromptSession(history=FileHistory(hist))

    cfg = _load_config(os.path.join(args.config, "assistant.md"))

    while True:
        try:
            with patch_stdout():
                user_input = await session.prompt_async(HTML("<b>></b> "))
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!"); break
        user_input = user_input.strip()
        if not user_input: continue
        if user_input == "/quit": break

        # commands (via Rich, prompt_toolkit already released terminal)
        if user_input == "/stats":
            s = params.snapshot()
            console.print(f"  pleasure={s['pleasure']:.1f} safety={s['safety_precision']:.1f} threat={s['threat_precision']:.1f}")
            continue
        if user_input == "/love":
            console.print(f"  oath={oath.state.value}({oath.strength:.1f}) sat={sat.saturation_level:.2f}")
            continue
        if user_input == "/good":
            metrics.record_positive(); oath.renew(); console.print("  +"); continue
        if user_input == "/bad":
            metrics.record_negative(); console.print("  -"); continue

        tick += 1; t0 = time.time()

        # memory
        mem_text = ""
        try:
            mems = await wm.recall(user_input, 2)
            mem_text = "; ".join(m.content[:60] for m in mems)
        except: pass

        # psych (flash)
        try:
            psych_result = await psych_engine.analyze(
                {"description": user_input, "type": "social", "significance": 0.5},
                memory_context=mem_text, assistant_config=cfg)
        except Exception as e:
            console.print(f"  [red]psych err: {e}[/red]"); continue

        # modulate
        fast = modulator.modulate_fast(psych_result)
        modulator.apply_shifts(fast)
        sat.observe(0.2, abs(params.self_update_openness.activation))
        sat.evaluate()

        # system prompt
        s = params.snapshot()
        lc = f"誓约:{oath.state.value}({oath.strength:.1f}) 关系:{sat.saturation_level:.2f}\n" if sat.saturation_level > 0.3 else ""
        system = silence.inject_pre_prompt(
            f"你是{name}。{cfg.get('traits','')[:100]}\n"
            f"[内心] {psych_result.inner_monologue}\n{lc}"
            f"[状态] pleasure={s['pleasure']:.1f} safety={s['safety_precision']:.1f} express={s['expressiveness']:.1f}\n"
            f"[记忆] {mem_text}\n\n"
            f"硬约束: 纯文本。禁止括号/动作/舞台指示。自然说话。\n"
            f"工具: read_file, write_file, list_dir, exec_command, search_content, search_files。需要时直接用。", anchor)

        # agent stream with Rich Live
        renderer = StreamRenderer(bot_name=name)
        try:
            async def od(text): await renderer.on_delta(text)
            turn = await agent.run(system, user_input, on_delta=od)
            if renderer.streamed: await renderer.on_end()
            else: await renderer.close()
        except Exception as e:
            await renderer.close()
            console.print(f"  [red]err: {e}[/red]"); continue

        # tool results
        for tr in (turn.tool_results if turn else []):
            icon = "+" if tr.success else "-"
            p = (tr.output or tr.error)[:80].replace("\n", " ")
            console.print(f"  [dim]{icon} {tr.name}: {p}[/dim]")

        # post
        if turn and turn.final_text: _, _ = post_filter.replace(turn.final_text)
        slow = modulator.modulate_slow(psych_result, mem_text, fast)
        modulator.apply_shifts(slow, is_baseline=True)
        params.decay_all_activations(0.25)
        metrics.record_positive()
        try: await wm.store(MemoryRecord(content=user_input, significance=0.5, event_type="dialogue", timestamp=time.time()))
        except: pass

        # status
        tn = len(turn.tool_results) if turn else 0
        tok = turn.total_tokens if turn else 0
        console.print(f"  [dim]t{tick} tok:{tok} tool:{tn} {time.time()-t0:.0f}s[/dim]")


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
