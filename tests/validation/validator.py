"""心理学真值验证引擎。

加载验证用例，运行系统管线，评分，生成报告。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# 确保可以导入 character_simulation_skills (go 4 levels up to reach repo parent)
_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_simulation_skills import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
    StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
)
from character_simulation_skills.benchmark.mock_provider import MockProvider
from character_simulation_skills.core import orchestrator as orch
from character_simulation_skills.core.base import extract_json

from character_simulation_skills.tests.validation.metrics import score_case, aggregate_scores


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def register_all_skills():
    registry = get_registry()
    registry._skills.clear()
    for layer in registry._by_layer:
        registry._by_layer[layer].clear()
    for domain in registry._by_domain:
        registry._by_domain[domain].clear()
    registry._by_trigger.clear()

    skills = [
        BigFiveSkill(), AttachmentSkill(),
        PlutchikEmotionSkill(), PTSDTriggerSkill(), EmotionProbeSkill(),
        OCCEmotionSkill(), CognitiveBiasSkill(), DefenseMechanismSkill(), SmithEllsworthSkill(),
        GottmanSkill(), MarionSkill(), FoucaultSkill(), SternbergSkill(),
        StrogatzSkill(), FisherLoveSkill(), DiriGentSkill(), TheoryOfMindSkill(),
        GrossRegulationSkill(), KohlbergSkill(), MaslowSkill(), SDTSkill(),
        YoungSchemaSkill(), ACETraumaSkill(), ResponseGeneratorSkill(),
    ]
    for skill in skills:
        registry.register(skill)
    return len(skills)


def load_fixtures() -> list[dict]:
    cases = []
    for fname in sorted(os.listdir(FIXTURE_DIR)):
        if fname.endswith(".json"):
            with open(FIXTURE_DIR / fname, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cases.extend(data)
    return cases


def extract_outputs(result) -> dict[int, list[dict]]:
    """从 CognitiveResult 提取 {layer: [{skill_name, output, success}, ...]}"""
    outputs = {}
    for layer, skill_results in result.layer_results.items():
        outputs[layer] = []
        for sr in skill_results:
            outputs[layer].append({
                "skill_name": sr.skill_name,
                "output": sr.output,
                "success": sr.success,
                "parse_success": sr.parse_success,
            })
    return outputs


async def run_case(case: dict, quality: float = 1.0) -> dict:
    """运行单个验证用例。"""
    register_all_skills()

    # Reset orchestrator singleton
    orch._orchestrator = None
    orchestrator = get_orchestrator(anti_alignment_enabled=True)

    provider = MockProvider(quality=quality, seed=hash(case["id"]) % 10000)

    character_state = case["character_state"]
    event = case["event"]

    # 确保必要字段存在
    if "emotion_decay" not in character_state:
        character_state["emotion_decay"] = {}
    if "personality_state_machine" not in character_state:
        character_state["personality_state_machine"] = {}

    start = time.perf_counter()
    result = await orchestrator.process_event(provider, character_state, event)
    elapsed = time.perf_counter() - start

    outputs = extract_outputs(result)
    scoring = score_case(outputs, case["expected"])

    return {
        "case_id": case["id"],
        "source": case.get("source", ""),
        "total": scoring["total"],
        "assertions": scoring["assertions"],
        "details": scoring["details"],
        "elapsed_ms": elapsed * 1000,
        "total_tokens": result.total_tokens,
        "errors": result.errors,
        "combined_analysis": result.combined_analysis[:200] if result.combined_analysis else "",
    }


async def run_all(quality: float = 1.0) -> dict:
    """运行所有验证用例并汇总结果。"""
    cases = load_fixtures()
    print(f"加载 {len(cases)} 个验证用例\n")

    results = []
    for i, case in enumerate(cases):
        r = await run_case(case, quality)
        results.append(r)
        status = "PASS" if r["total"] >= 0.7 else ("WARN" if r["total"] >= 0.4 else "FAIL")
        print(f"  [{status}] {case['id']}: {r['total']:.2f} ({r['assertions']} assertions, {r['elapsed_ms']:.0f}ms)")

    aggregation = aggregate_scores(results)

    # 打印报告
    print(f"\n{'='*50}")
    print(f"  心理学真值验证报告")
    print(f"{'='*50}")
    print(f"用例数: {len(results)}")
    print(f"总得分: {aggregation['overall']:.2f}")
    print(f"\n分层得分:")
    for layer in sorted(aggregation["by_layer"]):
        info = aggregation["by_layer"][layer]
        print(f"  {layer}: {info['score']:.2f}")
        for skill, sinfo in sorted(info["skills"].items()):
            bar = "█" * int(sinfo["score"] * 20)
            print(f"    {skill}: {sinfo['score']:.2f} {bar}")

    # 薄弱点
    weak = [(s, i["score"]) for s, i in aggregation["by_skill"].items() if i["score"] < 0.6]
    if weak:
        print(f"\n薄弱点 (得分<0.6):")
        for skill, score in sorted(weak, key=lambda x: x[1]):
            print(f"  - {skill}: {score:.2f}")

    return {
        "aggregation": aggregation,
        "results": results,
    }
