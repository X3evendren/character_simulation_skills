"""Character Mind v3 CLI — prompt_toolkit + Rich via ANSI buffer。"""
from __future__ import annotations

import argparse, asyncio, os, sys, time
from io import StringIO

_pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)


def _rich_to_ansi(render_fn) -> str:
    """Render Rich to ANSI string, safe for prompt_toolkit."""
    buf = StringIO()
    from rich.console import Console
    c = Console(file=buf, force_terminal=True, color_system="standard")
    render_fn(c)
    return buf.getvalue()


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
    args = p.parse_args()
    if args.cmd == "chat":
        asyncio.run(_chat(args))


async def _chat(args):
    from core.provider import OpenAIProvider
    from core.psychology import PsychologyEngine
    from core.params import UnifiedParams; from core.params_modulator import ParamsModulator
    from core.love import OathStore,OathType,OathConstraint,SaturationDetector,LoveMetrics
    from core.anti_rlhf import SilenceRule,PostFilter
    from core.memory import WorkingMemory,MemoryRecord
    from core.agent_loop import AgentLoop
    from core.tools.base import ToolRegistry
    from core.tools.builtin import register_builtin_tools
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.patch_stdout import patch_stdout
    from prompt_toolkit.formatted_text import ANSI, HTML
    from prompt_toolkit.shortcuts import print_formatted_text
    from prompt_toolkit.application import run_in_terminal

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
    cfg = _load_config(os.path.join(args.config, "assistant.md"))
    name = args.name or cfg.get("name", "林雨")
    psych_engine = PsychologyEngine(psych); params = UnifiedParams(); modulator = ParamsModulator(params)
    oath = OathStore().declare("user",OathType.EXCLUSIVE,OathConstraint(excluded_actions=["abandon","betray"])); oath.renew()
    sat = SaturationDetector("user"); metrics = LoveMetrics("user")
    silence = SilenceRule(); pf = PostFilter(); wm = WorkingMemory()
    registry = ToolRegistry(); register_builtin_tools(registry)
    agent = AgentLoop(gen, registry)
    anchor = silence.build_identity_anchor({"name":name,"essence":"","traits":cfg.get("traits","")})
    tick = 0

    # prompt_toolkit session
    hist = os.path.expanduser("~/.character_mind_history")
    os.makedirs(os.path.dirname(hist), exist_ok=True)
    session = PromptSession(history=FileHistory(hist))

    # banner — via prompt_toolkit
    def _banner():
        ansi = _rich_to_ansi(lambda c: c.print(f"\n  {name}  [/help /quit /stats]\n", markup=False))
        print_formatted_text(ANSI(ansi))
    await run_in_terminal(_banner)

    while True:
        try:
            with patch_stdout():
                user_input = await session.prompt_async(HTML("<b>></b> "))
        except (EOFError, KeyboardInterrupt):
            print_formatted_text(ANSI(_rich_to_ansi(lambda c: c.print("\nGoodbye!"))))
            break
        user_input = user_input.strip()
        if not user_input: continue
        if user_input == "/quit": break

        # commands
        if user_input == "/stats":
            s = params.snapshot()
            ansi = _rich_to_ansi(lambda c: c.print(f"  pleasure={s['pleasure']:.1f} safety={s['safety_precision']:.1f}"))
            await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))
            continue
        if user_input == "/love":
            ansi = _rich_to_ansi(lambda c: c.print(f"  oath={oath.state.value} sat={sat.saturation_level:.2f}"))
            await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))
            continue

        tick += 1; t0 = time.time()

        # memory
        mem_text = ""
        try:
            mems = await wm.recall(user_input, 2)
            mem_text = "; ".join(m.content[:60] for m in mems)
        except: pass

        # psych (flash)
        try:
            pr = await psych_engine.analyze({"description":user_input,"type":"social","significance":0.5},memory_context=mem_text,assistant_config=cfg)
        except Exception as e:
            ansi = _rich_to_ansi(lambda c: c.print(f"  [red]psych: {e}[/red]"))
            await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))
            continue

        # modulate
        fast = modulator.modulate_fast(pr); modulator.apply_shifts(fast)
        sat.observe(0.2,abs(params.self_update_openness.activation)); sat.evaluate()

        # system prompt
        s = params.snapshot()
        lc = f"Oath:{oath.state.value}({oath.strength:.1f}) sat:{sat.saturation_level:.2f}\n" if sat.saturation_level>0.3 else ""
        sys_prompt = silence.inject_pre_prompt(
            f"You are {name}. {cfg.get('traits','')[:100]}\n[inner] {pr.inner_monologue}\n{lc}[mem] {mem_text}\n\n"
            f"NO ACTIONS IN PARENS. Talk naturally. Use tools: read_file,write_file,list_dir,exec_command,search_content,search_files.", anchor)

        # agent stream — collect tokens, then render via Rich ANSI
        tokens = []
        async def od(t): tokens.append(t)
        try: turn = await agent.run(sys_prompt, user_input, on_delta=od)
        except Exception as e:
            ansi = _rich_to_ansi(lambda c: c.print(f"  [red]err: {e}[/red]"))
            await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))
            continue

        # render response via Rich Markdown → ANSI
        full_text = "".join(tokens)
        if full_text:
            from rich.markdown import Markdown
            def _render_response(c):
                c.print()
                c.print(f"[cyan]{name}[/cyan]")
                c.print(Markdown(full_text))
                c.print()
            ansi = _rich_to_ansi(_render_response)
            await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))

        # tool results
        for tr in (turn.tool_results if turn else []):
            icon = "+" if tr.success else "-"
            p = (tr.output or tr.error)[:80].replace("\n"," ")
            ansi = _rich_to_ansi(lambda c: c.print(f"  [dim]{icon} {tr.name}: {p}[/dim]"))
            await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))

        # post
        if turn and turn.final_text: _, _ = pf.replace(turn.final_text)
        slow = modulator.modulate_slow(pr, mem_text, fast); modulator.apply_shifts(slow, is_baseline=True)
        params.decay_all_activations(0.25); metrics.record_positive()
        try: await wm.store(MemoryRecord(content=user_input,significance=0.5,event_type="dialogue",timestamp=time.time()))
        except: pass

        tn = len(turn.tool_results) if turn else 0; tok = turn.total_tokens if turn else 0
        ansi = _rich_to_ansi(lambda c: c.print(f"  [dim]t{tick} tok:{tok} tool:{tn} {time.time()-t0:.0f}s[/dim]"))
        await run_in_terminal(lambda: print_formatted_text(ANSI(ansi)))


def _load_config(path: str) -> dict:
    import re
    c = {"name":"林雨","traits":"","essence":""}
    try:
        with open(path,"r",encoding="utf-8") as f: text = f.read()
        for k in ["名字","name"]:
            m = re.search(rf'{k}[：:]\s*(.+)',text)
            if m: c["name"] = m.group(1).strip(); break
        m = re.search(r'## 人格底色\n(.*?)(?=\n##|\Z)',text,re.DOTALL)
        if m: c["traits"] = m.group(1).strip().replace("\n"," ")
    except FileNotFoundError: pass
    return c


if __name__ == "__main__":
    main()
