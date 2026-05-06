"""Improved benchmark with better quality metrics.

Usage: python benchmark/improved_benchmark.py

Outputs METRIC lines for autoresearch consumption.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import time

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill, StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
    CognitiveResult, SkillResult,
)
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.benchmark.scenarios import get_scenarios
from character_mind.core.blackboard import Blackboard
from character_mind.core.perception_stream import PerceptionStream
from character_mind.core.toca_runner import TocaRunner, TocaConfig


# ── 情感关键词 (Plutchik 8基情 → 中文词) ──
EMOTION_KEYWORDS = {
    'joy': ['开心', '高兴', '快乐', '喜悦', '幸福', '兴奋', '期待', '美好'],
    'sadness': ['难过', '悲伤', '痛苦', '伤心', '失落', '孤独', '想念', '遗憾', '哭泣', '眼泪'],
    'fear': ['害怕', '恐惧', '担心', '不安', '焦虑', '紧张', '惊慌', '退缩', '威胁'],
    'anger': ['生气', '愤怒', '讨厌', '厌恶', '烦躁', '怨恨', '不满'],
    'trust': ['信任', '相信', '依赖', '放心', '安心', '依靠', '坦诚'],
    'disgust': ['恶心', '反感', '嫌弃', '讨厌', '回避', '疏远', '排斥'],
    'surprise': ['惊讶', '震惊', '意外', '没想到', '竟然', '居然'],
    'anticipation': ['期待', '盼望', '等待', '希望', '渴望', '憧憬', '向往', '期盼'],
}


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
        PlutchikEmotionSkill(), PTSDTriggerSkill(),
        OCCEmotionSkill(), CognitiveBiasSkill(), DefenseMechanismSkill(), SmithEllsworthSkill(),
        GottmanSkill(), MarionSkill(), FoucaultSkill(), SternbergSkill(),
        StrogatzSkill(), FisherLoveSkill(), DiriGentSkill(), TheoryOfMindSkill(),
        GrossRegulationSkill(), KohlbergSkill(), MaslowSkill(), SDTSkill(),
        YoungSchemaSkill(), ACETraumaSkill(), ResponseGeneratorSkill(),
    ]
    for skill in skills:
        registry.register(skill)
    return len(skills)


def check_response_emotion_alignment(response_text: str, plutchik_output: dict) -> float:
    """响应文本与Plutchik情感分析的一致性 (0-1)"""
    if not response_text or not plutchik_output:
        return 0.0
    internal = plutchik_output.get('internal', {})
    dominant = internal.get('dominant', 'neutral')
    if dominant == 'neutral':
        return 1.0
    keywords = EMOTION_KEYWORDS.get(dominant, [])
    if not keywords:
        return 0.5
    matches = sum(1 for kw in keywords if kw in response_text)
    return min(1.0, matches / 2.0)


def check_response_length_quality(response_text: str) -> float:
    """响应长度合理性 (0-1)"""
    if not response_text:
        return 0.0
    length = len(response_text)
    if length < 10:
        return 0.2
    if length < 30:
        return 0.5
    if length > 500:
        return 0.6
    return 1.0


def check_response_concreteness(response_text: str) -> float:
    """响应具体性——不含空洞模板 (0-1)"""
    if not response_text:
        return 0.0
    vague_patterns = [
        r'^(嗯|哦|好|知道了|明白了|是的|对|行)[.。!！?？…]*$',
        r'^我(觉得|认为|想)了一下[.。]*$',
    ]
    stripped = response_text.strip()
    for pat in vague_patterns:
        if re.match(pat, stripped):
            return 0.3
    if len(stripped) >= 15:
        return 1.0
    return 0.5


def check_emotional_range(plutchik_outputs: list[dict]) -> float:
    """情感输出有合理变化范围 (0-1)"""
    if len(plutchik_outputs) < 2:
        return 1.0
    dominants = set()
    for out in plutchik_outputs:
        internal = out.get('internal', {})
        dom = internal.get('dominant', 'neutral')
        dominants.add(dom)
    return min(1.0, len(dominants) / 2.0)


def check_occ_plutchik_consistency(occ_outputs: list[dict], plutchik_outputs: list[dict]) -> float:
    """OCC目标促进性与Plutchik愉悦度方向一致 (0-1)"""
    if not occ_outputs or not plutchik_outputs:
        return 1.0
    score = 0.0
    count = 0
    for occ, plu in zip(occ_outputs, plutchik_outputs):
        occ_conducive = occ.get('goal_conduciveness', 0)
        plu_pleasant = plu.get('internal', {}).get('pleasantness', 0)
        occ_dir = 1 if occ_conducive > 0.1 else (-1 if occ_conducive < -0.1 else 0)
        plu_dir = 1 if plu_pleasant > 0.1 else (-1 if plu_pleasant < -0.1 else 0)
        if occ_dir == 0 or plu_dir == 0:
            score += 0.5
        elif occ_dir == plu_dir:
            score += 1.0
        count += 1
    return score / max(count, 1)


async def run():
    register_all_skills()
    orch = get_orchestrator(anti_alignment_enabled=True)

    # === Metric 1: Token per event + quality metrics ===
    provider = MockProvider(quality=0.6, seed=42)
    scenarios = get_scenarios()
    total_tokens = 0
    total_responses = 0
    responses = []
    plutchik_outputs = []
    occ_outputs = []

    for s in scenarios[:3]:
        from character_mind.core import orchestrator as orch_mod
        orch_mod._orchestrator = None
        o = get_orchestrator(anti_alignment_enabled=True)
        r = await o.process_event(provider, s['character'], s['event'])
        total_tokens += r.total_tokens

        l5 = r.layer_results.get(5, [])
        for sr in l5:
            if sr.skill_name == 'response_generator' and sr.success:
                resp = sr.output.get('response_text', '')
                if len(resp) > 5:
                    total_responses += 1
                responses.append(resp)
                break

        l1 = r.layer_results.get(1, [])
        for sr in l1:
            if sr.skill_name == 'plutchik_emotion' and sr.success:
                plutchik_outputs.append(sr.output)
                break

        l2 = r.layer_results.get(2, [])
        for sr in l2:
            if sr.skill_name == 'occ_emotion_appraisal' and sr.success:
                occ_outputs.append(sr.output)
                break

    avg_tokens = total_tokens / 3
    resp_quality = total_responses / 3

    emotion_alignment = sum(check_response_emotion_alignment(r, p) for r, p in zip(responses, plutchik_outputs)) / max(len(responses), 1)
    length_quality = sum(check_response_length_quality(r) for r in responses) / max(len(responses), 1)
    concreteness = sum(check_response_concreteness(r) for r in responses) / max(len(responses), 1)
    emotional_range = check_emotional_range(plutchik_outputs)
    response_diversity = len(set(responses)) / max(len(responses), 1)
    occ_plu_consistency = check_occ_plutchik_consistency(occ_outputs, plutchik_outputs)

    composite_quality = (
        emotion_alignment * 0.20 +
        length_quality * 0.15 +
        concreteness * 0.20 +
        emotional_range * 0.15 +
        occ_plu_consistency * 0.20 +
        response_diversity * 0.10
    )

    # === Metric 2: TOCA write rate ===
    bb = Blackboard()
    ps = PerceptionStream()
    cs = {
        'name': 'test',
        'personality': {'openness': 0.5, 'conscientiousness': 0.5, 'extraversion': 0.5, 'agreeableness': 0.5, 'neuroticism': 0.5, 'attachment_style': 'secure', 'defense_style': [], 'cognitive_biases': [], 'moral_stage': 3},
        'trauma': {'ace_score': 0, 'active_schemas': [], 'trauma_triggers': []},
        'ideal_world': {}, 'motivation': {'current_goal': ''}, 'emotion_decay': {}
    }
    config = TocaConfig(pipeline_time_s=0.5, instance_count=3, window_s=3.0)
    runner = TocaRunner(bb, ps, orch, MockProvider(quality=1.0), cs, config)
    await runner.start()
    for _ in range(3):
        ps.feed('internal', 'test perception', 0.3)
        bb.append_perception({'t': time.time(), 'modality': 'internal', 'content': 'test', 'intensity': 0.3, 'source': ''})
        await asyncio.sleep(config.interval)
    await asyncio.sleep(0.5)
    await runner.stop()
    s = runner.stats()
    write_rate = s['write_success_rate']

    # === Metric 3: Multi-agent continuity ===
    from character_mind.core import orchestrator as orch_mod2
    characters = {
        'anxious': {
            'name': 'anxious',
            'personality': {'openness': 0.5, 'conscientiousness': 0.5, 'extraversion': 0.5, 'agreeableness': 0.7, 'neuroticism': 0.75, 'attachment_style': 'anxious', 'defense_style': ['投射'], 'cognitive_biases': ['灾难化'], 'moral_stage': 3},
            'trauma': {'ace_score': 2, 'active_schemas': ['遗弃'], 'trauma_triggers': ['被忽视']},
            'ideal_world': {}, 'motivation': {'current_goal': ''}, 'relations': {'avoidant': 'partner'}, 'emotion_decay': {}
        },
        'avoidant': {
            'name': 'avoidant',
            'personality': {'openness': 0.4, 'conscientiousness': 0.6, 'extraversion': 0.3, 'agreeableness': 0.35, 'neuroticism': 0.45, 'attachment_style': 'avoidant', 'defense_style': ['情感隔离'], 'cognitive_biases': [], 'moral_stage': 4},
            'trauma': {'ace_score': 1, 'active_schemas': [], 'trauma_triggers': []},
            'ideal_world': {}, 'motivation': {'current_goal': ''}, 'relations': {'anxious': 'partner'}, 'emotion_decay': {}
        }
    }
    event = {
        'description': 'anxious asks why avoidant has been distant',
        'type': 'conflict',
        'participants': [{'name': 'avoidant', 'relation': 'partner'}],
        'significance': 0.7,
        'tags': ['conflict']
    }
    mp = MockProvider(quality=0.8, seed=99)
    orch_mod2._orchestrator = None
    o2 = get_orchestrator(anti_alignment_enabled=True)
    t1 = await o2.process_multi_agent_turn(mp, characters, event, speaker_id='anxious', listener_ids=['avoidant'])

    turn_text = t1['conversation_turn']['text']
    ma_continuity = 0.0
    if turn_text:
        ma_continuity += 0.4
        if len(turn_text) >= 15:
            ma_continuity += 0.3
        if not re.match(r'^(嗯|哦|好|知道了|我(觉得|想))', turn_text.strip()):
            ma_continuity += 0.3
    ma_continuity = min(1.0, ma_continuity)

    # === Output ===
    print(f'METRIC total_tokens={avg_tokens:.1f}')
    print(f'METRIC toca_write_rate={write_rate:.2f}')
    print(f'METRIC response_quality={resp_quality:.2f}')
    print(f'METRIC multi_agent_continuity={ma_continuity:.2f}')
    print(f'METRIC emotion_alignment={emotion_alignment:.2f}')
    print(f'METRIC length_quality={length_quality:.2f}')
    print(f'METRIC concreteness={concreteness:.2f}')
    print(f'METRIC emotional_range={emotional_range:.2f}')
    print(f'METRIC occ_plutchik_consistency={occ_plu_consistency:.2f}')
    print(f'METRIC response_diversity={response_diversity:.2f}')
    print(f'METRIC composite_quality={composite_quality:.2f}')


if __name__ == "__main__":
    asyncio.run(run())
