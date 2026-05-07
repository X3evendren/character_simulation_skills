"""Phase B: stratified validation with DeepSeek."""
import sys, os, asyncio, json, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# DEEPSEEK_API_KEY must be set in environment
sys.stdout.reconfigure(line_buffering=True)

from character_mind.tests.validation.llm_provider import RealLLMProvider
from character_mind.tests.validation.validator import run_case
from character_mind.tests.validation.metrics import aggregate_scores

from pathlib import Path
fixture_dir = Path(__file__).parent / "fixtures"
cases = []
for fn in sorted(os.listdir(fixture_dir)):
    if fn.endswith('.json') and not fn.startswith('_'):
        with open(fixture_dir / fn, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                cases.extend(data)

seen = set()
unique = [c for c in cases if c['id'] not in seen and not seen.add(c['id'])]

random.seed(42)
key = [c for c in unique if any(p in c['id'] for p in ['att_','pers_','emo_','bias_','moral_','ptsd_','gottman_','tom_'])]
other = [c for c in unique if c not in key]
sampled = key[:25] + random.sample(other, min(5, len(other)))

print(f"Phase B: {len(sampled)} cases\n", flush=True)
provider = RealLLMProvider()

async def main():
    results = []
    t0 = time.perf_counter()
    for i, case in enumerate(sampled):
        tc = time.perf_counter()
        r = await run_case(case, quality=1.0, provider=provider)
        results.append(r)
        print(f"[{i+1}/{len(sampled)}] {r['case_id']:35s} {r['total']:.2f} ({int(time.perf_counter()-tc)}s)", flush=True)

    agg = aggregate_scores(results)
    t = int(time.perf_counter()-t0)
    print(f"\n=== Phase B: {len(results)} cases, {t}s, Overall {agg['overall']:.3f} ===", flush=True)
    for layer in sorted(agg['by_layer']):
        for skill, sinfo in sorted(agg['by_layer'][layer]['skills'].items()):
            bar = "#" * int(sinfo['score'] * 30)
            print(f"  {skill}: {sinfo['score']:.3f} {bar}", flush=True)
    weak = [(s,i['score']) for s,i in agg['by_skill'].items() if i['score'] < 0.6]
    print(f"\nWeak: {len(weak)}" if weak else "\nNo weak spots!", flush=True)
    for s,sc in sorted(weak, key=lambda x: x[1]):
        print(f"  {s}: {sc:.3f}", flush=True)

asyncio.run(main())
