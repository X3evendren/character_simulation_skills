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

# 确保可以导入 character_mind (go 4 levels up to reach repo parent)
_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
    StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
)
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.core import orchestrator as orch
from character_mind.core.base import extract_json

from character_mind.tests.validation.metrics import score_case, aggregate_scores


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


def load_fixtures(source_filter: str | None = None) -> list[dict]:
    """加载所有 fixture 文件，去重，可选按来源过滤。

    跳过下划线前缀的文件（如 _validation_sample.json）。
    source_filter: 仅加载指定来源的用例 (如 "CPED", "CharacterBench")
    """
    cases = []
    seen_ids = set()
    for fname in sorted(os.listdir(FIXTURE_DIR)):
        if not fname.endswith(".json"):
            continue
        if fname.startswith("_"):
            continue  # 跳过 _validation_sample.json 等子集/草稿
        filepath = FIXTURE_DIR / fname
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [WARN] 无法加载 {fname}: {e}")
            continue
        if isinstance(data, list):
            for case in data:
                cid = case.get("id", "")
                if cid and cid in seen_ids:
                    continue  # 去重
                if source_filter and case.get("source", "") != source_filter:
                    continue
                if cid:
                    seen_ids.add(cid)
                cases.append(case)
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


async def run_case(case: dict, quality: float = 1.0, provider=None) -> dict:
    """运行单个验证用例。可传入外部 provider (如 RealLLMProvider)。"""
    register_all_skills()

    orch._orchestrator = None
    orchestrator = get_orchestrator(anti_alignment_enabled=True)

    if provider is None:
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


async def run_all(quality: float = 1.0, max_cases: int = 0) -> dict:
    """运行所有验证用例并汇总结果。max_cases=0 表示全部运行。"""
    cases = load_fixtures()
    if max_cases > 0 and max_cases < len(cases):
        import random
        random.seed(42)
        cases = random.sample(cases, max_cases)

    # 统计来源和层级覆盖
    sources = {}
    layer_coverage = {f"L{i}": 0 for i in range(6)}
    for c in cases:
        src = c.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
        for skill_name in c.get("expected", {}):
            from character_mind.tests.validation.metrics import _skill_to_layer
            layer = _skill_to_layer(skill_name)
            if layer != "?":
                layer_coverage[layer] = layer_coverage.get(layer, 0) + 1

    print(f"加载 {len(cases)} 个验证用例（去重后）")
    print(f"来源分布: {dict(sources)}")
    print(f"层级断言覆盖: {layer_coverage}")
    print()

    results = []
    for i, case in enumerate(cases):
        r = await run_case(case, quality)
        results.append(r)
        status = "PASS" if r["total"] >= 0.7 else ("WARN" if r["total"] >= 0.4 else "FAIL")
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{len(cases)}] {status} {case['id']}: {r['total']:.2f}")

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
        n_skills = len(info["skills"])
        print(f"  {layer}: {info['score']:.2f} ({n_skills} skills)")
        for skill, sinfo in sorted(info["skills"].items()):
            bar = "█" * int(sinfo["score"] * 20)
            print(f"    {skill}: {sinfo['score']:.2f} [{sinfo['assertions']} assertions] {bar}")

    # 识别零覆盖率
    zero_coverage = [l for l in sorted(layer_coverage) if layer_coverage[l] == 0]
    if zero_coverage:
        print(f"\n[WARN] Zero-coverage layers: {', '.join(zero_coverage)}")

    # 薄弱点
    weak = [(s, i["score"]) for s, i in aggregation["by_skill"].items() if i["score"] < 0.6]
    if weak:
        print(f"\n薄弱点 (得分<0.6):")
        for skill, score in sorted(weak, key=lambda x: x[1]):
            print(f"  - {skill}: {score:.2f}")

    return {
        "aggregation": aggregation,
        "results": results,
        "layer_coverage": layer_coverage,
    }
