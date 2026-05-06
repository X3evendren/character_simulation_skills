#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Token Efficiency Benchmark — measures tokens, TOCA writes, multi-agent, response quality
exec python -c "
import sys, os, asyncio, json, time
sys.path.insert(0, os.path.dirname(os.getcwd()))

from character_simulation_skills.benchmark.run_benchmark import register_all_skills
from character_simulation_skills.benchmark.mock_provider import MockProvider
from character_simulation_skills.benchmark.scenarios import get_scenarios
from character_simulation_skills.core.blackboard import Blackboard
from character_simulation_skills.core.perception_stream import PerceptionStream
from character_simulation_skills.core.toca_runner import TocaRunner, TocaConfig
from character_simulation_skills import get_orchestrator

async def run():
    register_all_skills()
    orch = get_orchestrator(anti_alignment_enabled=True)

    # === Metric 1: Token per event (batch pipeline) ===
    provider = MockProvider(quality=0.6, seed=42)
    scenarios = get_scenarios()
    total_tokens = 0
    total_responses = 0
    for s in scenarios[:3]:
        from character_simulation_skills.core import orchestrator as orch_mod
        orch_mod._orchestrator = None
        o = get_orchestrator(anti_alignment_enabled=True)
        r = await o.process_event(provider, s['character'], s['event'])
        total_tokens += r.total_tokens
        if r.combined_analysis and len(r.combined_analysis) > 5:
            total_responses += 1

    avg_tokens = total_tokens / 3
    resp_quality = total_responses / 3

    # === Metric 2: TOCA write rate ===
    bb = Blackboard()
    ps = PerceptionStream()
    cs = {'name': 'test', 'personality': {'openness':0.5,'conscientiousness':0.5,'extraversion':0.5,'agreeableness':0.5,'neuroticism':0.5,'attachment_style':'secure','defense_style':[],'cognitive_biases':[],'moral_stage':3}, 'trauma':{'ace_score':0,'active_schemas':[],'trauma_triggers':[]}, 'ideal_world':{}, 'motivation':{'current_goal':''}, 'emotion_decay':{}}
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
    # Simulate 2-turn conversation
    from character_simulation_skills.core import orchestrator as orch_mod2
    characters = {
        'anxious': {'name': 'anxious', 'personality': {'openness':0.5,'conscientiousness':0.5,'extraversion':0.5,'agreeableness':0.7,'neuroticism':0.75,'attachment_style':'anxious','defense_style':['投射'],'cognitive_biases':['灾难化'],'moral_stage':3}, 'trauma':{'ace_score':2,'active_schemas':['遗弃'],'trauma_triggers':['被忽视']}, 'ideal_world':{}, 'motivation':{'current_goal':''}, 'relations':{'avoidant':'partner'}, 'emotion_decay':{}},
        'avoidant': {'name': 'avoidant', 'personality': {'openness':0.4,'conscientiousness':0.6,'extraversion':0.3,'agreeableness':0.35,'neuroticism':0.45,'attachment_style':'avoidant','defense_style':['情感隔离'],'cognitive_biases':[],'moral_stage':4}, 'trauma':{'ace_score':1,'active_schemas':[],'trauma_triggers':[]}, 'ideal_world':{}, 'motivation':{'current_goal':''}, 'relations':{'anxious':'partner'}, 'emotion_decay':{}}
    }
    event = {'description': 'anxious asks why avoidant has been distant', 'type': 'conflict', 'participants': [{'name': 'avoidant', 'relation': 'partner'}], 'significance': 0.7, 'tags': ['conflict']}
    mp = MockProvider(quality=0.8, seed=99)
    orch_mod2._orchestrator = None
    o2 = get_orchestrator(anti_alignment_enabled=True)
    t1 = await o2.process_multi_agent_turn(mp, characters, event, speaker_id='anxious', listener_ids=['avoidant'])
    continuity = 1.0 if t1['conversation_turn']['text'] else 0.0

    print(f'METRIC total_tokens={avg_tokens:.1f}')
    print(f'METRIC toca_write_rate={write_rate:.2f}')
    print(f'METRIC response_quality={resp_quality:.2f}')
    print(f'METRIC multi_agent_continuity={continuity:.2f}')

asyncio.run(run())
" "$@"
