#!/usr/bin/env python
"""用真实 LLM 运行心理学验证测试。

用法:
    python tests/validation/run_llm_validation.py [--cases N]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path

_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from character_mind.tests.validation.llm_provider import RealLLMProvider
from character_mind.tests.validation.validator import run_case
from character_mind.tests.validation.metrics import aggregate_scores


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=15, help="Number of cases to run (max 18)")
    args = parser.parse_args()

    # 精选覆盖所有维度的用例
    case_ids = [
        "pers_001", "pers_002",                  # L0 人格 Big Five
        "pevd_乔英子_1",                          # L0 PersonalityEvd
        "emo_001", "emo_003",                    # L1 情感 Plutchik
        "emo_complex_guilt", "emo_complex_despair",  # L1 复合情感
        "att_anxious_感知到被忽视",                # 依恋
        "att_avoidant_亲密要求",                   # 依恋
        "bias_灾难化", "bias_读心术",              # L2 认知偏差
        "moral_stage3", "moral_stage4",          # L4 道德
        "ptsd_ace4_0",                           # PTSD
        "gottman_criticism_defensiveness",       # L3 Gottman
        "tom_001",                               # L3 ToM
    ]

    # 加载用例
    fixture_dir = Path(__file__).parent / "fixtures"
    all_cases = {}
    for fname in sorted(os.listdir(fixture_dir)):
        if fname.endswith(".json") and not fname.startswith("_"):
            with open(fixture_dir / fname, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for c in data:
                        all_cases[c["id"]] = c

    selected = [all_cases[cid] for cid in case_ids if cid in all_cases][:args.cases]
    print(f"Running {len(selected)} cases with real LLM...\n")

    provider = RealLLMProvider()
    print(f"Provider: {provider.model} ({provider.backend})\n")

    results = []
    start_time = time.perf_counter()

    for i, case in enumerate(selected):
        case_start = time.perf_counter()
        r = await run_case(case, quality=1.0, provider=provider)
        case_elapsed = time.perf_counter() - case_start
        status = "PASS" if r["total"] >= 0.7 else ("WARN" if r["total"] >= 0.4 else "FAIL")
        print(f"  [{i+1}/{len(selected)}] [{status}] {case['id']}: {r['total']:.2f} ({case_elapsed:.0f}s, {r['total_tokens']} tokens)")
        if r["errors"]:
            print(f"    Errors: {r['errors']}")
        results.append(r)

    total_time = time.perf_counter() - start_time
    print(f"\n{'='*50}")
    print(f"  Real LLM Validation Report")
    print(f"{'='*50}")
    print(f"Model: {provider.model}")
    print(f"Cases: {len(results)}")
    print(f"Total time: {total_time:.0f}s")
    print(f"Total tokens: {sum(r['total_tokens'] for r in results)}")

    agg = aggregate_scores(results)
    print(f"\nOverall: {agg['overall']:.3f}")
    print(f"\nBy Layer:")
    for layer in sorted(agg["by_layer"]):
        info = agg["by_layer"][layer]
        if info["skills"]:
            print(f"  {layer}: {info['score']:.3f}")
            for skill, sinfo in sorted(info["skills"].items()):
                bar = "#" * int(sinfo["score"] * 30)
                print(f"    {skill}: {sinfo['score']:.3f} {bar}")

    weak = [(s, i["score"]) for s, i in agg["by_skill"].items() if i["score"] < 0.6]
    if weak:
        print(f"\nWeak spots (<0.6):")
        for skill, score in sorted(weak, key=lambda x: x[1]):
            print(f"  {skill}: {score:.3f}")

    # 输出每个用例的 combined_analysis (角色回应)
    print(f"\n=== Character Responses ===")
    for r in results:
        if r["combined_analysis"]:
            print(f"  [{r['case_id']}] {r['combined_analysis'][:150]}")


if __name__ == "__main__":
    asyncio.run(main())
