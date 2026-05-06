"""Benchmark runner — exercises the full cognitive pipeline and measures quality metrics.

Usage:
    python benchmark/run_benchmark.py [--quality Q] [--error-rate E] [--scenarios N]

Outputs METRIC lines for autoresearch consumption.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any

# Ensure the grandparent directory is on sys.path so we can import the package
_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_simulation_skills import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill, EmotionProbeSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill, StrogatzSkill, FisherLoveSkill, DiriGentSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
    CognitiveResult, SkillResult,
)

from character_simulation_skills.benchmark.mock_provider import MockProvider, SKILL_SCHEMAS
from character_simulation_skills.benchmark.scenarios import get_scenarios


# ── Expected field counts for field coverage metric ──
EXPECTED_FIELDS: dict[str, set[str]] = {}
for _name, _schema in SKILL_SCHEMAS.items():
    EXPECTED_FIELDS[_name] = set(_schema.keys())


def register_all_skills():
    """Register all available skills with the global registry."""
    registry = get_registry()
    # Clear any previous registrations
    registry._skills.clear()
    for layer in registry._by_layer:
        registry._by_layer[layer].clear()
    for domain in registry._by_domain:
        registry._by_domain[domain].clear()
    registry._by_trigger.clear()

    skills = [
        # L0
        BigFiveSkill(), AttachmentSkill(),
        # L1
        PlutchikEmotionSkill(), PTSDTriggerSkill(), EmotionProbeSkill(),
        # L2
        OCCEmotionSkill(), CognitiveBiasSkill(), DefenseMechanismSkill(), SmithEllsworthSkill(),
        # L3
        GottmanSkill(), MarionSkill(), FoucaultSkill(), SternbergSkill(),
        StrogatzSkill(), FisherLoveSkill(), DiriGentSkill(),
        # L4
        GrossRegulationSkill(), KohlbergSkill(), MaslowSkill(), SDTSkill(),
        # L5
        YoungSchemaSkill(), ACETraumaSkill(), ResponseGeneratorSkill(),
    ]
    for skill in skills:
        registry.register(skill)
    return len(skills)


def compute_json_parse_rate(layer_results: dict[int, list[SkillResult]]) -> float:
    """Fraction of skill executions where extract_json() successfully parsed LLM output.

    Uses the parse_success flag added to SkillResult.
    """
    total = 0
    successful = 0
    for results in layer_results.values():
        for sr in results:
            total += 1
            if sr.parse_success:
                successful += 1
    return successful / max(total, 1)


def compute_error_rate(layer_results: dict[int, list[SkillResult]]) -> float:
    """Fraction of skill executions that failed."""
    total = 0
    failed = 0
    for results in layer_results.values():
        for sr in results:
            total += 1
            if not sr.success:
                failed += 1
    return failed / max(total, 1)


def compute_field_coverage(layer_results: dict[int, list[SkillResult]]) -> float:
    """Fraction of expected fields that are actually present in outputs."""
    total_expected = 0
    total_present = 0
    for results in layer_results.values():
        for sr in results:
            expected = EXPECTED_FIELDS.get(sr.skill_name)
            if expected is None:
                continue
            total_expected += len(expected)
            actual = set(sr.output.keys()) if sr.output else set()
            total_present += len(expected & actual)
    return total_present / max(total_expected, 1)


def compute_inter_layer_consistency(layer_results: dict[int, list[SkillResult]]) -> float:
    """Check emotional direction agreement between L1 (Plutchik) and L2 (OCC).

    Returns fraction of comparable layer pairs that agree on emotional valence.
    """
    # Get L1 internal pleasantness
    l1_pleasantness = None
    l1_results = layer_results.get(1, [])
    for sr in l1_results:
        if sr.skill_name == "plutchik_emotion" and sr.success:
            internal = sr.output.get("internal", {})
            l1_pleasantness = internal.get("pleasantness", 0)
            break

    # Get L2 emotional intensity and appraisal summary
    l2_pleasantness = None
    l2_results = layer_results.get(2, [])
    for sr in l2_results:
        if sr.skill_name == "occ_emotion_appraisal" and sr.success:
            conduciveness = sr.output.get("goal_conduciveness", 0)
            l2_pleasantness = 1 if conduciveness > 0 else (-1 if conduciveness < 0 else 0)
            break

    # If either is missing, can't compare
    if l1_pleasantness is None or l2_pleasantness is None:
        return 1.0  # no data = no inconsistency detected

    # Check direction agreement
    l1_dir = 1 if l1_pleasantness > 0.05 else (-1 if l1_pleasantness < -0.05 else 0)
    l2_dir = l2_pleasantness

    if l1_dir == 0 or l2_dir == 0:
        return 1.0  # neutral = no inconsistency

    return 1.0 if l1_dir == l2_dir else 0.0


async def run_scenario(provider, character_state: dict, event: dict,
                       run_index: int = 0) -> dict[str, float]:
    """Run a single scenario through the pipeline and measure all metrics."""
    # Reset global singletons for clean state
    from character_simulation_skills.core import orchestrator as orch
    orch._orchestrator = None

    orchestrator = get_orchestrator(anti_alignment_enabled=True)

    start = time.perf_counter()
    result: CognitiveResult = await orchestrator.process_event(provider, character_state, event)
    elapsed = time.perf_counter() - start

    return {
        "json_parse_rate": compute_json_parse_rate(result.layer_results),
        "total_tokens": result.total_tokens,
        "execution_time_ms": elapsed * 1000,
        "field_coverage": compute_field_coverage(result.layer_results),
        "inter_layer_consistency": compute_inter_layer_consistency(result.layer_results),
        "skill_error_rate": compute_error_rate(result.layer_results),
    }


async def run_all_scenarios(quality: float = 0.8, error_rate: float = 0.0,
                            num_scenarios: int = 0) -> dict[str, float]:
    """Run benchmark across all scenarios and aggregate results."""
    register_all_skills()
    scenarios = get_scenarios()
    if num_scenarios > 0:
        scenarios = scenarios[:num_scenarios]

    provider = MockProvider(quality=quality, error_rate=error_rate)

    all_metrics: list[dict[str, float]] = []
    for i, scenario in enumerate(scenarios):
        metrics = await run_scenario(
            provider,
            scenario["character"],
            scenario["event"],
            run_index=i,
        )
        all_metrics.append(metrics)

    # Aggregate: average across scenarios
    agg = {}
    for key in all_metrics[0]:
        values = [m[key] for m in all_metrics]
        agg[key] = sum(values) / len(values)
    return agg


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Character Simulation Skills Benchmark")
    parser.add_argument("--quality", type=float, default=0.8,
                        help="Mock provider quality 0.0-1.0 (default: 0.8)")
    parser.add_argument("--error-rate", type=float, default=0.0,
                        help="Mock provider error rate 0.0-1.0 (default: 0.0)")
    parser.add_argument("--scenarios", type=int, default=0,
                        help="Number of scenarios to run (0=all)")
    parser.add_argument("--iterations", type=int, default=1,
                        help="Number of times to repeat the benchmark")
    args = parser.parse_args()

    # Run benchmark
    all_results = []
    for i in range(args.iterations):
        # Vary seed per iteration for different mock outputs
        results = asyncio.run(run_all_scenarios(
            quality=args.quality,
            error_rate=args.error_rate,
            num_scenarios=args.scenarios,
        ))
        all_results.append(results)

    # If multiple iterations, average them
    if len(all_results) > 1:
        agg = {}
        for key in all_results[0]:
            agg[key] = sum(r[key] for r in all_results) / len(all_results)
    else:
        agg = all_results[0]

    # Output METRIC lines
    print(f"METRIC json_parse_rate={agg['json_parse_rate']:.4f}")
    print(f"METRIC total_tokens={agg['total_tokens']:.1f}")
    print(f"METRIC execution_time_ms={agg['execution_time_ms']:.1f}")
    print(f"METRIC field_coverage={agg['field_coverage']:.4f}")
    print(f"METRIC inter_layer_consistency={agg['inter_layer_consistency']:.4f}")
    print(f"METRIC skill_error_rate={agg['skill_error_rate']:.4f}")


if __name__ == "__main__":
    main()
