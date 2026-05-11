"""Character Mind v3"""
import argparse, asyncio, os, sys, time

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if D not in sys.path: sys.path.insert(0, D)

def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd")
    c = s.add_parser("chat")
    c.add_argument("--provider", default="deepseek")
    c.add_argument("--api-key", default="")
    args = p.parse_args()
    if args.cmd == "chat": asyncio.run(_chat(args))

async def _chat(args):
    from core.provider import OpenAIProvider
    from core.agent_loop import AgentLoop
    from core.tools.base import ToolRegistry
    from core.tools.builtin import register_builtin_tools
    from core.psychology import PsychologyEngine

    ak = args.api_key or os.environ.get("DEEPSEEK_API_KEY","")
    gen = OpenAIProvider("deepseek-v4-pro", ak, "https://api.deepseek.com/v1")
    psych = OpenAIProvider("deepseek-v4-flash", ak, "https://api.deepseek.com/v1")

    psych_eng = PsychologyEngine(psych)
    reg = ToolRegistry(); register_builtin_tools(reg)
    agent = AgentLoop(gen, reg)

    cfg = {"name":"林雨","traits":"温柔善良","essence":""}
    try:
        with open(os.path.join("config","assistant.md"), encoding="utf-8") as f:
            import re; t = f.read()
            m = re.search(r'名字[：:]\s*(.+)', t)
            if m: cfg["name"] = m.group(1).strip()
            m = re.search(r'## 人格底色\n(.*?)(?=\n##|\Z)', t, re.DOTALL)
            if m: cfg["traits"] = m.group(1).strip().replace("\n"," ")
    except: pass

    name = cfg["name"]
    print(f"\n  {name}\n")
    tick = 0

    while True:
        try: ui = input("> ").strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not ui: continue
        if ui == "/quit": break
        if ui == "/stats": print(f"  tick:{tick}"); continue

        tick += 1; t0 = time.time()

        # psych
        try: pr = await psych_eng.analyze({"description":ui,"type":"social","significance":0.5},memory_context="",assistant_config=cfg)
        except Exception as e: print(f"  [err:{e}]"); continue

        # prompt
        sp = f"You are {name}. {cfg['traits'][:100]}\n[inner]{pr.inner_monologue}\nReply naturally in Chinese. 2-3 sentences. NO stage directions."

        # agent
        tokens = []
        async def od(t): tokens.append(t)
        try:
            turn = await agent.run(sp, ui, on_delta=od)
        except Exception as e: print(f"  [err:{e}]"); continue

        full = "".join(tokens)
        if full: print(f"\n{full}\n")

        # tools
        for tr in (turn.tool_results if turn else []):
            s = "+" if tr.success else "-"
            print(f"  {s} {tr.name}: {(tr.output or tr.error)[:80].replace(chr(10),' ')}")

        tok = turn.total_tokens if turn else 0
        print(f"  [t{tick} tok:{tok} {time.time()-t0:.0f}s]")


if __name__ == "__main__": main()
